#!/usr/bin/env python3
import os, sys, argparse, pathlib, logging, time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from agents.common.queue import read_queue_csv
from agents.common.filters import load_exclusions, contains_exclusion
from agents.common.status import append_status, write_json_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lici")

ART = pathlib.Path("artifacts/lici"); LOGS = pathlib.Path("logs")
BASE = pathlib.Path(__file__).resolve().parent.parent
EXCLUS = load_exclusions(BASE)

def need_env() -> bool:
    return os.getenv("LICI_USER") and os.getenv("LICI_PASS")

def match_score(nombre: str, palabra: str) -> float:
    nombre = (nombre or "").lower(); tokens = [t for t in (palabra or "").lower().split() if t]
    if not tokens: return 0.0
    hits = sum(1 for t in tokens if t in nombre)
    return 100.0 * hits / len(tokens)

def login(page):
    page.goto("https://www.lici.cl/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Iniciar sesión").click()
    page.wait_for_load_state("networkidle")
    page.get_by_label("Correo").fill(os.environ["LICI_USER"])
    page.get_by_label("Contraseña").fill(os.environ["LICI_PASS"])
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_load_state("networkidle")

def search_and_apply(page, palabra: str, match_min: float) -> dict:
    if contains_exclusion(palabra, EXCLUS):
        return {"palabra": palabra, "estado": "omitido", "motivo": "exclusion_logo"}
    page.goto("https://www.lici.cl/licitaciones", wait_until="domcontentloaded")
    page.get_by_placeholder("Buscar").fill(palabra)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    cards = page.locator(".card-licitacion").all()
    if not cards:
        return {"palabra": palabra, "estado": "sin_resultados"}

    titulo = (cards[0].text_content() or "")
    if contains_exclusion(titulo, EXCLUS):
        return {"palabra": palabra, "estado": "omitido", "motivo": "exclusion_logo_titulo"}

    score = match_score(titulo, palabra)
    if score < match_min:
        return {"palabra": palabra, "estado": "no_match", "score": round(score,1)}

    cards[0].click()
    page.wait_for_load_state("networkidle")

    applied = False
    for label in ["Postular","Participar","Enviar","Enviar oferta","Postulación"]:
        try:
            btn = page.get_by_role("button", name=label)
            if btn and btn.is_visible():
                btn.click(); page.wait_for_load_state("networkidle"); applied = True; break
        except Exception:
            continue

    ART.mkdir(parents=True, exist_ok=True)
    img = ART / f"lici_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    page.screenshot(path=str(img), full_page=True)
    return {"palabra": palabra, "estado": "postulada" if applied else "candidata", "evidencia": str(img), "score": round(score,1)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cola", required=True)
    ap.add_argument("--status", default="STATUS.md")
    args = ap.parse_args()

    if not need_env():
        append_status(args.status, "Lici", [{"estado": "skip", "motivo": "faltan_credenciales"}]); return 0

    resultados = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            login(page)
            for item in read_queue_csv(args.cola):
                palabra = (item.get("palabra") or "").strip()
                if not palabra: continue
                try:
                    match_min = float(item.get("match_min") or 70)
                except: match_min = 70.0
                try:
                    r = search_and_apply(page, palabra, match_min)
                except PWTimeout:
                    r = {"palabra": palabra, "estado": "error", "motivo": "timeout"}
                except Exception as e:
                    log.exception("error"); r = {"palabra": palabra, "estado": "error", "motivo": str(e)}
                resultados.append(r)
        finally:
            page.close(); browser.close()

    append_status(args.status, "Lici", resultados)
    write_json_log(LOGS / "lici.json", resultados)
    return 0

if __name__ == "__main__":
    sys.exit(main())

