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
    for s in os.environ.get("LICI_EMPRESAS", "FirmaVB Mobiliario,FirmaVB Aseo,FirmaVB Alimentos,FirmaVB Oficina,FirmaVB Electrodomésticos,FirmaVB Ferretería").split(",")
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
        # Submit
        pass_input.send_keys(Keys.RETURN)
        time.sleep(5)
        logger.info("Login completado.")
    except NoSuchElementException as e:
        logger.error(f"Error en login: elemento no encontrado. {e}")
        raise
@dataclass
class Oferta:
    nombre: str
    empresa: str
    publicacion: str
    apertura: str
    monto: str
    link: str
def buscar_licitaciones(driver, empresa: str, page_limit: int = 5) -> List[Oferta]:
    """
    Busca licitaciones para una empresa en LICI.CL.
    Extrae 'Ofertas Automáticas' usando selectores robustos basados en XPath.
    """
    logger.info(f"Buscando licitaciones para '{empresa}'...")
    ofertas = []
    # Navegar al buscador de licitaciones
    driver.get("https://www.lici.cl/licitaciones")
    time.sleep(3)
    try:
        # Buscar por empresa
        search_box = driver.find_element(By.ID, "search-input")
        search_box.clear()
        search_box.send_keys(empresa)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)
        # Recorrer las páginas de resultados
        for page_num in range(1, page_limit + 1):
            logger.info(f"Procesando página {page_num} para '{empresa}'...")
            
            # Extraer ofertas de la página actual usando XPath robusto
            # Selector: //main//div[contains(.,'Presupuesto') and contains(.,'Ofertado')]
            cards = driver.find_elements(By.XPATH, "//main//div[contains(.,'Presupuesto') and contains(.,'Ofertado')]")
            
            for card in cards:
                try:
                    # Extraer título (asumiendo que está en un elemento con clase o tag específico)
                    try:
                        titulo = card.find_element(By.XPATH, ".//h2 | .//h3 | .//*[contains(@class, 'title')] | .//*[contains(@class, 'nombre')]").text
                    except NoSuchElementException:
                        titulo = "N/A"
                    
                    # Extraer presupuesto
                    try:
                        presupuesto = card.find_element(By.XPATH, ".//*[contains(text(), 'Presupuesto')]/following-sibling::* | .//*[contains(text(), 'Presupuesto')]/parent::*//*[not(contains(text(), 'Presupuesto'))]").text
                    except NoSuchElementException:
                        presupuesto = "N/A"
                    
                    # Extraer ofertado
                    try:
                        ofertado = card.find_element(By.XPATH, ".//*[contains(text(), 'Ofertado')]/following-sibling::* | .//*[contains(text(), 'Ofertado')]/parent::*//*[not(contains(text(), 'Ofertado'))]").text
                    except NoSuchElementException:
                        ofertado = "N/A"
                    
                    # Extraer fecha de cierre
                    try:
                        fecha_cierre = card.find_element(By.XPATH, ".//*[contains(text(), 'Cierre') or contains(text(), 'cierre') or contains(text(), 'Fecha')]/following-sibling::* | .//*[contains(@class, 'fecha')] | .//*[contains(@class, 'date')]").text
                    except NoSuchElementException:
                        fecha_cierre = "N/A"
                    
                    # Extraer link
                    try:
                        link = card.find_element(By.XPATH, ".//a").get_attribute("href")
                    except NoSuchElementException:
                        link = "N/A"
                    
                    ofertas.append(Oferta(
                        nombre=titulo,
                        empresa=empresa,
                        publicacion=presupuesto,
                        apertura=fecha_cierre,
                        monto=ofertado,
                        link=link
                    ))
                except Exception as e:
                    logger.warning(f"Error procesando card: {e}")
                    continue
            
            # Intentar navegar a la siguiente página
            try:
                next_button = driver.find_element(By.CLASS_NAME, "next-page")
                if "disabled" in next_button.get_attribute("class"):
                    break
                next_button.click()
                time.sleep(3)
            except NoSuchElementException:
                break
    except Exception as e:
        logger.error(f"Error al buscar licitaciones para '{empresa}': {e}")
    logger.info(f"Se encontraron {len(ofertas)} ofertas para '{empresa}'.")
    return ofertas
def run():
    """
    Función principal que ejecuta el flujo completo.
    """
    driver = None
    try:
        logger.info(f"=== Inicio de LICI Automation ===")
        logger.info(f"Empresas a procesar: {EMPRESAS}")
        # Setup del driver
        driver = setup_driver()
        # Login
        login_lici(driver)
        # Buscar licitaciones para cada empresa
        results = []
        for empresa in EMPRESAS:
            ofertas = buscar_licitaciones(driver, empresa)
            for oferta in ofertas:
                results.append({
                    "Nombre": oferta.nombre,
                    "Empresa": oferta.empresa,
                    "Publicación": oferta.publicacion,
                    "Apertura": oferta.apertura,
                    "Monto": oferta.monto,
                    "Link": oferta.link,
                })
        # Guardar resultados en CSV
        if results:
            Path("artifacts").mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
            logger.info(f"Resultados guardados en {OUTPUT_FILE}")
        
        # Enviar notificaciones si están configuradas
        if NOTIFY_EMAILS:
            send_email(f"LICI automation completada - {len(results)} ofertas procesadas")
        
        logger.info("LICI automation completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}")
        if NOTIFY_EMAILS:
            send_email(f"Error en LICI automation: {e}")
        return 1
        
    finally:
        if driver:
            driver.quit()
            logger.info("Driver cerrado.")
def send_email(message: str):
    """
    Envía notificaciones por correo electrónico.
    """
    if not NOTIFY_EMAILS or not SMTP_HOST:
        logger.info("Email notifications not configured, skipping.")
        return
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_FROM
        msg['To'] = ', '.join(NOTIFY_EMAILS)
        msg['Subject'] = 'LICI Automation Notification'
        
        body = f"""
        LICI Automation Report
        
        {message}
        
        Timestamp: {now_fmt()}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASS:
                server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        logger.info(f"Email sent to {', '.join(NOTIFY_EMAILS)}")
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
if __name__ == '__main__':
    sys.exit(run())
