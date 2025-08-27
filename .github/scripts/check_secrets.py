#!/usr/bin/env python3
import os, sys
REQUIRED = [
    "WHEREX_USER","WHEREX_PASS",
    "SENEGOCIA_USER","SENEGOCIA_PASS",
    "META_PAGE_ACCESS_TOKEN","META_PAGE_ID",
    "LINKEDIN_ACCESS_TOKEN",
    "LICI_USER","LICI_PASS","CM_USER","CM_PASS",
    "META_AD_ACCOUNT_ID","META_PIXEL_ID"
]
ALT_ONE_OF = [("MP_TICKET","MP_SESSION_COOKIE")]
missing = [k for k in REQUIRED if not os.getenv(k)]
alt_missing = [(a,b) for (a,b) in ALT_ONE_OF if not (os.getenv(a) or os.getenv(b))]
if missing or alt_missing:
    print("\n[❌] Faltan secretos requeridos:\n")
    for k in missing: print(f"  - {k}")
    for a,b in alt_missing: print(f"  - Falta al menos uno: {a} o {b}")
    print("\nCárgalos en GitHub → Settings → Secrets and variables → Actions\n"); sys.exit(1)
print("[✅] Secretos mínimos presentes.")

