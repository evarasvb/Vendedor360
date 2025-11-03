#!/usr/bin/env python3
import os, sys, pathlib, argparse, logging, json
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

def get_keywords_from_env():
    """Read keywords from SENEGOCIA_KEYWORDS environment variable (comma-separated)."""
    env_keywords = os.getenv("SENEGOCIA_KEYWORDS")
    if not env_keywords:
        return None
    keywords = [kw.strip() for kw in env_keywords.split(",") if kw.strip()]
    return [{"palabra": kw} for kw in keywords]

def need_env() -> bool:
    return os.getenv("SENEGOCIA_USER") and os.getenv("SENEGOCIA_PASS")

def login(page, user, pwd) -> None:
    page.goto("https://portal.senegocia.com", wait_until="domcontentloaded")
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
    ap.add_argument("--cola", required=False, default=None)
    ap.add_argument("--status", default="STATUS.md")
    args = ap.parse_args()
    
    if not need_env():
        append_status(args.status, "Senegocia", [{"estado": "skip", "motivo": "faltan_credenciales"}])
        return 0
    
    # Determine source of keywords
    keywords_from_env = get_keywords_from_env()
    if keywords_from_env:
        queue = keywords_from_env
    elif args.cola:
        queue = read_queue_csv(args.cola)
    else:
        log.error("Error: either SENEGOCIA_KEYWORDS environment variable or --cola parameter must be provided")
        append_status(args.status, "Senegocia", [{"estado": "error", "motivo": "no_keywords_source"}])
        return 1
    
    log.info(f"Processing {len(queue)} keyword(s)")
    results = []
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            login(page, os.getenv("SENEGOCIA_USER"), os.getenv("SENEGOCIA_PASS"))
            
            for item in queue:
                palabra = item.get("palabra", "")
                if not palabra:
                    continue
                log.info(f"Processing: {palabra}")
                try:
                    res = run_item(page, palabra)
                    results.append(res)
                    log.info(f"Result for {palabra}: {res.get('estado')}")
                except Exception as e:
                    log.error(f"Error processing {palabra}: {e}")
                    results.append({"palabra": palabra, "estado": "error", "motivo": str(e)})
        
        finally:
            browser.close()
    
    # Write results to STATUS.md
    append_status(args.status, "Senegocia", results)
    
    # Export JSON for dashboard
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = pathlib.Path("artifacts") / f"senegocia_{timestamp}.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    stats = {
        "postulada": sum(1 for r in results if r.get("estado") == "postulada"),
        "omitido": sum(1 for r in results if r.get("estado") == "omitido"),
        "error": sum(1 for r in results if r.get("estado") == "error")
    }
    
    json_data = {
        "timestamp": timestamp,
        "total_keywords": len(queue),
        "results": results,
        "stats": stats
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    log.info(f"JSON export saved to {json_path}")
    log.info(f"Stats: {stats}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
