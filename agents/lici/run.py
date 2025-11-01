import os
import sys
import time
import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
# Add common utilities to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "common"))
# from queue import load_postulaciones_queue  # noqa: E402
# from status import actualizar_status  # noqa: E402
# ======================
# Configuración & Secretos
# ======================
LICI_USER = os.environ.get("LICI_USER")
LICI_PASS = os.environ.get("LICI_PASS")
# Multi-empresa: soporta lista por ENV o usa defaults
EMPRESAS = [s.strip() for s in os.environ.get("LICI_EMPRESAS", "FirmaVB Mobiliario,FirmaVB Aseo,FirmaVB Alimentos,FirmaVB Oficina,FirmaVB Electrodomésticos,FirmaVB Ferretería").split(",") if s.strip()]
# Notificaciones por correo
NOTIFY_EMAILS = [s.strip() for s in os.environ.get("LICI_NOTIFY_EMAILS", "").split(",") if s.strip()]
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "noreply@lici-bot.local")
OUTPUT_FILE = f"artifacts/lici_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)
def now_fmt() -> StringError:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1400,1000')
    return webdriver.Chrome(options=options)
def login_lici(driver):
    driver.get("https://lici.cl/login")
    time.sleep(2)
    driver.find_element(By.NAME, "email").send_keys(LICI_USER)
    driver.find_element(By.NAME, "password").send_keys(LICI_PASS)
    driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
    time.sleep(3)
    if "Inicio" not in driver.page_source and "/dashboard" not in driver.current_url:
        logger.error("Login no detectado correctamente.")
        raise Exception("Fallo de login en lici.cl")
def cambiar_empresa(driver, empresa: str):
    try:
        # Ajustar selector según UI real
        driver.find_element(By.XPATH, f"//span[contains(text(), '{empresa}')]" ).click()
        time.sleep(2)
    except Exception:
        logger.warning(f"No se pudo cambiar a empresa: {empresa}")
@dataclass
class Oferta:
    codigo: str
    match: int  # porcentaje 0-100
    presupuesto: float
    ofertado: float
    estado: str
    link: str
    raw: Any = None  # referencia al elemento/card si se necesita
def parse_currency(s: str) -> float:
    s = s.replace("$", "").replace(".", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0
def obtener_ofertas(driver) -> List[Oferta]:
    driver.get("https://lici.cl/auto_bids")
    time.sleep(2)
    # Ajustar selectores al DOM real de lici.cl
    cards = driver.find_elements(By.CSS_SELECTOR, ".card")
    ofertas: List[Oferta] = []
    for c in cards:
        try:
            detalle = c.text
            lines = [ln for ln in detalle.splitlines() if ln.strip()]
            # Heurística: primera línea código, segunda match, tercera presupuesto, cuarta ofertado, quinta estado
            codigo = lines[0]
            match = int(lines[1].replace("%", "").strip())
            presupuesto = parse_currency(lines[2])
            ofertado = parse_currency(lines[3])
            estado = lines[4] if len(lines) > 4 else ""
            link = c.find_element(By.TAG_NAME, "a").get_attribute("href") if c.find_elements(By.TAG_NAME, "a") else ""
            ofertas.append(Oferta(codigo, match, presupuesto, ofertado, estado, link, raw=c))
        except Exception as ex:
            logger.error(f"Error parseando tarjeta: {ex}")
    return ofertas
def ajustar_oferta(driver, oferta: Oferta, nuevo_monto: float) -> bool:
    # Implementación placeholder: ajustar dentro de la card si existe input de monto
    try:
        card = oferta.raw
        if not card:
            return False
        # Estos selectores deben mapearse al DOM real
        edit = card.find_elements(By.CSS_SELECTOR, ".edit, .btn-edit, [data-action='edit']")
        if edit:
            edit[0].click()
            time.sleep(0.5)
        monto_input = card.find_element(By.CSS_SELECTOR, "input[name='monto'], input.amount, input[type='number']")
        monto_input.clear()
        monto_input.send_keys(str(int(nuevo_monto)))
        save = card.find_elements(By.CSS_SELECTOR, ".guardar, .btn-save, [data-action='save']")
        if save:
            save[0].click()
        time.sleep(1)
        return True
    except Exception as ex:
        logger.warning(f"No se pudo ajustar oferta {oferta.codigo}: {ex}")
        return False
def enviar_oferta(driver, oferta: Oferta) -> bool:
    try:
        card = oferta.raw
        if not card:
            return False
        btns = card.find_elements(By.CSS_SELECTOR, ".enviar-propuesta, .btn-submit, [data-action='submit']")
        if btns:
            btns[0].click()
            time.sleep(1)
            return True
        return False
    except Exception as ex:
        logger.warning(f"No se pudo enviar oferta {oferta.codigo}: {ex}")
        return False
def guardar_csv(fila: List[Any]):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    existe = Path(OUTPUT_FILE).exists()
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["fecha", "empresa", "codigo", "match", "ofertado", "presupuesto", "estado", "accion", "link"])
        writer.writerow(fila)
