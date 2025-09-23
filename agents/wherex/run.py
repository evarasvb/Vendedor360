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
    # Evidencia antes de intentar postular
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ART.mkdir(parents=True, exist_ok=True)
    img_before = ART / f"wherex_before_{ts}.png"
    page.screenshot(path=str(img_before), full_page=True)
    
    # Intentar postular y verificar resultado
    did_click = _attempt_application(page)
    did_verify = _verify_application(page)
    
    # Evidencia después del intento/verificación
    img_after = ART / f"wherex_after_{ts}.png"
    page.screenshot(path=str(img_after), full_page=True)
    
    estado = "postulada" if did_verify else ("intento_no_confirmado" if did_click else "sin_postulacion")
    return {
        "palabra": palabra,
        "estado": estado,
        "evidencia_antes": str(img_before),
        "evidencia_despues": str(img_after),
    }

def _attempt_application(page) -> bool:
    """Intenta hacer clic en controles típicos de postulación.

    Devuelve True si se detectó y clickeó algún control de postulación.
    """
    button_labels = [
        "Postular",
        "Participar",
        "Enviar",
        "Enviar oferta",
        "Postulación",
        "Participar en licitación",
    ]
    for label in button_labels:
        try:
            btn = page.get_by_role("button", name=label)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_load_state("networkidle")
                # Confirmaciones adicionales frecuentes
                for confirm_label in ["Confirmar", "Sí", "Aceptar", "Enviar", "Enviar oferta"]:
                    try:
                        cbtn = page.get_by_role("button", name=confirm_label)
                        if cbtn and cbtn.is_visible():
                            cbtn.click()
                            page.wait_for_load_state("networkidle")
                            break
                    except Exception:
                        continue
                page.wait_for_timeout(700)
                return True
        except Exception:
            continue
    # Fallback por texto genérico
    try:
        generic = page.locator("text=/Postular|Participar|Enviar/i").first
        if generic and generic.is_visible():
            generic.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
            return True
    except Exception:
        pass
    return False

def _verify_application(page) -> bool:
    """Verifica en la interfaz si la postulación quedó registrada."""
    indicators = [
        # Botones/acciones visibles cuando ya estás participando
        "text=/Retirar(\s+postulaci[oó]n)?/i",
        "text=/Editar(\s+oferta)?/i",
        # Mensajes/estados comunes
        "text=/Oferta\s+enviada/i",
        "text=/Postulaci[oó]n\s+enviada/i",
        "text=/Ya\s+est[aá]s\s+participando/i",
        "text=/Ya\s+postulaste/i",
        "text=/Participando/i",
        "text=/Estado\s*:\s*Postulad[ao]/i",
    ]
    try:
        for sel in indicators:
            loc = page.locator(sel).first
            if loc and loc.is_visible():
                return True
    except Exception:
        return False
    return False

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
