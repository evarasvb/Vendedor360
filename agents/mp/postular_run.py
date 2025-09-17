#!/usr/bin/env python3
import csv
import argparse
from playwright.sync_api import sync_playwright
from agents.mp.postular import postular, login_if_needed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="queues/postulaciones.csv")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--storage", default="storage_state.json")
    args = ap.parse_args()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="",
            headless=args.headless,
            storage_state=args.storage if args.storage else None,
        )
        page = context.pages[0] if context.pages else context.new_page()
        login_if_needed(page, args.storage)

        with open(args.csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                auto = (row.get("send", "").lower() == "s")
                if auto:
                    postular(row, page)
        context.storage_state(path=args.storage)
        context.close()

if __name__ == "__main__":
    main()
