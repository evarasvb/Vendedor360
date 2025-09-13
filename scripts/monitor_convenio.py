"""
Monitor Convenio Marco rankings and provide price recommendations.

This script scrapes price offers from a Convenio Marco product page, calculates
the ranking of your company relative to competitors, and outputs a report with
recommendations on how to adjust your price to stay within the top positions.

Usage:
    python monitor_convenio.py input_products.csv output_ranking.csv

The input CSV must contain the following columns:
    product_id    – Your internal identifier for the product
    product_url   – URL of the Convenio Marco product page
    my_seller_name – Your seller name as it appears on the site
    my_price      – Your current price (used as a fallback if not found on page)
    costo_minimo  – Minimum cost (optional) used to avoid selling at a loss

The output CSV will contain, for each product:
    product_id, mi_precio, rank, top1_vendedor, top1_precio, brecha_pct,
    precio_para_top5, precio_para_top1, recomendacion

See the accompanying README for more details.
"""

import csv
import time
from dataclasses import dataclass
from typing import List, Optional

import requests
from bs4 import BeautifulSoup


@dataclass
class Oferta:
    """Representa una oferta de un proveedor en la tienda."""
    vendedor: str
    precio: float
    stock: Optional[int] = None


def parse_precio(txt: str) -> float:
    """Convierte un texto de precio a un número flotante.

    Normaliza distintos formatos como '1.234,56' o '1,234.56'.
    """
    t = txt.strip().replace("$", "").replace("\u00a0", " ").replace("CLP", "").strip()
    if t.count(",") == 1 and t.count(".") >= 1 and t.rfind(",") > t.rfind("."):
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", "")
    return float(t)


def scrap_ofertas(url: str) -> List[Oferta]:
    """Extrae ofertas de proveedores de una página de producto de Convenio Marco.

    Devuelve una lista de objetos Oferta ordenados por precio ascendente.
    """
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    ofertas: List[Oferta] = []
    filas = soup.select(".offer-row, .seller-line, table.ofertas tr")
    if not filas:
        filas = soup.find_all("tr")
    for f in filas:
        vend_el = f.select_one(".seller-name, .vendedor, .col-vendedor")
        precio_el = f.select_one(".price, .precio, .col-precio")
        if not vend_el or not precio_el:
            continue
        vendedor = vend_el.get_text(strip=True)
        try:
            precio = parse_precio(precio_el.get_text())
        except Exception:
            continue
        stock_el = f.select_one(".stock, .col-stock")
        stock: Optional[int] = None
        if stock_el:
            try:
                stock = int("".join(ch for ch in stock_el.get_text() if ch.isdigit()))
            except Exception:
                stock = None
        ofertas.append(Oferta(vendedor=vendedor, precio=precio, stock=stock))
    ofertas.sort(key=lambda o: o.precio)
    return ofertas


def calcular_reporte(productos_csv: str, salida_csv: str) -> None:
    """Calcula el ranking y recomendaciones de precios para un conjunto de productos.

    Lee un CSV de entrada con detalles de productos y genera un CSV de salida
    con datos de ranking y recomendaciones de ajuste de precios.
    """
    rows_out = []
    with open(productos_csv, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            pid = row["product_id"]
            url = row["product_url"]
            my_name = row["my_seller_name"].strip()
            my_price = float(row["my_price"])
            costo_min = float(row.get("costo_minimo", "0") or 0)

            ofertas = scrap_ofertas(url)
            if not ofertas:
                rows_out.append({
                    "product_id": pid,
                    "mi_precio": my_price,
                    "rank": "",
                    "top1_vendedor": "",
                    "top1_precio": "",
                    "brecha_pct": "",
                    "precio_para_top5": "",
                    "precio_para_top1": "",
                    "recomendacion": "sin_ofertas_detectadas"
                })
                continue

            nombres = [o.vendedor for o in ofertas]
            precios = [o.precio for o in ofertas]
            top1_vendedor = nombres[0]
            top1_precio = precios[0]
            rank: Optional[int] = None
            for i, o in enumerate(ofertas):
                if o.vendedor.lower() == my_name.lower():
                    rank = i + 1
                    my_price = o.precio
                    break
            quinto_precio = precios[min(4, len(precios) - 1)]
            precio_para_top5 = max(costo_min, round(quinto_precio - 0.01, 2))
            precio_para_top1 = max(costo_min, round(top1_precio - 0.01, 2))
            brecha_pct = round((my_price - top1_precio) / top1_precio * 100, 2)
            recomendacion = "mantener"
            if rank is None:
                if precio_para_top5 >= costo_min and precio_para_top5 < my_price:
                    recomendacion = f"bajar_a_{precio_para_top5}"
                else:
                    recomendacion = "no_rentable_top5"
            else:
                if rank > 5 and precio_para_top5 < my_price and precio_para_top5 >= costo_min:
                    recomendacion = f"bajar_a_{precio_para_top5}"
                elif rank > 1 and precio_para_top1 >= costo_min:
                    if (my_price - precio_para_top1) / my_price >= 0.01 and (my_price - top1_precio) / my_price <= 0.03:
                        recomendacion = f"bajar_a_{precio_para_top1}"
            rows_out.append({
                "product_id": pid,
                "mi_precio": round(my_price, 2),
                "rank": rank if rank is not None else "no_encontrado",
                "top1_vendedor": top1_vendedor,
                "top1_precio": round(top1_precio, 2),
                "brecha_pct": brecha_pct,
                "precio_para_top5": precio_para_top5,
                "precio_para_top1": precio_para_top1,
                "recomendacion": recomendacion
            })
            time.sleep(1.0)

    with open(salida_csv, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        wr.writeheader()
        wr.writerows(rows_out)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Uso: python monitor_convenio.py productos.csv reporte.csv")
    else:
        calcular_reporte(sys.argv[1], sys.argv[2])