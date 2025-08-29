from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import InboxRule


class InboxAutomation:
	def __init__(self, session: Session) -> None:
		self.session = session

	def find_response_for_message(self, text: str) -> Optional[str]:
		needle = (text or "").lower()
		stmt = select(InboxRule).order_by(InboxRule.id.asc())
		for rule in self.session.execute(stmt).scalars():
			if rule.keyword and rule.keyword.lower() in needle:
				return rule.response_text
		return None