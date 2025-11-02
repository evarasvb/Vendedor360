import os
import sys
import time
import csv
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
    nuevo = (presupuesto * Decimal("0.95")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    # Regla 1: 70-100% y oferta >120% presupuesto
    if match_pct >= 70 and ofertado > presupuesto * Decimal("1.20"):
        razon = f"Match {match_pct}% y ofertado {ofertado} >120% presupuesto {presupuesto}"
        return (True, nuevo, razon)

    # Regla 2: 100% y diferencia >=50%
    if match_pct == 100 and (ofertado >= presupuesto * Decimal("1.50") or presupuesto >= ofertado * Decimal("1.50")):
        razon = "Match 100% y diferencia >=50%"
        return (True, nuevo, razon)

    # Regla 3: 100% y oferta <90% presupuesto
    if match_pct == 100 and ofertado < presupuesto * Decimal("0.90"):
        razon = "Match 100% y oferta <90% presupuesto"
        return (True, nuevo, razon)

    return (False, None, f"No cumple reglas 95% (match={match_pct}%)")

def enviar_oferta_ajustada(driver, link_licitacion: str, nuevo_monto: Decimal) -> bool:
    """Navega a la licitación y trata de actualizar/enviar la oferta con nuevo_monto.
    Esta función es específica del sitio y puede requerir ajustes de selectores.
    Devuelve True si aparenta éxito.
    """
    try:
        driver.get(link_licitacion)
        time.sleep(2)
        # Ejemplo de selectores; podrían cambiar según el DOM real de LICI
        try:
            btn_editar = driver.find_element(By.CSS_SELECTOR, "button.edit-offer, a.edit-offer")
            btn_editar.click()
            time.sleep(1)
        except NoSuchElementException:
            # Si no hay botón editar, intentar ir directamente al formulario
            pass
        # Campo monto
        input_monto = driver.find_element(By.CSS_SELECTOR, "input[name='monto']")
        input_monto.clear()
        input_monto.send_keys(str(int(nuevo_monto)))
        # Enviar
        try:
            btn_enviar = driver.find_element(By.CSS_SELECTOR, "button.submit-offer, button[type='submit']")
        except NoSuchElementException:
            btn_enviar = driver.find_element(By.XPATH, "//button[contains(., 'Enviar') or contains(., 'Guardar')]")
        btn_enviar.click()
        time.sleep(2)
        # Verificar algún toast/mensaje de éxito
        try:
            msg = driver.find_element(By.CSS_SELECTOR, ".toast-success, .alert-success").text
            logging.info(f"LICI | Confirmación de envío: {msg}")
        except NoSuchElementException:
            pass
        return True
    except Exception as e:
        logging.error(f"LICI | Error enviando oferta ajustada: {e}")
        return False

# ======================
# Configuración & Secretos
# ======================
LICI_USER = os.environ.get("LICI_USER")
LICI_PASS = os.environ.get("LICI_PASS")
# Multi-empresa: soporta lista por ENV o usa defaults
EMPRESAS = [
    s.strip()
    for s in os.environ.get("LICI_EMPRESAS", "FirmaVB Aseo,FirmaVB Alimento,FirmaVB Oficina,FirmaVB Mobiliario,FirmaVB Desechable,FirmaVB Electrodomésticos,FirmaVB Ferretería").split(",")
    if s.strip()
]
# Notificaciones por correo (reservado para futuras extensiones)
NOTIFY_EMAILS = [
    s.strip()
    for s in os.environ.get("LICI_NOTIFY_EMAILS", "").split(",")
    if s.strip()
]
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "noreply@lici-bot.local")
OUTPUT_FILE = f"artifacts/lici_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def now_fmt() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1400,1000')
    return webdriver.Chrome(options=options)


def login_lici(driver):
    """
    Realiza login en LICI.CL.
    """
    logger.info("Iniciando login en LICI...")
    driver.get("https://www.lici.cl/login")
    time.sleep(3)

    try:
        # Ingresar usuario
        user_input = driver.find_element(By.ID, 'email')
        user_input.clear()
        user_input.send_keys(LICI_USER)

        # Ingresar contraseña
        pass_input = driver.find_element(By.ID, 'password')
        pass_input.clear()
        pass_input.send_keys(LICI_PASS)
        pass_input.send_keys(Keys.RETURN)
        time.sleep(3)

        logger.info('Login successful')
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise


@dataclass
class Licitacion:
    """Estructura de datos para una licitación/autobid existente."""
    codigo: str
    titulo: str
    presupuesto: str
    ofertado: str
    match_pct: str
    items: str
    fecha_creacion: str
    fecha_cierre: str
    link: str


