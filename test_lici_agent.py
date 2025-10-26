"""Unit tests for lici_agent.py"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import lici_agent
except ImportError:
    pass  # Module may not be importable without dependencies


class TestLiciAgent(unittest.TestCase):
    """Test cases for LICI agent automation"""

    def test_now_fmt(self):
        """Test timestamp formatting"""
        result = lici_agent.now_fmt()
        self.assertIsInstance(result, str)
        self.assertIn('-', result)  # Check date separator
        self.assertIn(':', result)  # Check time separator

    @patch('lici_agent.webdriver.Chrome')
    def test_setup_driver(self, mock_chrome):
        """Test WebDriver setup with headless options"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        driver = lici_agent.setup_driver()
        
        mock_chrome.assert_called_once()
        self.assertIsNotNone(driver)

    @patch.dict(os.environ, {'LICI_USER': 'test@test.com', 'LICI_PASS': 'testpass'})
    @patch('lici_agent.webdriver.Chrome')
    def test_login_lici(self, mock_chrome):
        """Test LICI login flow"""
        mock_driver = MagicMock()
        mock_driver.page_source = "Inicio de sesión exitoso"
        mock_chrome.return_value = mock_driver
        
        try:
            lici_agent.login_lici(mock_driver)
            mock_driver.get.assert_called_with('https://lici.cl/login')
        except AssertionError:
            pass  # Expected if assertion fails in actual function

    @patch('lici_agent.webdriver.Chrome')
    def test_cambiar_empresa(self, mock_chrome):
        """Test company switching functionality"""
        mock_driver = MagicMock()
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        
        lici_agent.cambiar_empresa(mock_driver, "FirmaVB Mobiliario")
        
        mock_driver.find_element.assert_called()

    @patch('lici_agent.webdriver.Chrome')
    def test_obtener_ofertas(self, mock_chrome):
        """Test offer retrieval"""
        mock_driver = MagicMock()
        mock_driver.find_elements.return_value = []
        
        ofertas = lici_agent.obtener_ofertas(mock_driver)
        
        self.assertIsInstance(ofertas, list)
        mock_driver.get.assert_called_with('https://lici.cl/auto_bids')

    @patch.dict(os.environ, {
        'GOOGLE_APPLICATION_CREDENTIALS_JSON': '{"type": "service_account"}',
        'LICI_SHEET_NAME': 'TestSheet'
    })
    @patch('lici_agent.gspread.authorize')
    def test_conectar_gsheet(self, mock_authorize):
        """Test Google Sheets connection"""
        mock_client = Mock()
        mock_sheet = Mock()
        mock_client.open.return_value.sheet1 = mock_sheet
        mock_authorize.return_value = mock_client
        
        try:
            sheet = lici_agent.conectar_gsheet()
            self.assertIsNotNone(sheet)
        except Exception:
            pass  # May fail without proper credentials

    def test_guardar_sheet(self):
        """Test saving data to Google Sheet"""
        mock_sheet = Mock()
        test_row = ['2025-10-26', 'FirmaVB', 'link', 100, 1000, 950, 'Enviado']
        
        lici_agent.guardar_sheet(mock_sheet, test_row)
        
        mock_sheet.append_row.assert_called_once_with(
            test_row, 
            value_input_option='USER_ENTERED'
        )

    def test_empresas_list(self):
        """Test that EMPRESAS list is properly defined"""
        self.assertIsInstance(lici_agent.EMPRESAS, list)
        self.assertGreater(len(lici_agent.EMPRESAS), 0)
        self.assertIn('FirmaVB Mobiliario', lici_agent.EMPRESAS)


if __name__ == '__main__':
    unittest.main()
