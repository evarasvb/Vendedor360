from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import SessionLocal, engine
from .models import Base, InboxRule, PostTask, Account
from .schemas import (
	CatalogSyncResponse,
	ConnectAccountRequest,
	ConnectAccountResponse,
	HealthResponse,
	InboxRuleRequest,
	InboxRuleResponse,
	PostTaskResponse,
	SchedulePostRequest,
)
from .services.catalog_sync import CatalogSyncService
from .services.content_engine import ContentEngine
from .services.sheets_client import SheetsClient
from .utils.logging import configure_logging, get_logger
from .webhooks.fb_ig import router as fb_ig_router
from .webhooks.wa import router as wa_router


settings = get_settings()
configure_logging(settings.APP_ENV)
logger = get_logger(__name__)

app = FastAPI(title="MetaOps", version="0.1.0")


# Dependency

def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


@app.on_event("startup")
def on_startup():
	# Create tables if not exist (for demo; production should use Alembic)
	Base.metadata.create_all(bind=engine)
	logger.info("app_startup")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
	return HealthResponse()


@app.post("/connect/accounts", response_model=ConnectAccountResponse)
def connect_accounts(payload: ConnectAccountRequest, db: Session = Depends(get_db)) -> ConnectAccountResponse:
	account = Account(
		page_id=payload.page_id,
		ig_business_id=payload.ig_business_id,
		wa_phone_number_id=payload.wa_phone_number_id,
		encrypted_token=payload.token,  # For demo only; should encrypt at rest
	)
	db.add(account)
	db.commit()
	db.refresh(account)
	return ConnectAccountResponse(success=True, account_id=account.id)


@app.post("/catalog/sync", response_model=CatalogSyncResponse)
def catalog_sync(db: Session = Depends(get_db)) -> CatalogSyncResponse:
	client = SheetsClient()
	inventory = client.read_inventory()
	service = CatalogSyncService(db)
	result = service.sync_from_inventory(inventory)
	return CatalogSyncResponse(**result)


@app.post("/content/schedule", response_model=PostTaskResponse)
def schedule_post(payload: SchedulePostRequest, db: Session = Depends(get_db)) -> PostTaskResponse:
	engine = ContentEngine(db)
	post = engine.schedule_post(
		text=payload.text,
		media_url=str(payload.media_url) if payload.media_url else None,
		destination=payload.destination,
		scheduled_at=payload.scheduled_at,
	)
	db.commit()
	db.refresh(post)
	return PostTaskResponse(id=post.id, status=post.status)


@app.get("/content/scheduled", response_model=List[PostTaskResponse])
def list_scheduled(db: Session = Depends(get_db)) -> List[PostTaskResponse]:
	stmt = select(PostTask).where(PostTask.status == "scheduled")
	posts = db.execute(stmt).scalars().all()
	return [PostTaskResponse(id=p.id, status=p.status) for p in posts]


@app.post("/inbox/rules", response_model=InboxRuleResponse)
def define_rule(payload: InboxRuleRequest, db: Session = Depends(get_db)) -> InboxRuleResponse:
	rule = InboxRule(
		keyword=payload.keyword,
		response_text=payload.response_text,
		silent_hours_start=payload.silent_hours_start,
		silent_hours_end=payload.silent_hours_end,
		escalate_to_human=payload.escalate_to_human,
	)
	db.add(rule)
	db.commit()
	db.refresh(rule)
	return InboxRuleResponse(id=rule.id, keyword=rule.keyword)


# Routers
app.include_router(fb_ig_router)
app.include_router(wa_router)