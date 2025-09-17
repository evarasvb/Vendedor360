#!/usr/bin/env python3
import csv
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from agents.mp.postular import postular, login_if_needed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="queues/postulaciones.csv")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--storage", default="storage_state.json")
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        storage_path = Path(args.storage)
        context = browser.new_context(
            storage_state=str(storage_path) if storage_path.is_file() else None,
        )
        page = context.new_page()
        login_if_needed(page, args.storage)

        with open(args.csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                auto = (row.get("send", "").lower() == "s")
                if auto:
                    postular(row, page)
        if args.storage:
            parent = storage_path.parent
            if str(parent) not in ("", "."):
                parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(storage_path))
        context.close()
        browser.close()

if __name__ == "__main__":
    main()
