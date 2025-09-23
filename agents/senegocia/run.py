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

def _verify_postulation(page) -> bool:
    try:
        for label in ["Participando", "Postulado", "Ya estás participando", "Oferta enviada", "Inscrito"]:
            el = page.get_by_text(label)
            if el and el.is_visible():
                return True
        post_btn = page.get_by_role("button", name="Postular")
        if post_btn and not post_btn.is_visible():
            return True
    except Exception:
        pass
    return False

def apply_for_bid(page) -> tuple[bool, bool]:
    clicked = False
    confirmed = False
    try:
        for label in ["Postular", "Participar", "Enviar", "Inscribirse", "Manifestar Interés"]:
            try:
                btn = page.get_by_role("button", name=label)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_load_state("networkidle")
                    clicked = True
                    for confirm_label in ["Confirmar", "Sí", "Enviar", "Aceptar"]:
                        try:
                            confirm_btn = page.get_by_role("button", name=confirm_label)
                            if confirm_btn and confirm_btn.is_visible():
                                confirm_btn.click()
                                page.wait_for_load_state("networkidle")
                                break
                        except Exception:
                            continue
                    break
            except Exception:
                continue
        confirmed = _verify_postulation(page)
    except Exception:
        pass
    return clicked, confirmed

def run_item(page, palabra: str) -> dict:
    if contains_exclusion(palabra, EXCLUS):
        return {"palabra": palabra, "estado": "omitido", "motivo": "exclusion_logo"}
    page.goto("https://proveedores.senegocia.com/licitaciones", wait_until="domcontentloaded")
    page.get_by_placeholder("Buscar").fill(palabra)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    # Abrir primera licitación si existe
    cards = page.locator(".card-licitacion, .card.item, .licitacion-card").all()
    if not cards:
        return {"palabra": palabra, "estado": "sin_resultados"}
    cards[0].click()
    page.wait_for_load_state("networkidle")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ART.mkdir(parents=True, exist_ok=True)
    before_img = ART / f"senegocia_{ts}_before.png"
    page.screenshot(path=str(before_img), full_page=True)
    clicked, confirmed = apply_for_bid(page)
    after_img = ART / f"senegocia_{ts}_after.png"
    page.screenshot(path=str(after_img), full_page=True)
    estado = "postulacion_confirmada" if confirmed else ("postulacion_intentada" if clicked else "no_postulado")
    return {"palabra": palabra, "estado": estado, "evidencia_before": str(before_img), "evidencia_after": str(after_img)}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cola", required=True)
    ap.add_argument("--status", default="STATUS.md")
    args = ap.parse_args()

    if not need_env():
        append_status(args.status, "Senegocia", [{"estado": "skip", "motivo": "faltan_credenciales"}])
        return 0

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
