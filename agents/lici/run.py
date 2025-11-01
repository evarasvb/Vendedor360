import os
import sys
import time
import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

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

# Notificaciones por correo (reservado para futuras extensiones)
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
    driver.get("https://www.licitaciones.info/login")
    time.sleep(2)

    # XPath selectors for login fields
    email_input = driver.find_element(By.XPATH, '//input[@type="email" or @aria-label="Email" or contains(@placeholder, "mail")]')
    email_input.send_keys(LICI_USER)

    password_input = driver.find_element(By.XPATH, '//input[@type="password" or @aria-label="Contraseña"]')
    password_input.send_keys(LICI_PASS)
    password_input.send_keys(Keys.RETURN)

    time.sleep(3)
    logger.info("Login completado.")


def cambiar_empresa(driver, nombre_empresa: str):
    """
    Cambia a la empresa especificada en el selector del encabezado.
    Si ya está activa, retorna True de inmediato.
    """
    logger.info(f"Intentando cambiar a empresa: {nombre_empresa}")
    try:
        selector = driver.find_element(By.ID, "company-selector")
        current = selector.get_attribute("value") or selector.text
        if nombre_empresa.lower() in current.lower():
            logger.info(f"Empresa '{nombre_empresa}' ya activa.")
            return True

        selector.click()
        time.sleep(1)

        options = driver.find_elements(By.CSS_SELECTOR, "#company-selector option, .company-option")
        for opt in options:
            if nombre_empresa.lower() in opt.text.lower():
                opt.click()
                time.sleep(2)
                logger.info(f"Empresa cambiada a '{nombre_empresa}'.")
                return True

        logger.warning(f"No se encontró la empresa '{nombre_empresa}' en el selector.")
        return False
    except NoSuchElementException:
        logger.warning("Selector de empresa no encontrado.")
        return False


@dataclass
class Oferta:
    licitacion_id: str
    titulo: str
    organismo: str
    monto_actual: float
    mi_oferta: Optional[float]
    num_ofertas: int
    fecha_cierre: str
    link: str


def parse_currency(text: str) -> float:
    """
    Convierte strings como '$1.234.567' o '$ 1.234.567 CLP' a float.
    """
    if not text:
        return 0.0
    clean = text.replace("$", "").replace(".", "").replace(",", ".").strip().split()[0]
    try:
        return float(clean)
    except ValueError:
        return 0.0


def obtener_ofertas(driver, empresa: str) -> List[Oferta]:
    """
    Navega a la página de 'Mis Licitaciones' y extrae las licitaciones activas.
    """
    logger.info(f"Obteniendo licitaciones para empresa '{empresa}'...")
    driver.get("https://www.licitaciones.info/mis-licitaciones")
    time.sleep(3)

    ofertas = []
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, ".licitacion-row, tr.licitacion")
        for row in rows:
            try:
                licitacion_id = row.find_element(By.CSS_SELECTOR, ".licitacion-id").text.strip()
                titulo = row.find_element(By.CSS_SELECTOR, ".licitacion-titulo").text.strip()
                organismo = row.find_element(By.CSS_SELECTOR, ".licitacion-organismo").text.strip()
                monto_str = row.find_element(By.CSS_SELECTOR, ".licitacion-monto").text.strip()
                monto_actual = parse_currency(monto_str)

                mi_oferta_elem = row.find_elements(By.CSS_SELECTOR, ".mi-oferta")
                mi_oferta = parse_currency(mi_oferta_elem[0].text) if mi_oferta_elem else None

                num_ofertas_elem = row.find_elements(By.CSS_SELECTOR, ".num-ofertas")
                num_ofertas = int(num_ofertas_elem[0].text) if num_ofertas_elem else 0

                fecha_cierre = row.find_element(By.CSS_SELECTOR, ".fecha-cierre").text.strip()

                link_elem = row.find_element(By.CSS_SELECTOR, "a.licitacion-link")
                link = link_elem.get_attribute("href")

                ofertas.append(Oferta(
                    licitacion_id=licitacion_id,
                    titulo=titulo,
                    organismo=organismo,
                    monto_actual=monto_actual,
                    mi_oferta=mi_oferta,
                    num_ofertas=num_ofertas,
                    fecha_cierre=fecha_cierre,
                    link=link
                ))
            except Exception as e:
                logger.warning(f"Error al procesar fila de licitación: {e}")
                continue

        logger.info(f"Se encontraron {len(ofertas)} licitaciones.")
    except Exception as e:
        logger.error(f"Error al obtener ofertas: {e}")

    return ofertas


