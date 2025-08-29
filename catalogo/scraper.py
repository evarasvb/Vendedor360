from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from typing import Optional, List, Dict

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
	"Chrome/126.0 Safari/537.36"
)


@dataclass
class ResultadoScrapeo:
	id_convenio_marco: str
	url_imagen: Optional[str]
	error: Optional[str]


def _solicitar_html(url: str, timeout: float = 15.0) -> Optional[str]:
	"""Obtiene HTML de una URL con headers adecuados y tolerancia a errores."""
	headers = {"User-Agent": USER_AGENT, "Accept-Language": "es-CL,es;q=0.9"}
	try:
		resp = requests.get(url, headers=headers, timeout=timeout)
		if resp.status_code != 200:
			return None
		return resp.text
	except requests.RequestException:
		return None


def _parsear_prisa_busqueda(html: str) -> Optional[str]:
	"""Dado el HTML de resultados de búsqueda de Prisa, retorna URL del primer producto.

	Esta función está basada en observación de estructura típica; si cambia,
	retorna None.
	"""
	soup = BeautifulSoup(html, "html.parser")
	# Ejemplos: enlaces con clase 'product-item-link' o contenedores de tarjetas
	link = soup.select_one("a.product-item-link, a[itemprop='url']")
	if link and link.get("href"):
		return link["href"].strip()
	# Alternativa: primera tarjeta con data-product-url
	card = soup.select_one("[data-product-url]")
	if card and card.get("data-product-url"):
		return card["data-product-url"].strip()
	return None


def _parsear_prisa_imagen_producto(html: str) -> Optional[str]:
	"""Extrae la URL de la imagen principal desde la página de producto de Prisa."""
	soup = BeautifulSoup(html, "html.parser")
	# Común en Magento: img#image, img.fotorama__img, meta property og:image
	img = soup.select_one("img#image, img.fotorama__img, img.product.image")
	if img and img.get("src"):
		return img["src"].strip()
	meta = soup.find("meta", attrs={"property": "og:image"})
	if meta and meta.get("content"):
		return meta["content"].strip()
	return None


def obtener_url_imagen_prisa(id_convenio_marco: str, espera_s: float = 1.0) -> ResultadoScrapeo:
	"""Realiza búsqueda por ID en Prisa y retorna la URL de imagen si existe."""
	busqueda = f"https://www.prisa.cl/buscar?q={id_convenio_marco}"
	html_busqueda = _solicitar_html(busqueda)
	if not html_busqueda:
		return ResultadoScrapeo(id_convenio_marco, None, "No se pudo cargar resultados de búsqueda")
	url_producto = _parsear_prisa_busqueda(html_busqueda)
	if not url_producto:
		return ResultadoScrapeo(id_convenio_marco, None, "Producto no encontrado en resultados")
	# Cortesía con el sitio
	time.sleep(espera_s)
	html_producto = _solicitar_html(url_producto)
	if not html_producto:
		return ResultadoScrapeo(id_convenio_marco, None, "No se pudo cargar página de producto")
	url_imagen = _parsear_prisa_imagen_producto(html_producto)
	if not url_imagen:
		return ResultadoScrapeo(id_convenio_marco, None, "No se encontró imagen en la página")
	return ResultadoScrapeo(id_convenio_marco, url_imagen, None)


def enriquecer_catalogo_con_imagenes(
	in_csv: str = "productos_catalogo.csv",
	out_csv: str = "productos_catalogo_con_imagenes.csv",
	sitio: str = "prisa",
	espera_s: float = 1.0,
) -> None:
	"""Lee un CSV con columna ID_Convenio_Marco y agrega URL_Imagen mediante scraping.

	Actualmente implementado para sitio 'prisa'. Se puede extender con 'dimerc'.
	"""
	# Leer IDs
	ids: List[str] = []
	with open(in_csv, newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		if "ID_Convenio_Marco" not in reader.fieldnames:
			raise ValueError("El CSV debe contener la columna 'ID_Convenio_Marco'")
		for row in reader:
			val = str(row.get("ID_Convenio_Marco", "")).strip()
			if val:
				ids.append(val)

	resultados: Dict[str, ResultadoScrapeo] = {}
	for id_val in ids:
		if sitio == "prisa":
			res = obtener_url_imagen_prisa(id_val, espera_s=espera_s)
		else:
			res = ResultadoScrapeo(id_val, None, f"Sitio no soportado: {sitio}")
		resultados[id_val] = res
		# Respeto de ritmo para no sobrecargar
		time.sleep(espera_s)

	# Releer e escribir salida con nueva columna
	with open(in_csv, newline="", encoding="utf-8") as fin, open(out_csv, "w", newline="", encoding="utf-8") as fout:
		reader = csv.DictReader(fin)
		fieldnames = list(reader.fieldnames or [])
		if "URL_Imagen" not in fieldnames:
			fieldnames.append("URL_Imagen")
		writer = csv.DictWriter(fout, fieldnames=fieldnames)
		writer.writeheader()
		for row in reader:
			id_val = str(row.get("ID_Convenio_Marco", "")).strip()
			res = resultados.get(id_val)
			row["URL_Imagen"] = res.url_imagen if res and res.url_imagen else ""
			writer.writerow(row)


def _cli():
	import argparse
	parser = argparse.ArgumentParser(description="Enriquece catálogo con URL de imágenes vía scraping")
	parser.add_argument("--in", dest="in_csv", default="productos_catalogo.csv", help="CSV de entrada con ID_Convenio_Marco")
	parser.add_argument("--out", dest="out_csv", default="productos_catalogo_con_imagenes.csv", help="CSV de salida")
	parser.add_argument("--sitio", default="prisa", choices=["prisa"], help="Sitio objetivo")
	parser.add_argument("--espera", type=float, default=1.0, help="Espera entre solicitudes (seg)")
	args = parser.parse_args()

	enriquecer_catalogo_con_imagenes(
		in_csv=args.in_csv,
		out_csv=args.out_csv,
		sitio=args.sitio,
		espera_s=args.espera,
	)
	print(f"Archivo enriquecido escrito en {args.out_csv}")


if __name__ == "__main__":
	_cli()

