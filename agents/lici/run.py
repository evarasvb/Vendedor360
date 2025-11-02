import os
import sys
import time
import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Add common utilities to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "common"))

# from queue import load_postulaciones_queue  # noqa: E402
# from status import actualizar_status  # noqa: E402

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