def should_bid_by_rules(match: int) -> bool:
    # Enrique's criteria: actuar entre 70%-100%
    return 70 <= match <= 100
def target_offer_amount(presupuesto: float, ofertado: float, match: int) -> Optional[float]:
    # Regla principal: si match 100%, ofertar al 95% del presupuesto máximo
    # Para 70-99%, política conservadora: tope al 95% también, pero no aumentar si ya es <=95%
    objetivo = 0.95 * presupuesto
    if match == 100:
        return objetivo
    if 70 <= match < 100:
        return objetivo if ofertado > objetivo else ofertado
    return None
def summarize_action(oferta: Oferta, realizado: str) -> str:
    return f"{oferta.codigo} | match={oferta.match}% | pres=${oferta.presupuesto:,.0f} | of=${oferta.ofertado:,.0f} | {realizado} | {oferta.link}"
def send_email(subject: str, body: str):
    if not NOTIFY_EMAILS or not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        logger.info("Notificaciones por email deshabilitadas o sin config SMTP")
        return
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body, _charset='utf-8')
        msg['Subject'] = subject
        msg['From'] = SMTP_FROM
        msg['To'] = ", ".join(NOTIFY_EMAILS)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, NOTIFY_EMAILS, msg.as_string())
        logger.info("Email de notificación enviado")
    except Exception as ex:
        logger.warning(f"Fallo enviando email: {ex}")
def run(cola=None, status_md="STATUS.md"):
    assert LICI_USER and LICI_PASS, "Definir LICI_USER y LICI_PASS en entorno"
    driver = setup_driver()
    acciones_resumen: List[str] = []
    try:
        login_lici(driver)
        for empresa in EMPRESAS:
            cambiar_empresa(driver, empresa)
            ofertas = obtener_ofertas(driver)
            for o in ofertas:
                realizado = []
                if should_bid_by_rules(o.match):
                    objetivo = target_offer_amount(o.presupuesto, o.ofertado, o.match)
                    if objetivo is not None:
                        if int(o.ofertado) != int(objetivo):
                            if ajustar_oferta(driver, o, objetivo):
                                realizado.append(f"ajustada a ${objetivo:,.0f}")
                                o.ofertado = objetivo
                        if enviar_oferta(driver, o):
                            realizado.append("enviada")
                    else:
                        realizado.append("omitida (sin objetivo)")
                else:
                    realizado.append("omitida (match < 70%)")
                accion_str = ", ".join(realizado)
                guardar_csv([
                    now_fmt(), empresa, o.codigo, o.match, int(o.ofertado), int(o.presupuesto), o.estado, accion_str, o.link
                ])
                # actualizar_status(status_md, empresa, o.codigo, f"{o.estado} ({accion_str})", now_fmt())
                acciones_resumen.append(f"[{empresa}] " + summarize_action(o, accion_str))
    finally:
        driver.quit()
        if acciones_resumen:
            send_email(
                subject=f"LICI Auto-bids: {len(acciones_resumen)} acciones",
                body="\n".join(acciones_resumen)
            )
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cola", type=str, default=None)
    parser.add_argument("--status", type=str, default="STATUS.md")
    args = parser.parse_args()
    run(cola=args.cola, status_md=args.status)
