from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import PostTask


class ContentEngine:
	def __init__(self, session: Session) -> None:
		self.session = session

	def render_template(self, text_template: str, variables: Dict[str, str]) -> str:
		result = text_template
		for key, value in variables.items():
			result = result.replace(f"{{{{{key}}}}}", str(value))
		return result

	def schedule_post(
		self, *, text: str, media_url: Optional[str], destination: str, scheduled_at: datetime
	) -> PostTask:
		post = PostTask(
			text=text,
			media_url=media_url,
			destination=destination,
			scheduled_at=scheduled_at,
			status="scheduled",
		)
		self.session.add(post)
		self.session.flush()
		return post

	def due_posts(self, now: datetime) -> list[PostTask]:
		stmt = select(PostTask).where(PostTask.status == "scheduled", PostTask.scheduled_at <= now)
		return list(self.session.execute(stmt).scalars().all())