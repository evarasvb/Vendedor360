#!/usr/bin/env python3
import os, sys, pathlib, argparse, logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from agents.common.queue import read_queue_csv
from agents.common.filters import load_exclusions, contains_exclusion
from agents.common.status import append_status, write_json_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wherex")
ART = pathlib.Path("artifacts/wherex"); LOGS = pathlib.Path("logs")
BASE = pathlib.Path(__file__).resolve().parent.parent; EXCLUS = load_exclusions(BASE)

def need_env():
    return os.getenv("WHEREX_USER") and os.getenv("WHEREX_PASS")

def login(page, user, pwd):
    page.goto("https://login.wherex.com", wait_until
              ="domcontentloaded")
    page.get_by_label("Correo").fill(user)
    page.get_by_label("Contraseña").fill(pwd)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_load_state("networkidle")

def run_item(page, palabra: str) -> dict:
    if contains_exclusion(palabra, EXCLUS):
        return {"palabra": palabra, "estado": "omitido", "motivo": "exclusion_logo"}
    page.goto("https://proveedores.wherex.com/licitaciones", wait_until="domcontentloaded")
    page.get_by_placeholder("Buscar").fill(palabra)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    cards = page.locator(".card-licitacion").all()
    if not cards:
        return {"palabra": palabra, "estado": "sin_resultados"}
    titulo = (cards[0].text_content() or "").lower()
    if contains_exclusion(titulo, EXCLUS):
        return {"palabra": palabra, "estado": "omitido", "motivo": "exclusion_logo_titulo"}
    cards[0].click()
    page.wait_for_load_state("networkidle")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ART.mkdir(parents=True, exist_ok=True)
    img = ART / f"wherex_{ts}.png"
    page.screenshot(path=str(img), full_page=True)
    return {"palabra": palabra, "estado": "postulada", "evidencia": str(img)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cola", required=True)
    ap.add_argument("--status", default="STATUS.md")
    args = ap.parse_args()

    if not need_env():
        append_status(args.status, "Wherex", [{"estado": "error", "motivo": "faltan_credenciales"}])
        
        return 1


    queue = read_queue_csv(args.cola)
    resultados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            login(page, os.environ["WHEREX_USER"], os.environ["WHEREX_PASS"])
            for item in queue:
                palabra = item.get("palabra") or ""
                try:
                    res = run_item(page, palabra)
                except PWTimeout:
                    log.exception("timeout")
                    res = {"palabra": palabra, "estado": "error", "motivo": "timeout"}
 
                except Exception as e:

                    log.exception("error")
                    res = {"palabra": palabra, "estado": "error", "motivo": str(e)}
                resultados.append(res)
        finally:
            page.close()
            browser.close()

    append_status(args.status, "Wherex", resultados)
    write_json_log(LOGS / "wherex.json", resultados)
    return 0

if __name__ == "__main__":
    sys.exit(main())
