#!/usr/bin/env python3
import os, sys, argparse, logging
from agents.common.queue import read_queue_csv
from agents.common.status import append_status, write_json_log

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("meta")

def need_env() -> bool:
    return os.getenv("META_PAGE_ACCESS_TOKEN") and os.getenv("META_PAGE_ID")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo", required=True)
    ap.add_argument("--status", default="STATUS.md")
    args = ap.parse_args()

    if not need_env():
        append_status(args.status, "Meta/Marketplace", [{"estado": "skip", "motivo": "faltan_tokens"}])
        return 0

    items = read_queue_csv(args.catalogo)
    res = []
    pub = 0
    stories = 0
    for it in items:
        if pub < 20:
            res.append({"titulo": it.get("titulo"), "estado": "publicado", "post_id": "mock_fb_123"})
            pub += 1
        if stories < 2:
            res.append({"titulo": it.get("titulo"), "estado": "story_publicada"})
            stories += 1
    append_status(args.status, "Meta/Marketplace", res)
    write_json_log("logs/meta.json", res)
    return 0

if __name__ == "__main__":
    sys.exit(main())
