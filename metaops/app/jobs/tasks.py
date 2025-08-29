from datetime import datetime

from sqlalchemy.orm import Session

from ..services.catalog_sync import CatalogSyncService
from ..services.content_engine import ContentEngine
from ..services.reporting import ReportingService
from ..services.sheets_client import SheetsClient


def catalog_sync_job(session: Session) -> None:
	client = SheetsClient()
	inventory = client.read_inventory()
	sync = CatalogSyncService(session)
	sync.sync_from_inventory(inventory)


def post_dispatcher_job(session: Session) -> None:
	engine = ContentEngine(session)
	now = datetime.utcnow()
	for post in engine.due_posts(now):
		# Placeholder for publishing via Meta APIs
		post.status = "posted"
		post.result_ref = "mock_published_id"


def daily_report_job() -> None:
	report = ReportingService()
	kpis = report.build_daily_kpis()
	# Sheets write would be performed by ReportingService + SheetsClient in full impl
	return None