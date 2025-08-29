from typing import Dict

from ..config import get_settings


class AdsService:
	def __init__(self) -> None:
		self.settings = get_settings()

	def enabled(self) -> bool:
		return bool(self.settings.ENABLE_ADS)

	def quick_campaign(self, params: Dict) -> Dict:
		if not self.enabled():
			raise RuntimeError("Ads feature disabled")
		# Placeholder for Marketing API interactions
		return {"id": "mock_campaign_id", "status": "created"}