def buscar_licitaciones(driver, empresa: str) -> List[Licitacion]:
    """
    Lee auto_bids existentes generados por Lisa desde https://lici.cl/auto_bids
    y aplica reglas de ajuste 95% cuando corresponda.
    """
    logger.info(f"Leyendo auto_bids para: {empresa}")
    resultados: List[Licitacion] = []

    try:
        driver.get("https://lici.cl/auto_bids")
        time.sleep(3)

        # Filtro por empresa si existe un buscador/selector
        try:
            search = driver.find_element(By.CSS_SELECTOR, "input[name='empresa'], input#empresa, input[placeholder*='Empresa']")
            search.clear()
            search.send_keys(empresa)
            search.send_keys(Keys.RETURN)
            time.sleep(2)
        except NoSuchElementException:
            pass

        # Cada autobid en una fila/tarjeta
        items = driver.find_elements(By.CSS_SELECTOR, ".auto-bid-row, .autobid-item, tr.autobid, .auto-bid-card")
        if not items:
            # fallback genérico: filas de tabla en /auto_bids
            items = driver.find_elements(By.CSS_SELECTOR, "table tr")

        for el in items:
            try:
                # Campos con selectores tolerantes
                codigo = el.get_attribute("data-id") or el.find_element(By.CSS_SELECTOR, ".id, .codigo, td.id").text
                titulo = el.find_element(By.CSS_SELECTOR, ".title, .titulo, td.titulo").text
                presupuesto_txt = el.find_element(By.CSS_SELECTOR, ".budget, .presupuesto, td.presupuesto").text
                ofertado_txt = el.find_element(By.CSS_SELECTOR, ".offered, .ofertado, td.ofertado").text
                match_txt = el.find_element(By.CSS_SELECTOR, ".match, .coincidencia, td.match").text
                items_txt = el.find_element(By.CSS_SELECTOR, ".items, .productos, td.items").text
                creacion_txt = el.find_element(By.CSS_SELECTOR, ".created, .creacion, td.creacion, .created-at").text
                cierre_txt = el.find_element(By.CSS_SELECTOR, ".closing, .cierre, td.cierre, .close-at").text
                link = el.find_element(By.CSS_SELECTOR, "a[href*='licitacion'], a.details, a").get_attribute("href")

                presupuesto = limpiar_monto(presupuesto_txt)
                ofertado = limpiar_monto(ofertado_txt)
                # match en numero
                m = re.search(r"(\d{1,3})\s*%", match_txt or "")
                match_pct = int(m.group(1)) if m else calcular_match_percentage(titulo, titulo)

                debe, nuevo_valor, razon = debe_ajustar_oferta_95(presupuesto, ofertado, match_pct)
                logger.info(f"AUTO_BID | {codigo} | match={match_pct}% | presupuesto={presupuesto} | ofertado={ofertado} | regla='{razon}'")
                if debe and nuevo_valor is not None and link:
                    logger.warning(f"AUTO_BID | {codigo} | Ajustando oferta a {nuevo_valor} (antes: {ofertado})")
                    ok = enviar_oferta_ajustada(driver, link, nuevo_valor)
                    if ok:
                        logger.info(f"AUTO_BID | {codigo} | Oferta ajustada y enviada con éxito a {nuevo_valor}")
                    else:
                        logger.error(f"AUTO_BID | {codigo} | Falló envío de oferta ajustada a {nuevo_valor}")
                else:
                    logger.info(f"AUTO_BID | {codigo} | No se ajusta oferta (o sin link)")

                resultados.append(
                    Licitacion(
                        codigo=str(codigo),
                        titulo=titulo,
                        presupuesto=presupuesto_txt,
                        ofertado=ofertado_txt,
                        match_pct=f"{match_pct}%",
                        items=items_txt,
                        fecha_creacion=creacion_txt,
                        fecha_cierre=cierre_txt,
                        link=link or ""
                    )
                )
            except NoSuchElementException:
                continue
            except Exception as e:
                logger.warning(f"Error leyendo autobid: {e}")
                continue
    except Exception as e:
        logger.error(f"Error en lectura auto_bids para {empresa}: {e}")

    return resultados


def guardar_resultados(licitaciones: List[Licitacion], output_file: str):
    """
    Guarda los resultados en un archivo CSV.
    """
    logger.info(f"Guardando {len(licitaciones)} resultados en {output_file}")

    # Crear directorio si no existe
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'ID',
            'Título',
            'Presupuesto',
            'Ofertado',
            'Match %',
            'Ítems',
            'Fecha Creación',
            'Fecha Cierre',
            'Link'
        ])

        for lic in licitaciones:
            writer.writerow([
                lic.codigo,
                lic.titulo,
                lic.presupuesto,
                lic.ofertado,
                lic.match_pct,
                lic.items,
                lic.fecha_creacion,
                lic.fecha_cierre,
                lic.link
            ])

    logger.info(f"Resultados guardados exitosamente")


def main():
    """
    Función principal del agente LICI.
    """
    logger.info("=" * 60)
    logger.info("Iniciando Agente LICI")
    logger.info(f"Timestamp: {now_fmt()}")
    logger.info(f"Empresas a buscar: {', '.join(EMPRESAS)}")
    logger.info("=" * 60)

    driver = None
    todas_licitaciones = []

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
    main
