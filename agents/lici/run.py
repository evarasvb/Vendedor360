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
EMPRESAS = [
    s.strip()
    for s in os.environ.get("LICI_EMPRESAS", "FirmaVB Mobiliario,FirmaVB Aseo,FirmaVB Alimentos,FirmaVB Oficina,FirmaVB Electrodomésticos,FirmaVB Ferretería").split(",")
    if s.strip()
]

# Notificaciones por correo
NOTIFY_EMAILS = [
    s.strip()
    for s in os.environ.get("LICI_NOTIFY_EMAILS", "").split(",")
    if s.strip()
]
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "noreply@lici-bot.local")

OUTPUT_FILE = f"artifacts/lici_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def now_fmt() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1400,1000')
    return webdriver.Chrome(options=options)

def login_lici(driver):
    logger.info("Iniciando login en LICI...")
    driver.get("https://www.licitaciones.info/empresas/")
    time.sleep(2)
    
    email_input = driver.find_element(By.XPATH, '//input[@aria-label="Email" or @placeholder="Email" or contains(@name, "email")]')
    email_input.send_keys(LICI_USER)
    
    pwd_input = driver.find_element(By.XPATH, '//input[@aria-label="Contraseña" or @type="password" or @placeholder="Contraseña"]')
    pwd_input.send_keys(LICI_PASS)
    pwd_input.send_keys(Keys.RETURN)
    
    time.sleep(3)
    logger.info("Login exitoso")

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
