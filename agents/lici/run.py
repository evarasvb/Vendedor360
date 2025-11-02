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
    Inicia sesión en LICI usando las credenciales del entorno.
    """
    logger.info("Iniciando login en LICI...")
    driver.get('https://lici.cl/login')
    time.sleep(2)
    try:
        user_input = driver.find_element(By.ID, "username")
        pass_input = driver.find_element(By.ID, "password")
        user_input.send_keys(LICI_USER)
        pass_input.send_keys(LICI_PASS)
        pass_input.send_keys(Keys.RETURN)
        time.sleep(3)
        logger.info("Login completado.")
    except NoSuchElementException as e:
        logger.error(f"No se encontraron los campos de login: {e}")
        raise

def run():
    """
    Función principal: itera sobre empresas y ofertas, extrayendo datos de LICI.
    """
    logger.info("=== Iniciando LICI Automation ===")
    driver = None
    
    try:
        driver = setup_driver()
        login_lici(driver)
        
        results = []
        
        # Iterar sobre cada empresa configurada
        for empresa in EMPRESAS:
            logger.info(f"Procesando empresa: {empresa}")
            
            # Aquí iría la lógica para navegar y extraer ofertas
            # Por ahora, simplemente logging
            time.sleep(1)
            
            # Ejemplo: extraer ofertas para esta empresa
            # ofertas = extract_ofertas(driver, empresa)
            # results.extend(ofertas)
        
        # Guardar resultados en CSV
        if results:
            Path("artifacts").mkdir(exist_ok=True)
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
