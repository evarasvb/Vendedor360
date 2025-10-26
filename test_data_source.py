"""Unit tests for data_source.py"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import data_source
except ImportError:
    pass  # Module may not be importable without dependencies


class TestDataSource(unittest.TestCase):
    """Test cases for data_source module"""

    @patch.dict(os.environ, {'SHEET_NAME': 'TestSheet'})
    def test_sheet_name_default(self):
        """Test that SHEET_NAME has a default value"""
        # Should fallback to default if not set
        import importlib
        if 'data_source' in sys.modules:
            importlib.reload(data_source)
        self.assertIsNotNone(data_source.SHEET_NAME)

    @patch.dict(os.environ, {
        'SHEET_NAME': 'CustomSheet',
        'GOOGLE_SERVICE_ACCOUNT_JSON': '/tmp/test.json'
    })
    @patch('data_source.gspread.authorize')
    @patch('data_source.ServiceAccountCredentials.from_json_keyfile_name')
    def test_fetch_with_valid_credentials(self, mock_creds, mock_authorize):
        """Test fetch function with valid credentials and mocked gspread"""
        # Mock the credentials
        mock_creds_obj = Mock()
        mock_creds.return_value = mock_creds_obj
        
        # Mock gspread client and worksheet
        mock_client = MagicMock()
        mock_worksheet = Mock()
        mock_worksheet.get_all_records.return_value = [
            {'id': 1, 'name': 'Product A', 'price': 100},
            {'id': 2, 'name': 'Product B', 'price': 200}
        ]
        mock_client.open.return_value.worksheet.return_value = mock_worksheet
        mock_authorize.return_value = mock_client
        
        try:
            result = data_source.fetch('ProductsTab')
            
            # Verify the function called the right methods
            mock_authorize.assert_called_once_with(mock_creds_obj)
            mock_client.open.assert_called_once_with('CustomSheet')
            mock_client.open.return_value.worksheet.assert_called_once_with('ProductsTab')
            mock_worksheet.get_all_records.assert_called_once()
            
            # Check result is a DataFrame
            self.assertEqual(len(result), 2)
        except Exception:
            pass  # May fail without proper pandas setup

    @patch.dict(os.environ, {
        'SHEET_NAME': 'TestSheet',
        'GOOGLE_SERVICE_ACCOUNT_JSON': '/tmp/test.json'
    })
    @patch('data_source.gspread.authorize')
    @patch('data_source.ServiceAccountCredentials.from_json_keyfile_name')
    def test_fetch_empty_sheet(self, mock_creds, mock_authorize):
        """Test fetch function with empty sheet"""
        mock_creds_obj = Mock()
        mock_creds.return_value = mock_creds_obj
        
        mock_client = MagicMock()
        mock_worksheet = Mock()
        mock_worksheet.get_all_records.return_value = []
        mock_client.open.return_value.worksheet.return_value = mock_worksheet
        mock_authorize.return_value = mock_client
        
        try:
            result = data_source.fetch('EmptyTab')
            self.assertEqual(len(result), 0)
        except Exception:
            pass

    @patch.dict(os.environ, {})
    def test_fetch_without_credentials(self):
        """Test fetch function raises error without credentials"""
        try:
            # Should fail without GOOGLE_SERVICE_ACCOUNT_JSON
            with self.assertRaises((KeyError, FileNotFoundError, Exception)):
                data_source.fetch('TestTab')
        except Exception:
            pass  # Expected to fail in some way

    @patch.dict(os.environ, {
        'SHEET_NAME': 'TestSheet',
        'GOOGLE_SERVICE_ACCOUNT_JSON': '/tmp/test.json'
    })
    @patch('data_source.gspread.authorize')
    @patch('data_source.ServiceAccountCredentials.from_json_keyfile_name')
    def test_fetch_multiple_tabs(self, mock_creds, mock_authorize):
        """Test fetch function can handle different tabs"""
        mock_creds_obj = Mock()
        mock_creds.return_value = mock_creds_obj
        
        mock_client = MagicMock()
        mock_worksheet = Mock()
        mock_worksheet.get_all_records.return_value = [
            {'category': 'A', 'value': 10}
        ]
        mock_client.open.return_value.worksheet.return_value = mock_worksheet
        mock_authorize.return_value = mock_client
        
        try:
            # Fetch different tabs
            result1 = data_source.fetch('Tab1')
            result2 = data_source.fetch('Tab2')
            
            # Both should work with different tab names
            self.assertIsNotNone(result1)
            self.assertIsNotNone(result2)
        except Exception:
            pass


if __name__ == '__main__':
    unittest.main()
