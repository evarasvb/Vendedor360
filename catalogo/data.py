from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Producto:
	"""Representa un producto del catálogo simulado."""
	id_convenio: str
	nombre: str
	precio: float
	url_imagen: str


def cargar_catalogo_simulado() -> Dict[str, Producto]:
	"""Retorna un diccionario que simula una base de datos de productos.

	La clave es el ID de Convenio Marco (string), y el valor es un Producto.
	"""
	return {
		"CM-0001": Producto(
			id_convenio="CM-0001",
			nombre="Lápiz Pasta Azul BIC",
			precio=250.0,
			url_imagen="https://example.com/images/bic-azul.jpg",
		),
		"CM-0002": Producto(
			id_convenio="CM-0002",
			nombre="Cuaderno Universitario 100 Hojas",
			precio=1890.0,
			url_imagen="https://example.com/images/cuaderno-100.jpg",
		),
		"CM-0003": Producto(
			id_convenio="CM-0003",
			nombre="Block de Notas 75x75mm",
			precio=990.0,
			url_imagen="https://example.com/images/notas-75.jpg",
		),
	}

