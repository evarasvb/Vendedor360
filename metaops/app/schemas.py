from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class HealthResponse(BaseModel):
	status: Literal["ok"] = "ok"


class ConnectAccountRequest(BaseModel):
	page_id: Optional[str] = None
	ig_business_id: Optional[str] = None
	wa_phone_number_id: Optional[str] = None
	token: str


class ConnectAccountResponse(BaseModel):
	success: bool
	account_id: int


class CatalogSyncResponse(BaseModel):
	processed: int
	created: int
	updated: int
	errors: int


class SchedulePostRequest(BaseModel):
	text: str
	media_url: Optional[HttpUrl] = None
	destination: Literal["fb", "ig", "both"]
	scheduled_at: datetime


class PostTaskResponse(BaseModel):
	id: int
	status: str


class InboxRuleRequest(BaseModel):
	keyword: str
	response_text: Optional[str] = None
	silent_hours_start: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
	silent_hours_end: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
	escalate_to_human: bool = False


class InboxRuleResponse(BaseModel):
	id: int
	keyword: str