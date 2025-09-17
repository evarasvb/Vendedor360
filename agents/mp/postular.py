import os
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from playwright.sync_api import Page

MP_HOME = "https://buscador.mercadopublico.cl/compra-agil"

def _fill_input(page: Page, selector: str, value: Optional[str]):
    if value:
        page.locator(selector).fill(str(value))

def login_if_needed(page: Page, storage_state_path: str = "storage_state.json"):
    """Ensure the MP session is active before interacting with the site.

    If a storage state file already exists the context was initialised with it
    and we simply navigate to the home. Otherwise we attempt to restore a
    session using the cookie provided via ``MP_SESSION_COOKIE`` and, if
    available, store the ``MP_TICKET`` token in ``localStorage``.
    """

    storage_file = Path(storage_state_path)
    if storage_file.is_file():
        page.goto(MP_HOME, wait_until="domcontentloaded")
        return

    cookie_header = os.getenv("MP_SESSION_COOKIE", "").strip()
    if cookie_header:
        hostname = urlparse(MP_HOME).hostname or ""
        domain = f".{hostname}" if hostname and not hostname.startswith(".") else hostname
        if domain:
            cookies = []
            for chunk in cookie_header.split(";"):
                name, _, value = chunk.strip().partition("=")
                if name and value:
                    cookies.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": domain,
                        "path": "/",
                    })
            if cookies:
                page.context.add_cookies(cookies)

    page.goto(MP_HOME, wait_until="domcontentloaded")

    ticket = os.getenv("MP_TICKET")
    if ticket:
        page.evaluate("ticket => window.localStorage.setItem('MP_TICKET', ticket)", ticket)

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
    postular_btn = page.get_by_role("button", name="Postular")
    postular_btn.wait_for(state="visible", timeout=10000)
    postular_btn.click()
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
    enviar_btn = page.get_by_role("button", name="Enviar oferta")
    enviar_btn.wait_for(state="visible", timeout=10000)
    enviar_btn.click()
    page.wait_for_selector("text=Oferta enviada", timeout=15000)
    time.sleep(0.5)
