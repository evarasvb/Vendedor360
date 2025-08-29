from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	# App
	APP_ENV: str = "dev"
	TZ: str = "UTC"
	DATABASE_URL: str = "sqlite:///./metaops.db"

	# Meta
	META_APP_ID: Optional[str] = None
	META_APP_SECRET: Optional[str] = None
	META_VERIFY_TOKEN: Optional[str] = None
	META_PAGE_ACCESS_TOKEN: Optional[str] = None
	META_IG_BUSINESS_ID: Optional[str] = None
	META_CATALOG_ID: Optional[str] = None

	# WhatsApp Cloud
	WA_PHONE_NUMBER_ID: Optional[str] = None
	WA_BUSINESS_ACCOUNT_ID: Optional[str] = None
	WA_TOKEN: Optional[str] = None

	# Google Sheets
	GCP_SERVICE_ACCOUNT_JSON_PATH: Optional[str] = None
	GOOGLE_SHEETS_INVENTORY_KEY: Optional[str] = None
	GOOGLE_SHEETS_REPORTS_KEY: Optional[str] = None

	# Notifications / Email
	ALERT_EMAILS: Optional[str] = None
	SMTP_HOST: Optional[str] = None
	SMTP_PORT: int = 587
	SMTP_USER: Optional[EmailStr] = None
	SMTP_PASSWORD: Optional[str] = None

	# Ads feature flag
	ENABLE_ADS: bool = False

	@property
	def alert_emails_list(self) -> List[str]:
		if not self.ALERT_EMAILS:
			return []
		return [email.strip() for email in self.ALERT_EMAILS.split(",") if email.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()