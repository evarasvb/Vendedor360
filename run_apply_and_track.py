#!/usr/bin/env python3
"""
Script de automatización para WherEX con funciones de postulación y seguimiento.

Este script extiende la funcionalidad básica del archivo original `agents/wherex/run.py` del
repositorio Vendedor360. Además de iniciar sesión en el portal de proveedores de
WherEX y buscar licitaciones en función de una lista de palabras clave, intenta
realizar la postulación a la licitación y ofrece un punto de entrada para
consultar posteriormente el estado de las postulaciones.

La función principal `run_item` realiza los siguientes pasos:
1. Navega a `https://proveedores.wherex.com/licitaciones`.
2. Introduce la palabra clave en el campo de búsqueda y pulsa Enter.
3. Si existen resultados, abre la primera tarjeta de licitación.
4. Verifica exclusiones sobre la palabra y el título de la licitación.
5. Llama a `apply_for_bid` para intentar postular a la licitación.
6. Captura una captura de pantalla de la página de detalles como evidencia.

La función `apply_for_bid` busca botones comunes de postulación como "Postular",
"Participar" o "Enviar". Si los encuentra, ejecuta los clics necesarios para
finalizar la postulación. Dado que el flujo exacto puede variar entre
licitaciones, los selectores se implementan de forma robusta y con manejo de
errores silencioso para no interrumpir el proceso general.

La función `track_applications` es un marcador de posición que puede
personalizarse para navegar al módulo de historial de licitaciones y recopilar
estados (por ejemplo, "En evaluación", "Adjudicada", "No adjudicada"). Por
defecto, la función no hace nada, pero se deja preparada para futuras
implementaciones.
"""

import os
import sys
import pathlib
import argparse
import logging
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Page

from agents.common.queue import read_queue_csv
from agents.common.filters import load_exclusions, contains_exclusion
from agents.common.status import append_status, write_json_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wherex-apply-track")

ART = pathlib.Path("artifacts/wherex"); LOGS = pathlib.Path("logs")
BASE = pathlib.Path(__file__).resolve().parent.parent  # se asume estructura de repositorio
EXCLUS = load_exclusions(BASE)


def need_env() -> bool:
    """Comprueba que las credenciales de WherEX estén presentes en el entorno."""
    return os.getenv("WHEREX_USER") and os.getenv("WHEREX_PASS")


def login(page: Page, user: str, pwd: str) -> None:
    """Inicia sesión en WherEX con las credenciales proporcionadas."""
    page.goto("https://login.wherex.com", wait_until="domcontentloaded")
    page.get_by_label("Correo").fill(user)
    page.get_by_label("Contraseña").fill(pwd)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_load_state("networkidle")


def apply_for_bid(page: Page) -> bool:
    """
    Intenta postular a la licitación actualmente abierta.

    Busca botones comunes de acción como "Postular", "Participar", "Enviar" y
    realiza clics en ellos. Devuelve True si se hizo clic en un botón de
    postulación, False en caso contrario.
    """
    applied = False
    try:
        # Intentar encontrar un botón de postulación con nombres habituales.
        for label in ["Postular", "Participar", "Enviar", "Postulación", "Participar en licitación"]:
            try:
                btn = page.get_by_role("button", name=label)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_load_state("networkidle")
                    # Intentar confirmar si hay paso adicional
                    for confirm_label in ["Confirmar", "Sí", "Enviar", "Enviar oferta", "Aceptar"]:
                        try:
                            confirm_btn = page.get_by_role("button", name=confirm_label)
                            if confirm_btn and confirm_btn.is_visible():
                                confirm_btn.click()
                                page.wait_for_load_state("networkidle")
                                break
                        except Exception:
                            continue
                    # Verificar indicadores de éxito en la UI
                    success_locators = [
                        page.get_by_text("Postulación enviada"),
                        page.get_by_text("Oferta enviada"),
                        page.get_by_text("Participando"),
                        page.get_by_role("button", name="Retirar oferta"),
                    ]
                    for loc in success_locators:
                        try:
                            if loc.is_visible():
                                applied = True
                                break
                        except Exception:
                            continue
                    # Si no se detectó indicador, mantener applied en False
                    break
            except Exception:
                continue
    except Exception as exc:
        log.debug(f"Error al intentar postular: {exc}")
    return applied


def track_applications(page: Page) -> list[dict]:
    """
    Punto de entrada para realizar seguimiento de las postulaciones.

    Esta función puede navegar al módulo de historial de licitaciones y
    recopilar información sobre cada licitación postulada, como estado actual,
    fecha de cierre, adjudicatario, etc. Por defecto no realiza acciones y
    devuelve una lista vacía. Se deja como referencia para futuras
    implementaciones.
    """
    resultados = []
    # TODO: Implementar navegación al historial y extracción de estados.
    return resultados


def run_item(page: Page, palabra: str) -> dict:
    """
    Ejecuta el flujo de búsqueda y postulación para una palabra clave.

    Devuelve un diccionario con la palabra clave, el estado (por ejemplo,
    'sin_resultados', 'omitido', 'postulada', 'postulacion_realizada') y la ruta
    de la evidencia si corresponde. Si se omite por exclusión, se indica el
    motivo.
    """
    # Verificar exclusiones por palabra antes de buscar.
    if contains_exclusion(palabra, EXCLUS):
        return {"palabra": palabra, "estado": "omitido", "motivo": "exclusion_logo"}
    # Ir a la página de búsqueda de licitaciones.
    page.goto("https://proveedores.wherex.com/licitaciones", wait_until="domcontentloaded")
    page.get_by_placeholder("Buscar").fill(palabra)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    cards = page.locator(".card-licitacion").all()
    if not cards:
        return {"palabra": palabra, "estado": "sin_resultados"}
    # Obtener el título de la primera licitación y comprobar exclusiones por título.
    titulo = (cards[0].text_content() or "").lower()
    if contains_exclusion(titulo, EXCLUS):
        return {"palabra": palabra, "estado": "omitido", "motivo": "exclusion_logo_titulo"}
    # Abrir la licitación.
    cards[0].click()
    page.wait_for_load_state("networkidle")
    # Intentar postular.
    did_apply = apply_for_bid(page)
    # Capturar evidencia.
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ART.mkdir(parents=True, exist_ok=True)
    img_path = ART / f"wherex_{ts}.png"
    page.screenshot(path=str(img_path), full_page=True)
    estado = "postulacion_realizada" if did_apply else "buscada"
    resultado = {"palabra": palabra, "estado": estado, "evidencia": str(img_path)}
    return resultado


def main() -> int:
    """Punto de entrada del script."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--cola", required=True, help="Ruta al archivo CSV con palabras clave (columna 'palabra')")
    ap.add_argument("--status", default="STATUS.md", help="Archivo donde se escribirán los estados de ejecución")
    ap.add_argument("--track", action="store_true", help="Si se especifica, realiza seguimiento de las postulaciones al final")
    args = ap.parse_args()

    if not need_env():
        append_status(args.status, "WherEX", [{"estado": "error", "motivo": "faltan_credenciales"}])
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
            # Si se solicita seguimiento, invocar función de seguimiento.
            if args.track:
                try:
                    seguimiento = track_applications(page)
                    resultados.extend(seguimiento)
                except Exception:
                    log.exception("error_seguimiento")
        finally:
            page.close()
            browser.close()

    append_status(args.status, "WherEX", resultados)
    write_json_log(LOGS / "wherex_apply_track.json", resultados)
    return 0


if __name__ == "__main__":
    sys.exit(main())