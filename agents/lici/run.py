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

def debe_ajustar_oferta(presupuesto: Optional[Decimal], ofertado: Optional[Decimal], match_pct: int) -> Tuple[bool, Optional[Decimal], str]:
    """Reglas:
    - Si presupuesto y ofertado existen y ofertado > presupuesto, intentar bajar.
      • Con match >= 80, bajar a 98% del presupuesto.
      • Con match 60-79, bajar a 99% del presupuesto.
      • Con match < 60, no ajustar automáticamente.
    - Si ofertado <= presupuesto, no ajustar.
    Retorna (debe_ajustar, nuevo_valor, razon_log).
    """
    if presupuesto is None or ofertado is None:
        return (False, None, "Montos insuficientes para ajuste")
    if ofertado <= presupuesto:
        return (False, None, "Oferta actual no supera el presupuesto")
    if match_pct >= 80:
        nuevo = (presupuesto * Decimal("0.98")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return (True, nuevo, f"Match {match_pct}%: ajustar a 98% del presupuesto")
    if 60 <= match_pct < 80:
        nuevo = (presupuesto * Decimal("0.99")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return (True, nuevo, f"Match {match_pct}%: ajustar a 99% del presupuesto")
    return (False, None, f"Match {match_pct}% insuficiente para ajuste automático")

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
    """Estructura de datos para una licitación."""
    codigo: str
    titulo: str
    organismo: str
    fecha_publicacion: str
    fecha_cierre: str
    estado: str
    monto_estimado: str
    link: str

def buscar_licitaciones(driver, empresa: str) -> List[Licitacion]:
    """
    Busca licitaciones en LICI para una empresa específica.
    """
    logger.info(f"Buscando licitaciones para: {empresa}")
    resultados = []
    
    try:
        # Navegar a búsqueda
        driver.get("https://www.lici.cl/licitaciones")
        time.sleep(2)
        
        # Buscar por empresa
        search_box = driver.find_element(By.ID, 'search')
        search_box.clear()
        search_box.send_keys(empresa)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)
        
        # Extraer resultados
        licitaciones_elements = driver.find_elements(By.CLASS_NAME, 'licitacion-item')
        
        for elem in licitaciones_elements:
            try:
                codigo = elem.find_element(By.CLASS_NAME, 'codigo').text
                titulo = elem.find_element(By.CLASS_NAME, 'titulo').text
                organismo = elem.find_element(By.CLASS_NAME, 'organismo').text
                fecha_pub = elem.find_element(By.CLASS_NAME, 'fecha-publicacion').text
                fecha_cierre = elem.find_element(By.CLASS_NAME, 'fecha-cierre').text
                estado = elem.find_element(By.CLASS_NAME, 'estado').text
                monto = elem.find_element(By.CLASS_NAME, 'monto').text
                link = elem.find_element(By.TAG_NAME, 'a').get_attribute('href')

                # === Lógica de ajuste automático por oferta ===
                # Suponemos que 'monto' es presupuesto referencial. Si existe monto ofertado visible, extraer.
                presupuesto = limpiar_monto(monto)
                # Intentar leer posible texto de requerimiento/oferta desde el elemento
                texto_req = (titulo + " " + (elem.text or "")) if titulo else (elem.text or "")
                # Si hubiera un campo específico de "oferta actual", podríamos leerlo. Fallback: None
                ofertado_actual = None
                try:
                    ofertado_txt = elem.find_element(By.CSS_SELECTOR, ".oferta-actual, .monto-ofertado").text
                    ofertado_actual = limpiar_monto(ofertado_txt)
                except NoSuchElementException:
                    ofertado_actual = None

                match_pct = calcular_match_percentage(texto_req, titulo)
                debe, nuevo_valor, razon = debe_ajustar_oferta(presupuesto, ofertado_actual, match_pct)
                logger.info(f"LICI | {codigo} | match={match_pct}% | presupuesto={presupuesto} | ofertado={ofertado_actual} | regla='{razon}'")

                if debe and nuevo_valor is not None:
                    logger.warning(f"LICI | {codigo} | Ajustando oferta automática a {nuevo_valor} (antes: {ofertado_actual})")
                    ok = enviar_oferta_ajustada(driver, link, nuevo_valor)
                    if ok:
                        logger.info(f"LICI | {codigo} | Oferta ajustada y enviada con éxito a {nuevo_valor}")
                    else:
                        logger.error(f"LICI | {codigo} | Falló envío de oferta ajustada a {nuevo_valor}")
                else:
                    logger.info(f"LICI | {codigo} | No se ajusta oferta automática")
                
                licitacion = Licitacion(
                    codigo=codigo,
                    titulo=titulo,
                    organismo=organismo,
                    fecha_publicacion=fecha_pub,
                    fecha_cierre=fecha_cierre,
                    estado=estado,
                    monto_estimado=monto,
                    link=link
                )
                resultados.append(licitacion)
                logger.info(f"  Encontrada: {codigo} - {titulo}")
            except NoSuchElementException as e:
                logger.warning(f"Error extrayendo elemento: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error en búsqueda para {empresa}: {e}")
    
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
            'Código',
            'Título',
            'Organismo',
            'Fecha Publicación',
            'Fecha Cierre',
            'Estado',
            'Monto Estimado',
            'Link'
        ])
        
        for lic in licitaciones:
            writer.writerow([
                lic.codigo,
                lic.titulo,
                lic.organismo,
                lic.fecha_publicacion,
                lic.fecha_cierre,
                lic.estado,
                lic.monto_estimado,
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
    main()
