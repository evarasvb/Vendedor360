from datetime import datetime
from typing import Dict, List

from ..config import get_settings


class ReportingService:
	def __init__(self) -> None:
		self.settings = get_settings()

	def build_daily_kpis(self) -> Dict[str, int]:
		# In a real implementation, aggregate from DB; here placeholders
		return {
			"posts_published": 0,
			"dms_handled": 0,
			"comments_replied": 0,
			"new_leads": 0,
			"errors": 0,
		}

	def to_sheet_row(self, kpis: Dict[str, int]) -> List[str]:
		return [
			datetime.utcnow().isoformat(),
			str(kpis["posts_published"]),
			str(kpis["dms_handled"]),
			str(kpis["comments_replied"]),
			str(kpis["new_leads"]),
			str(kpis["errors"]),
		]

	def send_email_summary(self, kpis: Dict[str, int]) -> None:
		# Placeholder for SMTP
		return None