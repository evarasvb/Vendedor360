import os
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuración de logging
logging.basicConfig(level=logging.INFO, filename='lici_agent.log', 
                    format='%(asctime)s | %(levelname)s | %(message)s')

# Seguridad de credenciales
LICI_USER = os.environ.get("LICI_USER")
LICI_PASS = os.environ.get("LICI_PASS")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
SHEET_NAME = os.environ.get("LICI_SHEET_NAME", "PostulacionesAutomatizadas")

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

LISTING_URL = "https://lici.cl/auto_bids"


def obtener_ofertas(driver):
    driver.get(LISTING_URL)
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
                "link": link,
                "element": card,
                "list_url": driver.current_url
            })
        except Exception as ex:
            logging.error(f"Error parsing tarjeta: {ex}")
    return ofertas

def _abrir_detalle_oferta(driver, oferta):
    """Asegura que la oferta esté abierta en pantalla y devuelve metadatos."""
    if oferta.get("_detail_open"):
        return oferta.get("_origin_window"), oferta.get("list_url"), False

    origen = driver.current_window_handle
    list_url = oferta.get("list_url", LISTING_URL)
    try:
        enlace = oferta.get("link")
        if enlace:
            driver.get(enlace)
        elif oferta.get("element"):
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", oferta["element"])
            click_target = oferta["element"].find_element(By.TAG_NAME, "a")
            click_target.click()
        else:
            raise ValueError("La oferta no tiene referencia navegable")

        WebDriverWait(driver, 10).until(lambda d: d.current_url != list_url or len(d.window_handles) > 1)
        if len(driver.window_handles) > 1:
            for handle in driver.window_handles:
                if handle != origen:
                    driver.switch_to.window(handle)
                    break

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        oferta["_detail_open"] = True
        oferta["_origin_window"] = origen
        return origen, list_url, True
    except Exception as exc:
        logging.error(f"No se pudo abrir detalle de oferta: {exc}")
        raise


def _encontrar_elemento(driver, candidatos):
    for by, selector in candidatos:
        try:
            elemento = WebDriverWait(driver, 5).until(EC.presence_of_element_located((by, selector)))
            return elemento
        except TimeoutException:
            continue
        except Exception:
            continue
    raise NoSuchElementException(f"No se encontró ningún elemento con los selectores: {candidatos}")


def ajustar_oferta(driver, oferta, nuevo_monto):
    origen, list_url, opened_here = _abrir_detalle_oferta(driver, oferta)
    try:
        campo_monto = _encontrar_elemento(driver, [
            (By.CSS_SELECTOR, "input[name='monto']"),
            (By.CSS_SELECTOR, "input[name='offer_amount']"),
            (By.CSS_SELECTOR, "input[name='amount']"),
            (By.CSS_SELECTOR, "input[id*='monto']"),
            (By.CSS_SELECTOR, "input[id*='amount']"),
        ])
        campo_monto.click()
        campo_monto.clear()
        campo_monto.send_keys(str(int(round(nuevo_monto))))

        boton_guardar = _encontrar_elemento(driver, [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "button.guardar"),
            (By.XPATH, "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'guardar')]")
        ])
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton_guardar)
        boton_guardar.click()

        try:
            WebDriverWait(driver, 10).until(EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".toast-success")),
                EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Actualizado")
            ))
        except TimeoutException:
            logging.warning("No se detectó confirmación visual tras guardar la oferta")
    except Exception as exc:
        logging.error(f"Error ajustando oferta: {exc}")
        raise
    finally:
        if opened_here:
            # Se mantiene abierta para que enviar_oferta la utilice.
            oferta["_detail_open"] = True


def enviar_oferta(driver, oferta):
    origen, list_url, _ = _abrir_detalle_oferta(driver, oferta)
    try:
        boton_enviar = _encontrar_elemento(driver, [
            (By.CSS_SELECTOR, "button.enviar"),
            (By.CSS_SELECTOR, "button[type='submit'].enviar-oferta"),
            (By.XPATH, "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'enviar')]")
        ])
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton_enviar)
        boton_enviar.click()

        try:
            confirmacion = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'confirmar') or "
                "contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'si')]"
            )))
            confirmacion.click()
        except TimeoutException:
            pass

        try:
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            alerta = driver.switch_to.alert
            alerta.accept()
        except TimeoutException:
            pass

        try:
            WebDriverWait(driver, 10).until(EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".toast-success")),
                EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "enviada")
            ))
        except TimeoutException:
            logging.warning("No se detectó confirmación visual tras enviar la oferta")
    except Exception as exc:
        logging.error(f"Error al enviar oferta: {exc}")
        raise
    finally:
        oferta["_detail_open"] = False
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(origen)
            else:
                if driver.current_url != list_url:
                    driver.get(list_url)
        except Exception as exc:
            logging.warning(f"No se pudo retornar a la lista de ofertas: {exc}")


def conectar_gsheet():
    # Requiere un archivo JSON de service account en el entorno
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = eval(GOOGLE_CREDS_JSON) if GOOGLE_CREDS_JSON else None
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

def guardar_sheet(sheet, fila):
    sheet.append_row(fila, value_input_option="USER_ENTERED")

def ciclo():
    # Autenticación y setup
    driver = setup_driver()
    gs = conectar_gsheet()
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
