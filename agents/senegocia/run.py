#!/usr/bin/env python3
import os, sys, pathlib, argparse, logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from agents.common.queue import read_queue_csv
from agents.common.filters import load_exclusions, contains_exclusion
from agents.common.status import append_status, write_json_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("senegocia")
ART = pathlib.Path("artifacts/senegocia")
BASE = pathlib.Path(__file__).resolve().parent.parent
EXCLUS = load_exclusions(BASE)

def need_env() -> bool:
    return os.getenv("SENEGOCIA_USER") and os.getenv("SENEGOCIA_PASS")

def login(page, user, pwd) -> None:
    page.goto("https://proveedores.senegocia.com/login", wait_until="domcontentloaded")
    page.get_by_label("Usuario").fill(user)
    page.get_by_label("Contraseña").fill(pwd)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_load_state("networkidle")

def run_item(page, palabra: str) -> dict:
    if contains_exclusion(palabra, EXCLUS):
        return {"palabra": palabra, "estado": "omitido", "motivo": "exclusion_logo"}
    page.goto("https://proveedores.senegocia.com/licitaciones", wait_until="domcontentloaded")
    page.get_by_placeholder("Buscar").fill(palabra)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ART.mkdir(parents=True, exist_ok=True)
    img = ART / f"senegocia_{ts}.png"
    page.screenshot(path=str(img), full_page=True)
    return {"palabra": palabra, "estado": "postulada", "evidencia": str(img)}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cola", required=True)
    ap.add_argument("--status", default="STATUS.md")
    args = ap.parse_args()

    if not need_env():
        append_status(args.status, "Senegocia", [{"estado": "error", "motivo": "faltan_credenciales"}])
        return 1

    resultados = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        login(page, os.getenv("SENEGOCIA_USER"), os.getenv("SENEGOCIA_PASS"))
        for it in read_queue_csv(args.cola):
            palabra = (it.get("palabra") or "").strip()
            if not palabra:
                continue
            try:
                r = run_item(page, palabra)
            except PWTimeout:
                r = {"palabra": palabra, "estado": "error", "motivo": "timeout"}
            except Exception as e:  # pylint: disable=broad-except
                r = {"palabra": palabra, "estado": "error", "motivo": str(e)}
            resultados.append(r)
        browser.close()
    append_status(args.status, "Senegocia", resultados)
    write_json_log("logs/senegocia.json", resultados)
    return 0

if __name__ == "__main__":
    sys.exit(main())
