from typing import List, Dict, Any, Optional

import gspread
from google.oauth2.service_account import Credentials

from ..config import get_settings


SCOPES = [
	"https://www.googleapis.com/auth/spreadsheets",
	"https://www.googleapis.com/auth/drive.readonly",
]


class SheetsClient:
	def __init__(self, service_account_json_path: Optional[str] = None) -> None:
		self.settings = get_settings()
		self.creds_path = service_account_json_path or self.settings.GCP_SERVICE_ACCOUNT_JSON_PATH
		self.client = self._build_client()

	def _build_client(self) -> gspread.Client:
		if not self.creds_path:
			raise RuntimeError("Missing GCP_SERVICE_ACCOUNT_JSON_PATH")
		credentials = Credentials.from_service_account_file(self.creds_path, scopes=SCOPES)
		return gspread.authorize(credentials)

	def read_inventory(self) -> List[Dict[str, Any]]:
		key = self.settings.GOOGLE_SHEETS_INVENTORY_KEY
		if not key:
			raise RuntimeError("Missing GOOGLE_SHEETS_INVENTORY_KEY")
		ws = self.client.open_by_key(key).sheet1
		rows = ws.get_all_records()
		# Expected columns: SKU, Nombre, Descripción, Precio, Stock, ImagenURL, Categoría
		normalized = []
		for r in rows:
			normalized.append(
				{
					"sku": str(r.get("SKU", "")).strip(),
					"name": str(r.get("Nombre", "")).strip(),
					"description": str(r.get("Descripción", "")).strip(),
					"price": float(r.get("Precio", 0) or 0),
					"stock": int(r.get("Stock", 0) or 0),
					"image_url": str(r.get("ImagenURL", "")).strip(),
					"category": str(r.get("Categoría", "")).strip(),
				}
			)
		return normalized

	def append_report_row(self, data: List[Any]) -> None:
		key = self.settings.GOOGLE_SHEETS_REPORTS_KEY
		if not key:
			raise RuntimeError("Missing GOOGLE_SHEETS_REPORTS_KEY")
		ws = self.client.open_by_key(key).sheet1
		ws.append_row(data, value_input_option="USER_ENTERED")