from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..config import get_settings
from ..db import SessionLocal
from .tasks import catalog_sync_job, daily_report_job, post_dispatcher_job


scheduler: BackgroundScheduler | None = None


def with_session(func):
	def wrapper():
		session = SessionLocal()
		try:
			func(session)
		finally:
			session.close()
	return wrapper


def start_scheduler() -> BackgroundScheduler:
	global scheduler
	if scheduler:
		return scheduler
	settings = get_settings()
	scheduler = BackgroundScheduler(timezone=settings.TZ)
	scheduler.add_job(with_session(catalog_sync_job), IntervalTrigger(hours=2), id="catalog_sync_job")
	scheduler.add_job(with_session(post_dispatcher_job), IntervalTrigger(minutes=1), id="post_dispatcher_job")
	scheduler.add_job(daily_report_job, CronTrigger(hour=9, minute=0, timezone=settings.TZ), id="daily_report_job")
	scheduler.start()
	return scheduler