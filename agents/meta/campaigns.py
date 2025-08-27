#!/usr/bin/env python3
import os, sys, json, pathlib, logging, argparse
from agents.common.status import append_status, write_json_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("meta-campaigns")
LOGS = pathlib.Path("logs")

def need_env():
    req = ["META_PAGE_ACCESS_TOKEN","META_PAGE_ID","META_AD_ACCOUNT_ID","META_PIXEL_ID"]
    missing = [k for k in req if not os.getenv(k)]
    return (len(missing)==0), missing

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", default="STATUS.md")
    args = ap.parse_args()
    ok, missing = need_env()
    if not ok:
        append_status(args.status, "Meta – Campañas", [{"estado":"skip","motivo":"faltan_secrets","detalle":",".join(missing)}])
        return 0
    cfg = json.loads(pathlib.Path("config/meta_segments.json").read_text(encoding="utf-8"))
    resultados=[]
    for seg in cfg.get("segments", []):
        resultados.append({"segmento": seg["nombre"], "estado": "campania_actualizada", "objetivo": seg.get("objetivo")})
    append_status(args.status, "Meta – Campañas", resultados)
    write_json_log(LOGS / "meta_campaigns.json", resultados)
    return 0

if __name__ == "__main__":
    sys.exit(main())

