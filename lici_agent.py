import json
import os
import time
import logging
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuración de logging
logging.basicConfig(level=logging.INFO, filename='lici_agent.log', 
                    format='%(asctime)s | %(levelname)s | %(message)s')

# Seguridad de credenciales
LICI_USER = os.environ.get("LICI_USER")
LICI_PASS = os.environ.get("LICI_PASS")

EMPRESAS = [
    "FirmaVB Mobiliario",
    "FirmaVB Aseo",
    "FirmaVB Alimentos",
    "FirmaVB Oficina",
    "FirmaVB Electrodomésticos",
    "FirmaVB Ferretería"
]

def now_fmt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)

def login_lici(driver):
    driver.get("https://lici.cl/login")
    time.sleep(2)
    driver.find_element(By.NAME, "email").send_keys(LICI_USER)
    driver.find_element(By.NAME, "password").send_keys(LICI_PASS)
    driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
    time.sleep(3)
    assert "Inicio" in driver.page_source  # Cambia si el panel de bienvenida muestra otro texto

def cambiar_empresa(driver, empresa):
    try:
        driver.find_element(By.XPATH, f"//span[contains(text(), '{empresa}')]").click()
        time.sleep(2)
        logging.info(f"Cambiado a empresa: {empresa}")
    except Exception:
        logging.warning(f"No se pudo cambiar a empresa: {empresa}")

def obtener_ofertas(driver):
    driver.get("https://lici.cl/auto_bids")
    time.sleep(2)
    # Parsing avanzado: ajusta selectores según HTML real (dummy de ejemplo)
    cards = driver.find_elements(By.CSS_SELECTOR, ".card")
    ofertas = []
    for card in cards:
        try:
            total_items = int(card.find_element(By.CSS_SELECTOR, ".match").text.replace("%", ""))
            productos = card.find_element(By.CSS_SELECTOR, ".productos").text
            presupuesto = float(card.find_element(By.CSS_SELECTOR, ".presupuesto").text.replace("$", "").replace(".","").replace(",",""))
            ofertado = float(card.find_element(By.CSS_SELECTOR, ".ofertado").text.replace("$", "").replace(".","").replace(",",""))
            estado = card.find_element(By.CSS_SELECTOR, ".estado").text
            link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
            ofertas.append({
                "match": total_items,
                "productos": productos,
                "presupuesto": presupuesto,
                "ofertado": ofertado,
                "estado": estado,
                "link": link
            })
        except Exception as ex:
            logging.error(f"Error parsing tarjeta: {ex}")
    return ofertas

def ajustar_oferta(driver, card, nuevo_monto):
    # Implementa la lógica de edición, ajustando el monto
    pass  # Completar según la estructura de edición de lici.cl

def enviar_oferta(driver, card):
    # Implementa la navegación para enviar la propuesta
    pass  # Completar con la lógica click "enviar", validar alertas, etc.

def _load_google_credentials() -> ServiceAccountCredentials | None:
    """Carga credenciales de servicio para acceder a Google Sheets."""

    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
    ]

    creds_source: str | None = None

    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if creds_json:
        creds_source = creds_json
    elif creds_path:
        try:
            creds_source = Path(creds_path).read_text(encoding="utf-8")
        except FileNotFoundError:
            logging.error(
                "No se encontró el archivo indicado por GOOGLE_APPLICATION_CREDENTIALS"
            )
            return None

    if not creds_source:
        logging.warning(
            "Credenciales de Google Sheets no configuradas; se omitirá el registro en la hoja."
        )
        return None

    try:
        creds_dict = json.loads(creds_source)
    except json.JSONDecodeError as exc:
        logging.error(
            "El contenido de GOOGLE_APPLICATION_CREDENTIALS_JSON no es un JSON válido"
        )
        raise ValueError("Credenciales de Google inválidas") from exc

    return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)


def conectar_gsheet():
    # Requiere un archivo JSON de service account en el entorno
    creds = _load_google_credentials()
    if creds is None:
        return None

    client = gspread.authorize(creds)
    sheet_name = os.environ.get("LICI_SHEET_NAME", "PostulacionesAutomatizadas")
    sheet = client.open(sheet_name).sheet1
    return sheet

def guardar_sheet(sheet, fila):
    if sheet is None:
        logging.debug("Sin Google Sheet configurado; fila omitida: %s", fila)
        return

    sheet.append_row(fila, value_input_option="USER_ENTERED")

def ciclo():
    # Autenticación y setup
    driver = setup_driver()
    gs = conectar_gsheet()
    if gs is None:
        logging.warning("Continuando sin registrar postulaciones en Google Sheets")
    login_lici(driver)
    for empresa in EMPRESAS:
        cambiar_empresa(driver, empresa)
        ofertas = obtener_ofertas(driver)
        for oferta in ofertas:
            # Aplicar lógica: match, ajuste, faltantes
            if oferta['match'] == 100 and oferta['ofertado'] > oferta['presupuesto'] * 0.95:
                ajustar_oferta(driver, oferta, oferta['presupuesto'] * 0.95)
            enviar_oferta(driver, oferta)
            fila = [
                now_fmt(), empresa, oferta['link'], oferta['match'],
                oferta['ofertado'], oferta['presupuesto'], oferta['estado']
            ]
            guardar_sheet(gs, fila)
            logging.info(f"Registrado en Google Sheet: {fila}")
        # Agrega bucles similares para 1 y 2 productos faltantes
    driver.quit()

if __name__ == "__main__":
    try:
        ciclo()
    except Exception as e:
        logging.error(f"Fallo grave en el ciclo: {e}")
        raise
