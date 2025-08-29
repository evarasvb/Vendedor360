from typing import Any, Dict, Optional

import requests

from ..config import get_settings
from ..utils.logging import get_logger
from ..utils.backoff import retry_with_exponential_backoff


logger = get_logger(__name__)
settings = get_settings()


class MetaClient:
	base_url = "https://graph.facebook.com/v20.0"

	def __init__(self, access_token: Optional[str] = None) -> None:
		self.access_token = access_token or settings.META_PAGE_ACCESS_TOKEN

	def _headers(self) -> Dict[str, str]:
		return {"Authorization": f"Bearer {self.access_token}"}

	@retry_with_exponential_backoff()
	def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		url = f"{self.base_url}/{path.lstrip('/')}"
		resp = requests.get(url, params=params, headers=self._headers(), timeout=30)
		if resp.status_code >= 400:
			logger.error("meta_api_error", status=resp.status_code, text=resp.text)
			resp.raise_for_status()
		return resp.json()

	@retry_with_exponential_backoff()
	def post(self, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		url = f"{self.base_url}/{path.lstrip('/')}"
		resp = requests.post(url, data=data, headers=self._headers(), timeout=30)
		if resp.status_code >= 400:
			logger.error("meta_api_error", status=resp.status_code, text=resp.text)
			resp.raise_for_status()
		return resp.json()