def ajustar_oferta(driver, oferta: Oferta, nuevo_monto: float) -> bool:
    """
    Navega a la licitación y ajusta la oferta al monto especificado.
    """
    logger.info(f"Ajustando oferta para {oferta.licitacion_id} a ${nuevo_monto:,.0f}")
    try:
        driver.get(oferta.link)
        time.sleep(2)

        input_oferta = driver.find_element(By.CSS_SELECTOR, "input[name='oferta'], #oferta-input")
        input_oferta.clear()
        input_oferta.send_keys(str(int(nuevo_monto)))

        btn_enviar = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .btn-enviar-oferta")
        btn_enviar.click()
        time.sleep(2)

        logger.info(f"Oferta ajustada exitosamente para {oferta.licitacion_id}.")
        return True
    except Exception as e:
        logger.error(f"Error al ajustar oferta para {oferta.licitacion_id}: {e}")
        return False


def enviar_oferta(driver, oferta: Oferta, monto: float) -> bool:
    """
    Alias de ajustar_oferta para enviar una nueva oferta.
    """
    return ajustar_oferta(driver, oferta, monto)


def guardar_csv(ofertas: List[Oferta], empresa: str):
    """
    Guarda las ofertas procesadas en un archivo CSV.
    """
    Path("artifacts").mkdir(exist_ok=True)
    with open(OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow(["Timestamp", "Empresa", "Licitacion_ID", "Titulo", "Organismo",
                             "Monto_Actual", "Mi_Oferta", "Num_Ofertas", "Fecha_Cierre", "Link"])
        for oferta in ofertas:
            writer.writerow([
                now_fmt(), empresa, oferta.licitacion_id, oferta.titulo, oferta.organismo,
                oferta.monto_actual, oferta.mi_oferta, oferta.num_ofertas, oferta.fecha_cierre, oferta.link
            ])
    logger.info(f"Ofertas guardadas en {OUTPUT_FILE}")


def should_bid_by_rules(oferta: Oferta) -> bool:
    """
    Evalúa si se debe ofertar basándose en reglas de negocio.
    """
    if oferta.monto_actual <= 0:
        return False
    if oferta.mi_oferta and oferta.mi_oferta <= oferta.monto_actual:
        return False
    return True


def target_offer_amount(oferta: Oferta) -> float:
    """
    Calcula el monto objetivo para ofertar (ej. 1% menos que el actual).
    """
    return oferta.monto_actual * 0.99


def summarize_action(oferta: Oferta, action: str, empresa: str):
    """
    Registra un resumen de la acción tomada para una licitación.
    """
    logger.info(f"[{empresa}] {action} | {oferta.licitacion_id} | {oferta.titulo}")


def run():
    """
    Función principal que ejecuta el bot para todas las empresas configuradas.
    """
    logger.info(f"=== Iniciando bot LICI para {len(EMPRESAS)} empresa(s) ===")
    driver = setup_driver()

    try:
        login_lici(driver)

        for empresa in EMPRESAS:
            logger.info(f"\n{'='*60}")
            logger.info(f"Procesando empresa: {empresa}")
            logger.info(f"{'='*60}")

            if not cambiar_empresa(driver, empresa):
                logger.warning(f"No se pudo cambiar a la empresa '{empresa}'. Saltando.")
                continue

            ofertas = obtener_ofertas(driver, empresa)
            if not ofertas:
                logger.info(f"No hay licitaciones activas para '{empresa}'.")
                continue

            for oferta in ofertas:
                if should_bid_by_rules(oferta):
                    nuevo_monto = target_offer_amount(oferta)
                    if enviar_oferta(driver, oferta, nuevo_monto):
                        summarize_action(oferta, "OFERTA_ENVIADA", empresa)
                    else:
                        summarize_action(oferta, "ERROR_ENVIO", empresa)
                else:
                    summarize_action(oferta, "NO_ACCION", empresa)

            guardar_csv(ofertas, empresa)

        logger.info("\n=== Ejecución completada ===")

    except Exception as e:
        logger.error(f"Error crítico durante la ejecución: {e}", exc_info=True)
    finally:
        driver.quit()
        logger.info("Driver cerrado.")


if __name__ == "__main__":
    run()
