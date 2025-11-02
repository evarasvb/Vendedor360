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
