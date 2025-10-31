import json
import pathlib
from typing import Optional

EXCLUS_DEFAULT = [
    "logo", "logotipo", "impreso", "impresión", "impresas",
    "personalizado", "personalizada", "serigrafía", "serigrafiado",
    "bordado", "esval"
]

def load_exclusions(base: pathlib.Path) -> list[str]:
    """Carga lista de palabras de exclusión desde exclusiones.json."""
    p = base / "exclusiones.json"
    if p.exists():
        try:
            return [w.lower() for w in json.loads(p.read_text(encoding="utf-8"))]
        except Exception:
            return EXCLUS_DEFAULT
    return EXCLUS_DEFAULT

def contains_exclusion(txt: str, exclus: list[str]) -> bool:
    """Verifica si el texto contiene alguna palabra de exclusión."""
    t = (txt or "").lower()
    return any(w in t for w in exclus)

def filtrar_por_exclusiones(descripcion: str, exclus: list[str]) -> bool:
    """Filtra licitaciones que contengan palabras de exclusión.
    
    Args:
        descripcion: Descripción de la licitación
        exclus: Lista de palabras de exclusión
    
    Returns:
        True si debe filtrarse (contiene exclusión), False si puede continuar
    """
    return contains_exclusion(descripcion, exclus)

def debe_postular(monto_licitacion: float, monto_catalogo: float, tipo_compra: str) -> bool:
    """Evalúa si debe postular según criterios de negocio de Enrique.
    
    Criterios:
    1. Si monto_licitacion <= monto_catalogo: SIEMPRE postular
    2. Si monto_licitacion > monto_catalogo Y tipo == 'Licitación Pública': NO postular
    3. Si monto_licitacion > monto_catalogo Y tipo == 'Trato Directo': SÍ postular
    
    Args:
        monto_licitacion: Monto de la licitación
        monto_catalogo: Monto total del catálogo disponible
        tipo_compra: Tipo de compra (ej: 'Licitación Pública', 'Trato Directo')
    
    Returns:
        True si debe postular, False si no
    """
    # Criterio 1: Si el monto de licitación es menor o igual al catálogo, siempre postular
    if monto_licitacion <= monto_catalogo:
        return True
    
    # Criterio 2: Si monto_licitacion > monto_catalogo Y es Licitación Pública, NO postular
    if tipo_compra == "Licitación Pública":
        return False
    
    # Criterio 3: Si monto_licitacion > monto_catalogo Y es Trato Directo, SÍ postular
    if tipo_compra == "Trato Directo":
        return True
    
    # Por defecto, no postular si no cumple ningún criterio
    return False

def aplicar_criterios_ajuste(monto_licitacion: float, monto_catalogo: float) -> dict:
    """Aplica criterios de ajuste de presupuesto (95% de monto_licitacion).
    
    Args:
        monto_licitacion: Monto de la licitación
        monto_catalogo: Monto total del catálogo disponible
    
    Returns:
        Dict con monto_ajustado y info sobre si está dentro del rango del catálogo
    """
    monto_ajustado = monto_licitacion * 0.95
    
    return {
        "monto_ajustado": monto_ajustado,
        "monto_original": monto_licitacion,
        "porcentaje_ajuste": 0.95,
        "dentro_catalogo": monto_ajustado <= monto_catalogo,
        "monto_catalogo": monto_catalogo
    }
