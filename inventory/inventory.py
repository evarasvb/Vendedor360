"""
Módulo de inventario para Vendedor360.

Este módulo proporciona una interfaz para un inventario inteligente y autónomo. Debe ser completado para conectarse con la fuente real de datos (por ejemplo, una hoja de cálculo de Google Sheets, una base de datos o un servicio de inventario externo).

Funciones sugeridas:
- `cargar_inventario()`: Carga los datos del inventario en memoria.
- `actualizar_inventario()`: Sincroniza cambios con la fuente externa.
- `buscar_producto_por_id(id_convenio: str)`: Devuelve un registro de producto según su ID.
- `buscar_productos_por_nombre(nombre: str)`: Devuelve una lista de productos cuyo nombre coincida.

Las funciones aquí son meramente ilustrativas y deben adaptarse a las necesidades reales.
"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Producto:
    id_convenio: str
    nombre: str
    precio: float
    url_imagen: str
    stock: Optional[int] = None

# Inventario interno (ejemplo básico)
_catalogo: List[Producto] = []

def cargar_inventario() -> None:
    """Carga el inventario desde la fuente de datos en la variable interna.

    Modifique esta función para conectar con su base de datos o Google Sheets.
    """
    global _catalogo
    # TODO: leer de la fuente real. Aquí se carga un ejemplo estático.
    _catalogo = [
        Producto(id_convenio="CM-0001", nombre="Ejemplo Producto 1", precio=1000.0, url_imagen="https://example.com/img1.jpg", stock=10),
        Producto(id_convenio="CM-0002", nombre="Ejemplo Producto 2", precio=2500.0, url_imagen="https://example.com/img2.jpg", stock=5),
    ]

def actualizar_inventario() -> None:
    """Actualiza el inventario sincronizando cambios en la fuente de datos.

    Implemente la lógica necesaria para sincronizar cambios (por ejemplo, leer un fichero CSV actualizado o consultar una API).
    """
    # TODO: Implementar sincronización con la fuente de datos externa.
    pass

def buscar_producto_por_id(id_convenio: str) -> Optional[Producto]:
    """Busca un producto en el inventario por su ID de convenio.

    Args:
        id_convenio: Identificador único del producto.

    Returns:
        Una instancia de `Producto` si se encuentra, de lo contrario `None`.
    """
    for producto in _catalogo:
        if producto.id_convenio == id_convenio:
            return producto
    return None

def buscar_productos_por_nombre(nombre: str) -> List[Producto]:
    """Busca productos cuyo nombre contenga la cadena proporcionada (no sensible a mayúsculas/minúsculas).

    Args:
        nombre: Texto a buscar en los nombres de productos.

    Returns:
        Lista de productos coincidentes.
    """
    nombre_lower = nombre.lower()
    return [prod for prod in _catalogo if nombre_lower in prod.nombre.lower()]

