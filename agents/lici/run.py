import os
import sys
import time
import csv
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
# Add common utilities to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "common"))
# from queue import load_postulaciones_queue  # noqa: E402
# from status import actualizar_status  # noqa: E402
# === Reglas de ajuste automático de oferta (añadidas) ===
import re
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Config
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def now_fmt() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

EMPRESAS: List[str] = [
    # ejemplo: "EMPRESA1", "EMPRESA2"
]

OUTPUT_FILE = ARTIFACTS_DIR / f"lici_{now_fmt()}.csv"

# ---------- Utilidades de montos y match ----------

def limpiar_monto(texto: str) -> Optional[Decimal]:
    """Normaliza montos como "$ 1.234.567,89" a Decimal("1234567.89").
    Devuelve None si no hay monto válido.
    """
    if not texto:
        return None
    s = str(texto).strip()
    # Reemplazos comunes CLP: quitar símbolo, espacios, puntos de miles y convertir coma decimal
    s = s.replace("$", "").replace("CLP", "").replace("cop", "").replace("COP", "")
    s = re.sub(r"\s+", "", s)
    s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except Exception:
        return None

def calcular_match_percentage(texto_requerimiento: str, texto_oferta: str) -> int:
    """Porcentaje simple de match basado en términos compartidos.
    Heurística: intersección de tokens / tokens requeridos.
    """
    if not texto_requerimiento:
        return 0
    req_tokens = {t for t in re.findall(r"[\wáéíóúñÁÉÍÓÚÑ]+", texto_requerimiento.lower()) if len(t) > 2}
    if not req_tokens:
        return 0
    oferta_tokens = {t for t in re.findall(r"[\wáéíóúñÁÉÍÓÚÑ]+", (texto_oferta or "").lower()) if len(t) > 2}
    inter = req_tokens & oferta_tokens
    pct = int(round(100 * len(inter) / max(1, len(req_tokens))))
    return max(0, min(100, pct))

def debe_ajustar_oferta_95(presupuesto: Optional[Decimal], ofertado: Optional[Decimal], match_pct: int) -> Tuple[bool, Optional[Decimal], str]:
    """Reglas 95% solicitadas:
    - 70-100% match y oferta >120% presupuesto → ajustar a 95% presupuesto
    - 100% match y diferencia >=50% (oferta >=150% presupuesto o presupuesto >=150% oferta) → 95%
    - 100% match y oferta <90% presupuesto → 95%
    Devuelve (debe_ajustar, nuevo_valor, razón)
    """
    if presupuesto is None or ofertado is None:
        return (False, None, "Montos insuficientes para ajuste")
    if presupuesto <= 0:
        return (False, None, "Presupuesto inválido")
    razon = None
    # ... reglas adicionales (omitidas por brevedad) ...
    return (False, None, "Sin reglas aplicables")

# ---------- Modelo de datos ----------

@dataclass
class Licitacion:
    codigo: str
    titulo: str
    presupuesto: Optional[Decimal]
    ofertado: Optional[Decimal]
    match_pct: int
    items: int
    fecha_creacion: Optional[str]
    fecha_cierre: Optional[str]
    link: str

# ---------- Navegación Selenium (stubs o reales en el repo) ----------

def setup_driver():
    # Implementación real en el repo
    return webdriver.Chrome()

def login_lici(driver):
    # Implementación real en el repo
    pass

def buscar_licitaciones(driver, empresa: str) -> List[Licitacion]:
    # Implementación real en el repo
    return []

# ---------- Persistencia CSV existente ----------

def guardar_resultados(licitaciones: List[Licitacion], output_file: Path) -> None:
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "codigo",
            "titulo",
            "presupuesto",
            "ofertado",
            "match_pct",
            "items",
            "fecha_creacion",
            "fecha_cierre",
            "link",
        ])
        for lic in licitaciones:
            writer.writerow([
                lic.codigo,
                lic.titulo,
                str(lic.presupuesto) if lic.presupuesto is not None else "",
                str(lic.ofertado) if lic.ofertado is not None else "",
                lic.match_pct,
                lic.items,
                lic.fecha_creacion or "",
                lic.fecha_cierre or "",
                lic.link,
            ])
    logger.info(f"Resultados guardados exitosamente en {output_file}")

# ---------- Nueva exportación JSON para dashboard ----------

def guardar_resultados_json(licitaciones: List[Licitacion], output_file: Path) -> None:
    """Exporta resultados a JSON con detalles, timestamps y estadísticas agregadas."""
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    total_ofertas = len(licitaciones)
    valor_total_ofertado = sum([(lic.ofertado or Decimal(0)) for lic in licitaciones], Decimal(0))

    # datos estructurados para el dashboard
    data = {
        "timestamp": now_fmt(),
        "empresa_actual": ", ".join(EMPRESAS) if EMPRESAS else None,
        "total_ofertas": total_ofertas,
        "valor_total_ofertado": float(valor_total_ofertado),
        "ofertas": [
            {
                "codigo": lic.codigo,
                "titulo": lic.titulo,
                "presupuesto": float(lic.presupuesto) if lic.presupuesto is not None else None,
                "ofertado": float(lic.ofertado) if lic.ofertado is not None else None,
                "match_pct": lic.match_pct,
                "items": lic.items,
                "fecha_creacion": lic.fecha_creacion,
                "fecha_cierre": lic.fecha_cierre,
                "link": lic.link,
            }
            for lic in licitaciones
        ],
        "stats": {
            "min_oferta": float(min([lic.ofertado for lic in licitaciones if lic.ofertado is not None], default=Decimal(0))) if licitaciones else 0.0,
            "max_oferta": float(max([lic.ofertado for lic in licitaciones if lic.ofertado is not None], default=Decimal(0))) if licitaciones else 0.0,
            "avg_oferta": float((valor_total_ofertado / total_ofertas) if total_ofertas > 0 else Decimal(0)),
        },
    }

    with output_file.open("w", encoding="utf-8") as jf:
        json.dump(data, jf, ensure_ascii=False, indent=2)

    logger.info(f"JSON guardado exitosamente en {output_file}")

# ---------- Ejecución principal ----------

def main():
    """Función principal del agente LICI."""
    logger.info("=" * 60)
    logger.info("Iniciando Agente LICI")
    logger.info(f"Timestamp: {now_fmt()}")
    logger.info(f"Empresas a buscar: {', '.join(EMPRESAS)}")
    logger.info("=" * 60)

    driver = None
    todas_licitaciones: List[Licitacion] = []

    try:
        # Configurar driver
        driver = setup_driver()

        # Login
        login_lici(driver)

        # Buscar para cada empresa
        for empresa in EMPRESAS:
            licitaciones = buscar_licitaciones(driver, empresa)
            todas_licitaciones.extend(licitaciones)
            time.sleep(2)  # Pausa entre búsquedas

        # Guardar resultados
        if todas_licitaciones:
            guardar_resultados(todas_licitaciones, OUTPUT_FILE)

            # Además, exportar JSON para dashboard
            json_path = ARTIFACTS_DIR / f"lici_{now_fmt()}.json"
            guardar_resultados_json(todas_licitaciones, json_path)

            logger.info(f"Total de licitaciones encontradas: {len(todas_licitaciones)}")
        else:
            logger.warning("No se encontraron licitaciones")

    except Exception as e:
        logger.error(f"Error en ejecución principal: {e}")
        raise
    finally:
        if driver:
            driver.quit()
            logger.info("Driver cerrado")

    logger.info("=" * 60)
    logger.info("Agente LICI finalizado")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
