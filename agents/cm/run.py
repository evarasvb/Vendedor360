#!/usr/bin/env python3
import os, sys, argparse, pathlib, logging, csv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from agents.common.status import append_status, write_json_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cm")
ART = pathlib.Path("artifacts/cm"); LOGS = pathlib.Path("logs")

def need_env(): return os.getenv("CM_USER") and os.getenv("CM_PASS")

def login(page):
    page.goto("https://www.conveniomarco.cl/login", wait_until="domcontentloaded")
    page.get_by_label("Usuario").fill(os.environ["CM_USER"])
    page.get_by_label("Contraseña").fill(os.environ["CM_PASS"])
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_load_state("networkidle")

def process_item(page, marca, codigo, descripcion, precio, region, stock, imagenes):
    page.goto("https://www.conveniomarco.cl/mi-catalogo/oficina", wait_until="domcontentloaded")
    page.get_by_placeholder("Buscar").fill(codigo or (descripcion or "")[:20])
    page.keyboard.press("Enter"); page.wait_for_timeout(1200)
    created_or_updated = "actualizado"
    try:
        if page.locator(".resultado-item").count() == 0:
            page.get_by_role("button", name="Crear producto").click()
            created_or_updated = "creado"
        page.get_by_label("Marca").fill(marca)
        page.get_by_label("Código").fill(codigo)
        page.get_by_label("Descripción").fill((descripcion or "")[:180])
        if precio: page.get_by_label("Precio").fill(str(int(float(precio))))
        page.get_by_label("Stock").fill(str(int(stock or 0)))
        page.get_by_label("Regiones").fill(region)
        # TODO: implementar uploader de imágenes según componente real
        page.get_by_role("button", name="Guardar").click()
        page.wait_for_load_state("networkidle")
    except Exception as e:
        log.exception("cm_error"); return {"marca": marca, "codigo": codigo, "estado": "error", "motivo": str(e)}

    ART.mkdir(parents=True, exist_ok=True)
    shot = ART / f"cm_{marca}_{codigo}.png"
    page.screenshot(path=str(shot), full_page=True)
    return {"marca": marca, "codigo": codigo, "estado": created_or_updated, "evidencia": str(shot)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--status", default="STATUS.md")
    args = ap.parse_args()
    if not need_env():
        append_status(args.status, "Convenio Marco – Oficina", [{"estado":"skip","motivo":"faltan_credenciales"}]); return 0

    rows = list(csv.DictReader(open(args.csv, encoding="utf-8")))
    targets = {"BARRILITO","KENSINGTON","REXEL"}
    resultados=[]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True); page = browser.new_page()
        try:
            login(page)
            for r in rows:
                marca = (r.get("marca") or "").upper().strip()
                if marca not in targets: continue
                res = process_item(page,
                    marca.title(), r.get("codigo",""), r.get("descripcion",""),
                    r.get("precio",""), r.get("region","RM;V;VIII"), r.get("stock","100"),
                    r.get("imagenes",""))
                resultados.append(res)
        finally:
            page.close(); browser.close()
    append_status(args.status, "Convenio Marco – Oficina", resultados)
    write_json_log(LOGS / "cm.json", resultados)
    return 0

if __name__ == "__main__":
    sys.exit(main())

