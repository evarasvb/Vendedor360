#!/usr/bin/env python3
import os, csv, math, argparse
import pandas as pd
from rapidfuzz import process, fuzz
from pathlib import Path

DEFAULT_DISCOUNT = float(os.getenv("DEFAULT_DISCOUNT", "0.07"))  # 7% por defecto
MIN_SCORE = int(os.getenv("MP_MIN_FUZZ", "80"))                  # umbral similitud

def load_catalog(path: str) -> pd.DataFrame:
    """
    Catálogo esperado con columnas mínimas:
      sku, nombre, precio_base [, descuento, ficha_path, foto_path, coti_path]
    """
    df = pd.read_csv(path)
    must = {"sku","nombre","precio_base"}
    missing = must - set(map(str.lower, df.columns))
    if missing:
        raise ValueError(f"Catálogo sin columnas requeridas: {missing}")
    cols = {c: c.lower() for c in df.columns}
    df.rename(columns=cols, inplace=True)
    return df

def load_opps(path: str) -> pd.DataFrame:
    """
    Oportunidades MP con columnas mínimas:
      opportunity_id, descripcion
    """
    df = pd.read_csv(path)
    cols = {c: c.lower() for c in df.columns}
    df.rename(columns=cols, inplace=True)
    for req in ("opportunity_id","descripcion"):
        if req not in df.columns:
            raise ValueError(f"Oportunidades sin columna: {req}")
    return df

def best_match(desc: str, catalog_names: list[str]) -> tuple[int, str, int]:
    match, score, idx = process.extractOne(
        desc, catalog_names, scorer=fuzz.token_set_ratio, score_cutoff=MIN_SCORE
    ) or (None, 0, -1)
    return idx, match, int(score)

def price_with_discount(base: float, descuento: float|None) -> int:
    d = DEFAULT_DISCOUNT if pd.isna(descuento) or descuento is None else float(descuento)
    return int(math.ceil(base * (1 - d)))

def generate(opps_csv: str, catalog_csv: str, out_csv: str):
    cat = load_catalog(catalog_csv)
    opps = load_opps(opps_csv)
    names = cat["nombre"].astype(str).tolist()
    rows = []
    for _, r in opps.iterrows():
        idx, _, score = best_match(str(r["descripcion"]), names)
        if idx == -1:
            continue
        item = cat.iloc[idx]
        precio = price_with_discount(float(item["precio_base"]), item.get("descuento"))
        rows.append({
            "opportunity_id": r["opportunity_id"],
            "sku": item.get("sku",""),
            "precio_sugerido": precio,
            "ficha_path": item.get("ficha_path",""),
            "foto_path": item.get("foto_path",""),
            "coti_path": item.get("coti_path",""),
            "send": "s",
        })
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "opportunity_id","sku","precio_sugerido","ficha_path","foto_path","coti_path","send"
        ])
        w.writeheader()
        w.writerows(rows)
    return len(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opps", required=True, help="data/opps_mp.csv")
    ap.add_argument("--catalog", required=True, help="data/catalogo.csv")
    ap.add_argument("--out", default="queues/postulaciones.csv")
    args = ap.parse_args()
    n = generate(args.opps, args.catalog, args.out)
    print(f"generadas {n} filas -> {args.out}")

if __name__ == "__main__":
    main()
