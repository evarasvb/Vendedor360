from pathlib import Path
from typing import Dict, Optional
from playwright.sync_api import Page
import time

MP_HOME = "https://buscador.mercadopublico.cl/compra-agil"

def _fill_input(page: Page, selector: str, value: Optional[str]):
    if value:
        page.locator(selector).fill(str(value))

def login_if_needed(page: Page, storage_state_path: str = "storage_state.json"):
    """
    Usa estado persistente si existe. Si no, asume sesión ya abierta vía cookie o ticket.
    Ajusta este método con tus selectores reales de sesión iniciada.
    """
    page.goto(MP_HOME, wait_until="domcontentloaded")
    return

def postular(row: Dict[str, str], page: Page) -> None:
    """
    row esperado:
      opportunity_id, sku, precio_sugerido, ficha_path, foto_path, coti_path
    """
    opp = row.get("opportunity_id", "").strip()
    if not opp:
        return

    # 1) Abrir ficha de oportunidad
    page.goto(f"{MP_HOME}/detalle/{opp}", wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    # 2) Ir a formulario de postulación (ajusta selectores reales)
    page.get_by_role("button", name="Postular").click()
    page.wait_for_load_state("domcontentloaded")

    # 3) Completar formulario básico
    _fill_input(page, 'input[name="sku"]', row.get("sku"))
    _fill_input(page, 'input[name="precio"]', row.get("precio_sugerido"))

    # 4) Adjuntos (si existen)
    def _attach(sel: str, path_key: str):
        p = row.get(path_key)
        if p and Path(p).exists():
            page.locator(sel).set_input_files(p)
    _attach('input[type="file"][name="ficha"]', "ficha_path")
    _attach('input[type="file"][name="foto"]', "foto_path")
    _attach('input[type="file"][name="cotizacion"]', "coti_path")

    # 5) Enviar
    page.get_by_role("button", name="Enviar oferta").click()
    page.wait_for_selector("text=Oferta enviada", timeout=15000)
    time.sleep(0.5)
