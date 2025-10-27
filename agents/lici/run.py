import os
import sys
import time
import csv
import logging
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
sys.path.append(str(Path(__file__).resolve().parent.parent / "common"))
from queue import load_postulaciones_queue
from status import actualizar_status

# === CONFIGURACIÓN DE ENTORNO/SECRETOS
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
OUTPUT_FILE = f"artifacts/lici_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

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
    if "Inicio" not in driver.page_source:
        logging.error("Login no detectado correctamente.")
        raise Exception("Fallo de login en lici.cl")

def cambiar_empresa(driver, empresa):
    try:
        driver.find_element(By.XPATH, f"//span[contains(text(), '{empresa}')]").click()
        time.sleep(2)
    except Exception:
        logging.warning(f"No se pudo cambiar a empresa: {empresa}")

LISTING_URL = "https://lici.cl/auto_bids"


def obtener_ofertas(driver):
    driver.get(LISTING_URL)
    time.sleep(2)
    # ATENCIÓN: Ajusta los selectores reales según la estructura HTML de lici.cl (dummy de ejemplo abajo).
    cards = driver.find_elements(By.CSS_SELECTOR, ".card")
    ofertas = []
    for c in cards:
        try:
            detalle = c.text
            # --- Parsing manual básico. Ajusta según tus campos reales ---
            lines = detalle.splitlines()
            codigo = lines[0]
            match = int(lines[1].replace("%", ""))  # por ejemplo: "100%"
            presupuesto = float(lines[2].replace("$", "").replace(".", "").replace(",", ""))
            ofertado = float(lines[3].replace("$", "").replace(".", "").replace(",", ""))
            estado = lines[4]
            link = c.find_element(By.TAG_NAME, "a").get_attribute("href") if c.find_elements(By.TAG_NAME, "a") else ""
            ofertas.append({
                "codigo": codigo,
                "match": match,
                "presupuesto": presupuesto,
                "ofertado": ofertado,
                "estado": estado,
                "link": link,
                "element": c,
                "list_url": driver.current_url
            })
        except Exception as ex:
            logging.error(f"Error parsing tarjeta: {ex}")
    return ofertas

def _abrir_detalle_oferta(driver, oferta):
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

def guardar_csv(fila):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    existe = Path(OUTPUT_FILE).exists()
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["fecha", "empresa", "codigo", "match", "ofertado", "presupuesto", "estado", "link"])
        writer.writerow(fila)

def run(cola=None, status_md="STATUS.md"):
    driver = setup_driver()
    login_lici(driver)
    for empresa in EMPRESAS:
        cambiar_empresa(driver, empresa)
        ofertas = obtener_ofertas(driver)
        for o in ofertas:
            realizado = ""
            # 100% match
            if o['match'] == 100:
                if o['ofertado'] >= o['presupuesto'] * 0.95:
                    ajustar_oferta(driver, o, o['presupuesto'] * 0.95)
                    realizado = "ajustada"
                enviar_oferta(driver, o)
                realizado += " enviada"
            # Repite lógica para 1 y 2 faltantes si puedes identificarlo en el parser
            guardar_csv([
                now_fmt(), empresa, o['codigo'], o['match'], o['ofertado'], o['presupuesto'], f"{o['estado']} ({realizado.strip()})", o['link']
            ])
            actualizar_status(status_md, empresa, o['codigo'], o['estado'], now_fmt())
    driver.quit()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cola", type=str, default=None)
    parser.add_argument("--status", type=str, default="STATUS.md")
    args = parser.parse_args()
    run(cola=args.cola, status_md=args.status)
