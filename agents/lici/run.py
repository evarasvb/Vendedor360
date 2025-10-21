import argparse
import csv
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from agents.common.queue import read_queue_csv
from agents.common.status import append_status, write_json_log

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

def normalize_empresa(nombre: str) -> str:
    return nombre.strip().lower().replace(" ", "")


def load_objetivos(cola: str | None) -> Dict[str, Dict[str, float]]:
    if not cola or not Path(cola).exists():
        return {}

    objetivos: Dict[str, Dict[str, float]] = {}
    for row in read_queue_csv(cola):
        empresa = row.get("empresa") or ""
        if not empresa:
            continue
        key = normalize_empresa(empresa)
        meta = objetivos.setdefault(key, {"match_min": 100.0, "precio_max": 0.0})
        try:
            match_min = float(row.get("match_min") or 100)
            meta["match_min"] = max(meta["match_min"], match_min)
        except ValueError:
            pass
        try:
            precio = float(row.get("precio_max") or 0)
            meta["precio_max"] = max(meta["precio_max"], precio)
        except ValueError:
            pass
    return objetivos


def run(cola: str | None = None, status_md: str = "STATUS.md") -> None:
    objetivos = load_objetivos(cola)
    resultados: List[dict] = []

    driver = setup_driver()
    try:
        login_lici(driver)
        for empresa in EMPRESAS:
            normalized = normalize_empresa(empresa)
            if objetivos and normalized not in objetivos:
                logging.info("Saltando %s por no estar en la cola priorizada", empresa)
                continue

            meta = objetivos.get(normalized, {"match_min": 100.0, "precio_max": 0.0})
            cambiar_empresa(driver, empresa)
            ofertas = obtener_ofertas(driver)
            for o in ofertas:
                realizado: List[str] = []
                estado_final = o["estado"]

                if o["match"] >= meta.get("match_min", 100):
                    if meta.get("precio_max", 0) and o["presupuesto"] > meta["precio_max"]:
                        estado_final = f"omitida (presupuesto>{meta['precio_max']})"
                    else:
                        if o["ofertado"] >= o["presupuesto"] * 0.95:
                            ajustar_oferta(driver, o, o["presupuesto"] * 0.95)
                            realizado.append("ajustada")
                        enviar_oferta(driver, o)
                        realizado.append("enviada")
                        estado_final = "procesada"

                guardar_csv([
                    now_fmt(),
                    empresa,
                    o["codigo"],
                    o["match"],
                    o["ofertado"],
                    o["presupuesto"],
                    estado_final,
                    o["link"],
                ])
                resultados.append(
                    {
                        "empresa": empresa,
                        "codigo": o["codigo"],
                        "match": o["match"],
                        "estado": estado_final,
                        "acciones": ",".join(realizado) if realizado else "",
                        "link": o["link"],
                    }
                )
    finally:
        driver.quit()

    append_status(status_md, "Lici", resultados)
    write_json_log("logs/lici.json", resultados)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cola", type=str, default=None)
    parser.add_argument("--status", type=str, default="STATUS.md")
    args = parser.parse_args()

    run(cola=args.cola, status_md=args.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
