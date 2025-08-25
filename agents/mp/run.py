#!/usr/bin/env python3

"""
Vendedor360 – agente de Mercado Público

Este script automatiza la detección y postulación de órdenes de compra en
Mercado Público. La implementación original solo usaba la variable de
entorno ``MP_TICKET`` e ignoraba ``MP_SESSION_COOKIE`` durante la
petición de órdenes, lo que ocasionaba que no se recuperaran
postulaciones cuando solo se configuraba la cookie. Además, la lógica
de coincidencia era rígida: exigía un 100 % de coincidencia entre
las palabras clave y el nombre de la orden de compra. Esta versión
aborda ambos problemas:

* Se introduce una función ``get_mp_token()`` que toma el ticket si
  existe y, de lo contrario, utiliza la cookie. De esta forma, la
  llamada a la API funcionará siempre que al menos una credencial esté
  configurada.
* Se reemplaza ``match_100()`` por ``match_score()``, que calcula el
  porcentaje de coincidencia entre las palabras clave y el nombre de la
  orden. Cada entrada de la cola puede establecer un umbral
  ``match_min`` (por defecto 100 %) para considerar una orden como
  candidata.
"""

import os
import sys
import argparse
import logging
import pathlib
from datetime import datetime, timedelta
import requests

from agents.common.queue import read_queue_csv
from agents.common.filters import load_exclusions, contains_exclusion
from agents.common.status import append_status, write_json_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mp")

# Directorio base del proyecto para cargar exclusiones
BASE = pathlib.Path(__file__).resolve().parent.parent
EXCLUS = load_exclusions(BASE)

def get_mp_token() -> str | None:
    """
    Obtiene el token para consumir la API de Mercado Público.

    Prefiere ``MP_TICKET`` pero, si no existe, utiliza
    ``MP_SESSION_COOKIE``. Esta función se utiliza tanto para validar
    las credenciales como para pasar el parámetro correcto a las
    peticiones.
    """
    return os.getenv("MP_TICKET") or os.getenv("MP_SESSION_COOKIE")


def need_env() -> bool:
    """
    Devuelve ``True`` si existe alguna credencial válida para Mercado
    Público. Si ambas variables están vacías, devuelve ``False`` y el
    agente registrará un estado de omisión.
    """
    return bool(get_mp_token())


def fetch_agiles(token: str | None, since_hours: int = 24) -> list[dict]:
    """
    Recupera órdenes de compra recientes de Mercado Público.

    Parameters
    ----------
    token:
        Token o cookie de acceso. Si es ``None`` o vacío, la función
        devuelve una lista vacía.
    since_hours:
        Número de horas hacia atrás desde el momento actual para
        recuperar órdenes. Por defecto, 24 horas.

    Returns
    -------
    list[dict]
        Una lista de órdenes de compra. En caso de error de red, se
        devuelve una lista vacía y se registra un aviso en el log.
    """
    if not token:
        return []
    desde = (datetime.utcnow() - timedelta(hours=since_hours)).strftime("%Y-%m-%d")
    url = (
        "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json"
        f"?fecha={desde}&ticket={token}"
    )
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        d = r.json()
        return d.get("Listado", []) or d.get("Ordenes", []) or []
    except Exception as e:  # pylint: disable=broad-except
        log.warning("MP fetch error: %s", e)
        return []


def match_score(nombre: str, palabra: str) -> float:
    """
    Calcula el porcentaje de coincidencia entre una cadena ``nombre`` y
    una palabra clave ``palabra``.

    La función separa ``palabra`` por espacios y comprueba cuántos de
    esos tokens están presentes como subcadenas en ``nombre`` (sin
    distinguir mayúsculas/minúsculas). Devuelve un valor de 0 a 100.
    """
    nombre_lower = (nombre or "").lower()
    tokens = [t for t in (palabra or "").lower().split() if t]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in nombre_lower)
    return hits * 100.0 / len(tokens)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cola", required=True)
    ap.add_argument("--status", default="STATUS.md")
    ap.add_argument("--since-hours", default="24")
    args = ap.parse_args()

    # Verificar credenciales
    if not need_env():
        append_status(
            args.status,
            "Mercado Público",
            [{"estado": "skip", "motivo": "faltan_credenciales"}],
        )
        return 0

    token = get_mp_token()
    agiles = fetch_agiles(token, int(args.since_hours))
    queue = read_queue_csv(args.cola)
    res: list[dict] = []

    for oc in agiles:
        nombre = (oc.get("Nombre", "") or oc.get("Descripcion", "")).strip()
        # Filtrar por palabras excluidas (anti-logo, etc.)
        if contains_exclusion(nombre, EXCLUS):
            res.append({"oc": oc.get("CodigoOC"), "estado": "omitida", "motivo": "exclusion_logo"})
            continue

        # Calcular coincidencia con cada entrada de la cola. Se acepta si
        # el porcentaje es igual o superior a ``match_min`` (por defecto 100 %).
        matched = False
        for entry in queue:
            palabra = entry.get("palabra", "") or entry.get("titulo", "")
            # Algunos CSV pueden no tener el campo 'match_min', asumimos 100
            try:
                match_min = float(entry.get("match_min", 100) or 100)
            except ValueError:
                match_min = 100.0
            score = match_score(nombre, palabra)
            if score >= match_min:
                matched = True
                break
        if not matched:
            res.append({"oc": oc.get("CodigoOC"), "estado": "omitida", "motivo": "no_match"})
            continue
        # La orden cumple con los criterios
        res.append({"oc": oc.get("CodigoOC"), "estado": "candidata", "motivo": "match_ok"})

    # Escribir resultados en STATUS.md y en log JSON
    append_status(args.status, "Mercado Público", res)
    write_json_log("logs/mp.json", res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
