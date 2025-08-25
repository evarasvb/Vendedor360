#!/usr/bin/env python3
import os, sys, argparse, logging
from agents.common.status import append_status, write_json_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("linkedin")

TEMPLATE = "Hoy comparto un tip de #MercadoPúblico y #IA para PyMEs: {idea}."
IDEAS = [
    "usa checklist de match 100%",
    "automatiza compras ágiles 24h",
    "registra evidencia de cada postulación",
]

def need_env() -> bool:
    return os.getenv("LINKEDIN_ACCESS_TOKEN")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", default="STATUS.md")
    args = ap.parse_args()

    if not need_env():
        append_status(args.status, "LinkedIn", [{"estado": "skip", "motivo": "falta_token"}])
        return 0

    texto = TEMPLATE.format(idea=IDEAS[0])
    res = [{"estado": "publicado", "post_id": "mock_ln_123", "texto": texto}]
    append_status(args.status, "LinkedIn", res)
    write_json_log("logs/linkedin.json", res)
    return 0

if __name__ == "__main__":
    sys.exit(main())
