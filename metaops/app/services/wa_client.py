from typing import Any, Dict, Optional

import requests

from ..config import get_settings
from ..utils.logging import get_logger
from ..utils.backoff import retry_with_exponential_backoff


logger = get_logger(__name__)
settings = get_settings()


class WhatsAppClient:
	base_url = "https://graph.facebook.com/v20.0"

	def __init__(self, token: Optional[str] = None, phone_number_id: Optional[str] = None) -> None:
		self.token = token or settings.WA_TOKEN
		self.phone_number_id = phone_number_id or settings.WA_PHONE_NUMBER_ID

	def _headers(self) -> Dict[str, str]:
		return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

	@retry_with_exponential_backoff()
	def send_template(self, to_phone: str, template_name: str, lang: str = "es") -> Dict[str, Any]:
		url = f"{self.base_url}/{self.phone_number_id}/messages"
		payload = {
			"messaging_product": "whatsapp",
			"to": to_phone,
			"type": "template",
			"template": {"name": template_name, "language": {"code": lang}},
		}
		resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
		if resp.status_code >= 400:
			logger.error("wa_api_error", status=resp.status_code, text=resp.text)
			resp.raise_for_status()
		return resp.json()