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

def obtener_ofertas(driver):
    driver.get("https://lici.cl/auto_bids")
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
                "link": link
            })
        except Exception as ex:
            logging.error(f"Error parsing tarjeta: {ex}")
    return ofertas

def ajustar_oferta(driver, card, nuevo_monto):
    # Implementa aquí el cambio de monto en la interfaz de lici.cl si es posible.
    # Ejemplo placeholder:
    # edit_btn = card.find_element(By.CSS_SELECTOR, ".edit")
    # edit_btn.click(); ...
    # caja_monto = driver.find_element(By.NAME, "monto")
    # caja_monto.clear()
    # caja_monto.send_keys(str(int(nuevo_monto)))
    # driver.find_element(By.CSS_SELECTOR, ".guardar").click()
    pass

def enviar_oferta(driver, card):
    # Implementa aquí el "click" en el botón de enviar propuesta si existe
    # Ejemplo placeholder:
    # driver.find_element(By.CSS_SELECTOR, ".enviar-propuesta").click()
    pass

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
