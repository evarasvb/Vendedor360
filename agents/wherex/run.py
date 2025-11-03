#!/usr/bin/env python3
import os, sys, pathlib, argparse, logging, json
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

def get_keywords_from_env():
    """Read keywords from WHEREX_KEYWORDS environment variable (comma-separated)"""
    env_keywords = os.getenv("WHEREX_KEYWORDS")
    if env_keywords:
        keywords = [k.strip() for k in env_keywords.split(",") if k.strip()]
        return [{"palabra": k} for k in keywords]
    return None

def login(page, user, pwd):
    page.goto("https://login.wherex.com", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.locator('input[type="email"]').first.fill(user)
    page.locator('input[type="password"]').first.fill(pwd)
    page.keyboard.press('Enter')
    page.wait_for_load_state("networkidle")

def run_item(page, palabra: str) -> dict:
    if contains_exclusion(palabra, EXCLUS):
        return {"palabra": palabra, "estado": "omitido", "motivo": "exclusion_logo"}
    try:
        log.info(f"Searching '{palabra}'...")
        search_page = f"https://www.wherex.com/search?q={palabra}"
        page.goto(search_page, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        
        # Wait for results container
        results_present = False
        try:
            page.wait_for_selector("div[class*='result'], article, .search-results", timeout=10000)
            results_present = True
        except PWTimeout:
            log.warning(f"No results container found for '{palabra}'")
            return {"palabra": palabra, "estado": "error", "motivo": "no_results"}
        
        if not results_present:
            return {"palabra": palabra, "estado": "error", "motivo": "no_results"}
        
        # Take screenshots
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ss_name = f"{ts}_{palabra.replace(' ','_')}.png"
        ss_path = ART / ss_name
        page.screenshot(path=str(ss_path), full_page=True)
        log.info(f"Screenshot saved: {ss_path}")
        
        return {"palabra": palabra, "estado": "ok", "screenshot": str(ss_path)}
    except Exception as e:
        log.error(f"Error with '{palabra}': {e}")
        return {"palabra": palabra, "estado": "error", "motivo": str(e)}

def main():
    parser = argparse.ArgumentParser(description="WhereX agent")
    parser.add_argument("--queue", help="Path to CSV queue file")
    parser.add_argument("--keywords", help="Comma-separated list of keywords")
    parser.add_argument('--status', help='Path to STATUS.md file for status updates')
    args = parser.parse_args()
    
    if not need_env():
        log.error("Missing WHEREX_USER or WHEREX_PASS environment variables")
        sys.exit(1)
    
    user = os.getenv("WHEREX_USER")
    pwd = os.getenv("WHEREX_PASS")
    
    # Determine keyword source
    if args.keywords:
        items = [{"palabra": k.strip()} for k in args.keywords.split(",") if k.strip()]
    elif args.queue:
        items = read_queue_csv(args.queue)
    else:
        items = get_keywords_from_env()
        if not items:
            log.error("No keywords provided via --keywords, --queue, or WHEREX_KEYWORDS env")
            sys.exit(1)
    
    if not items:
        log.error("No valid keywords to process")
        sys.exit(1)
    
    ART.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            login(page, user, pwd)
            log.info("Login successful")
        except Exception as e:
            log.error(f"Login failed: {e}")
            browser.close()
            sys.exit(1)
        
        for item in items:
            palabra = item.get("palabra", "").strip()
            if not palabra:
                continue
            result = run_item(page, palabra)
            results.append(result)
            
            if args.status:
                append_status("wherex", result, status_file=args.status)
            else:
                append_status("wherex", result)
        
        browser.close()
    
    log.info(f"Processed {len(results)} keywords")
    
    # Write JSON log to logs directory (existing functionality)
    log_path = LOGS / f"wherex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    write_json_log(log_path, results)
    log.info(f"Log written to {log_path}")
    
    # Export JSON to artifacts directory for dashboard
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_path = pathlib.Path("artifacts") / f"wherex_{timestamp}.json"
    
    # Calculate stats
    success_count = sum(1 for r in results if r.get("estado") == "ok")
    error_count = sum(1 for r in results if r.get("estado") == "error")
    skip_count = sum(1 for r in results if r.get("estado") == "omitido")
    
    export_data = {
        "timestamp": timestamp,
        "total_keywords": len(items),
        "keywords_processed": len(results),
        "results": results,
        "stats": {
            "success_count": success_count,
            "error_count": error_count,
            "skip_count": skip_count
        }
    }
    
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    log.info(f"JSON export saved to {export_path}")

if __name__ == "__main__":
    main()
