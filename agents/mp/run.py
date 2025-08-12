#!/usr/bin/env python3
import os, sys, argparse, logging, pathlib
from datetime import datetime, timedelta
import requests
from agents.common.queue import read_queue_csv
from agents.common.filters import load_exclusions, contains_exclusion
from agents.common.status import append_status, write_json_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mp")
BASE = pathlib.Path(__file__).resolve().parent.parent
EXCLUS = load_exclusions(BASE)

def need_env() -> bool:
    return os.getenv("MP_TICKET") or os.getenv("MP_SESSION_COOKIE")

def fetch_agiles(ticket: str | None, since_hours: int = 24) -> list[dict]:
    if not ticket:
        return []
    desde = (datetime.utcnow() - timedelta(hours=since_hours)).strftime("%Y-%m-%d")
    url = (
        "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json"
        f"?fecha={desde}&ticket={ticket}"
    )
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        d = r.json()
        return d.get("Listado", []) or d.get("Ordenes", []) or []
    except Exception as e:  # pylint: disable=broad-except
        log.warning("MP fetch error: %s", e)
        return []

def match_100(nombre: str, palabra: str) -> bool:
    n = (nombre or "").lower()
    return all(p in n for p in (palabra or "").lower().split())

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cola", required=True)
    ap.add_argument("--status", default="STATUS.md")
    ap.add_argument("--since-hours", default="24")
    args = ap.parse_args()

    if not need_env():
        append_status(
            args.status,
            "Mercado Público",
            [{"estado": "skip", "motivo": "faltan_ticket_cookie"}],
        )
        return 0

    ticket = os.getenv("MP_TICKET")
    agiles = fetch_agiles(ticket, int(args.since_hours))
    queue = read_queue_csv(args.cola)
    res = []
    for oc in agiles:
        nombre = (oc.get("Nombre", "") or oc.get("Descripcion", "")).strip()
        if contains_exclusion(nombre, EXCLUS):
            res.append({"oc": oc.get("CodigoOC"), "estado": "omitida", "motivo": "exclusion_logo"})
            continue
        if not any(match_100(nombre, i.get("palabra", "")) for i in queue):
            res.append({"oc": oc.get("CodigoOC"), "estado": "omitida", "motivo": "no_100_match"})
            continue
        res.append({"oc": oc.get("CodigoOC"), "estado": "candidata", "motivo": "match_ok"})
    append_status(args.status, "Mercado Público", res)
    write_json_log("logs/mp.json", res)
    return 0

if __name__ == "__main__":
    sys.exit(main())
