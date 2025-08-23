#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
contacts_scraper.py

This script crawls public Chilean government websites to extract contact
emails for institutions such as hospitals, municipalities, ministries,
and armed forces. It is designed to be integrated into the Vendedor360
automation suite but can also be executed standalone.  When run,
it reads a list of seed URLs from a CSV file and visits pages within
those domains, looking for email addresses.  Results are written
to a CSV file in the `data` directory (creating it if necessary).

Environment variables can be used to override default settings:

  - CONTACTS_OUT_CSV: path to output CSV file (default: data/contactos_estado.csv)
  - CONTACTS_SEEDS_CSV: path to CSV file containing seed URLs (default: agents/contacts/seeds.csv)
  - CONTACTS_MAX_PAGES: maximum pages to visit per seed (default: 80)
  - CONTACTS_MAX_DEPTH: maximum crawl depth (default: 2)
  - CONTACTS_DELAY: delay between requests in seconds (default: 0.6)
  - CONTACTS_SHEETS_ID: Google Sheets ID to upload results (optional)

The script also optionally uploads results to Google Sheets when
credentials are available and CONTACTS_SHEETS_ID is set.

Note: This scraper requires Playwright with Chromium installed.  See
`agents/contacts/requirements.txt` for the list of dependencies.
"""

import csv
import os
import re
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Regular expression to match email addresses
EMAIL_REGEX = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+@(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}\b",
    re.IGNORECASE,
)

# Prioritized keywords in link text to guide the crawler toward pages
# likely to contain contact information
PRIORITY_KEYWORDS = [
    "contacto",
    "contactos",
    "contact",
    "transparencia",
    "proveedores",
    "compras",
    "licitaciones",
    "quienes-somos",
    "equipo",
    "funcionarios",
    "directorio",
    "telefonos",
    "correo",
    "oficinas",
]

# Domain suffixes that are allowed; helps filter out personal email
# addresses from generic providers like Gmail or Hotmail
ALLOWED_DOMAIN_HINTS = [
    ".gob.cl",
    ".gov.cl",
    ".mil.cl",
    ".cl",
]

# Heuristic categories and keywords to assign a category to each institution
CATEGORIAS = {
    "Hospital / Salud": [
        "hospital",
        "salud",
        "servicio de salud",
        "cesfam",
        "minsal",
        "ssm",
    ],
    "Fuerzas Armadas / Orden": [
        "ejército",
        "ejercito",
        "armada",
        "fach",
        "carabineros",
        "pdi",
        "gendarmería",
        "mil",
    ],
    "Ministerio / Servicio Público": [
        "ministerio",
        "superintendencia",
        "servicio",
        "subsecretaría",
        "gobierno",
        "seremi",
    ],
    "Municipalidad": [
        "municipalidad",
        "ilustre municipalidad",
        "muni",
        "alcaldía",
        "alcaldia",
    ],
    "Educación Pública": [
        "universidad",
        "liceo",
        "colegio",
        "educación",
        "educacion",
    ],
}

# Default file locations
DEFAULT_OUT_CSV = Path("data/contactos_estado.csv")
DEFAULT_SEEDS_CSV = Path("agents/contacts/seeds.csv")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def guess_category(text: str) -> str:
    """Return a category for the given text based on keyword heuristics."""
    t = (text or "").lower()
    for cat, keys in CATEGORIAS.items():
        if any(k in t for k in keys):
            return cat
    return "Otro público"


def is_allowed_email(email: str) -> bool:
    """Return True if the email belongs to an allowed domain (non-personal)."""
    e = email.lower()
    # Exclude popular personal email providers
    blacklist = ["gmail.", "yahoo.", "hotmail.", "outlook.", "live."]
    if any(b in e for b in blacklist):
        return False
    return any(h in e for h in ALLOWED_DOMAIN_HINTS)


def is_same_site_or_child(seed_netloc: str, target_url: str) -> bool:
    """Check whether target_url belongs to the same domain or a subdomain."""
    try:
        t = urlparse(target_url)
        return bool(t.netloc) and (
            t.netloc == seed_netloc or t.netloc.endswith("." + seed_netloc)
        )
    except Exception:
        return False


def normalize_url(base: str, href: str) -> str:
    """Resolve relative href against base URL."""
    try:
        return urljoin(base, href)
    except Exception:
        return ""


def should_visit_link(href: str) -> bool:
    """Return True if the href should be visited."""
    if not href:
        return False
    if href.startswith(("mailto:", "tel:", "javascript:")):
        return False
    lower = href.lower()
    # Skip common binary file types
    if any(lower.endswith(ext) for ext in [
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".zip",
        ".rar",
    ]):
        return False
    return True


def score_link_text(text: str) -> int:
    """Assign a priority score based on the presence of keywords."""
    if not text:
        return 0
    t = text.lower()
    return sum(1 for kw in PRIORITY_KEYWORDS if kw in t)


def extract_emails(html: str) -> set[str]:
    """Return a set of email addresses found in the HTML."""
    return set(EMAIL_REGEX.findall(html or ""))


def extract_title(html: str) -> str:
    """Extract the page title from HTML."""
    try:
        soup = BeautifulSoup(html, "lxml")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
    except Exception:
        pass
    return ""


def crawl_site(play, start_url: str, max_pages: int, max_depth: int, per_domain_delay: float) -> list[dict]:
    """Crawl a single site and return a list of discovered contact rows."""
    browser = play.chromium.launch(headless=True)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    results: list[dict] = []
    visited: set[tuple[str, int]] = set()

    seed_netloc = urlparse(start_url).netloc
    queue: deque = deque()
    queue.append((start_url, 0, 0))  # (url, depth, priority)
    pages_visited = 0
    discovered_emails: set[tuple[str, str]] = set()

    while queue and pages_visited < max_pages:
        # Select the best link from a small window to prioritize contact pages
        best_idx, best_score = 0, -1
        for i in range(min(10, len(queue))):
            _, _, score = queue[i]
            if score > best_score:
                best_idx, best_score = i, score
        # Rotate queue to bring best to the left
        for _ in range(best_idx):
            queue.append(queue.popleft())

        current_url, depth, priority = queue.popleft()

        # Visit the page
        try:
            page.goto(current_url, wait_until="domcontentloaded", timeout=25000)
            time.sleep(per_domain_delay)
            html = page.content()
        except Exception:
            continue

        pages_visited += 1
        title = extract_title(html)
        emails = {e for e in extract_emails(html) if is_allowed_email(e)}

        for e in emails:
            key = (current_url, e)
            if key not in discovered_emails:
                discovered_emails.add(key)
                results.append(
                    {
                        "categoria": guess_category((title or "") + " " + seed_netloc),
                        "institucion": seed_netloc,
                        "email": e,
                        "titulo_pagina": title,
                        "url": current_url,
                    }
                )

        if depth < max_depth:
            try:
                soup = BeautifulSoup(html, "lxml")
                links: set[tuple[str, int]] = set()
                for a in soup.find_all("a", href=True):
                    href = normalize_url(current_url, a["href"])
                    if not should_visit_link(href):
                        continue
                    if not is_same_site_or_child(seed_netloc, href):
                        continue
                    prio = score_link_text(
                        (a.get_text(strip=True) or "") + " " + (a.get("href") or "")
                    )
                    links.add((href, prio))
                # Enqueue links sorted by descending priority
                for h, pr in sorted(links, key=lambda x: -x[1]):
                    if (h, depth + 1) not in visited:
                        visited.add((h, depth + 1))
                        queue.append((h, depth + 1, pr))
            except Exception:
                pass

    context.close()
    browser.close()
    return results


def main() -> None:
    """Entry point for running the scraper."""
    # Determine paths and limits from environment or defaults
    out_csv = Path(os.getenv("CONTACTS_OUT_CSV", str(DEFAULT_OUT_CSV)))
    seeds_path = Path(os.getenv("CONTACTS_SEEDS_CSV", str(DEFAULT_SEEDS_CSV)))
    max_pages = int(os.getenv("CONTACTS_MAX_PAGES", "80"))
    max_depth = int(os.getenv("CONTACTS_MAX_DEPTH", "2"))
    crawl_delay = float(os.getenv("CONTACTS_DELAY", "0.6"))

    if not seeds_path.exists():
        print(f"[ERROR] Seeds file {seeds_path} not found.")
        return

    # Read seed URLs
    seeds: list[str] = []
    with open(seeds_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            url = row[0].strip()
            if url and url.startswith("http"):
                seeds.append(url)

    all_rows: list[dict] = []
    with sync_playwright() as play:
        for s in seeds:
            try:
                print(f"[INFO] Crawling {s}")
                rows = crawl_site(
                    play,
                    start_url=s,
                    max_pages=max_pages,
                    max_depth=max_depth,
                    per_domain_delay=crawl_delay,
                )
                all_rows.extend(rows)
            except Exception as e:
                print(f"[WARN] Error processing {s}: {e}")

    df = pd.DataFrame(all_rows)
    if df.empty:
        print("[OK] No contacts found. Adjust seeds or crawl depth.")
        return

    # Deduplicate by email and institution
    df = df.drop_duplicates(subset=["email", "institucion"]).reset_index(drop=True)

    # Ensure output directory exists
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"[OK] Contacts saved to {out_csv} (rows: {len(df)})")

    # Optional: upload to Google Sheets if configured
    sheets_id = os.getenv("CONTACTS_SHEETS_ID")
    creds_path = "credentials.json"
    if sheets_id and os.path.exists(creds_path):
        try:
            import gspread
            from oauth2client.service_account import ServiceAccountCredentials

            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            gc = gspread.authorize(creds)
            sh = gc.open_by_key(sheets_id)
            try:
                ws = sh.worksheet("contactos_estado")
            except Exception:
                ws = sh.add_worksheet(title="contactos_estado", rows="1000", cols="10")
            ws.clear()
            ws.update([df.columns.tolist()] + df.values.tolist())
            print("[OK] Uploaded contacts to Google Sheets.")
        except Exception as e:
            print(f"[INFO] Skipping Google Sheets upload: {e}")


if __name__ == "__main__":
    main()