from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
	pass


class Account(Base):
	__tablename__ = "accounts"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	page_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
	ig_business_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
	wa_phone_number_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
	encrypted_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Product(Base):
	__tablename__ = "products"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
	name: Mapped[str] = mapped_column(String(255))
	description: Mapped[Optional[str]] = mapped_column(Text)
	price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
	stock: Mapped[Optional[int]] = mapped_column(Integer)
	image_url: Mapped[Optional[str]] = mapped_column(Text)
	category: Mapped[Optional[str]] = mapped_column(String(128))
	updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PostTask(Base):
	__tablename__ = "post_tasks"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	text: Mapped[str] = mapped_column(Text)
	media_url: Mapped[Optional[str]] = mapped_column(Text)
	destination: Mapped[str] = mapped_column(String(16))  # fb, ig, both
	scheduled_at: Mapped[datetime] = mapped_column(DateTime, index=True)
	status: Mapped[str] = mapped_column(String(16), default="scheduled")  # scheduled, posted, failed
	result_ref: Mapped[Optional[str]] = mapped_column(Text)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MessageLog(Base):
	__tablename__ = "message_logs"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	platform: Mapped[str] = mapped_column(String(16))  # fb, ig, wa
	conversation_id: Mapped[Optional[str]] = mapped_column(String(128))
	sender_id: Mapped[Optional[str]] = mapped_column(String(128))
	recipient_id: Mapped[Optional[str]] = mapped_column(String(128))
	message_type: Mapped[str] = mapped_column(String(32))  # comment, dm, wa
	message_text: Mapped[Optional[str]] = mapped_column(Text)
	matched_rule: Mapped[Optional[str]] = mapped_column(String(128))
	responded: Mapped[bool] = mapped_column(Boolean, default=False)
	error: Mapped[Optional[str]] = mapped_column(Text)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InboxRule(Base):
	__tablename__ = "inbox_rules"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	keyword: Mapped[str] = mapped_column(String(128), index=True)
	response_text: Mapped[Optional[str]] = mapped_column(Text)
	silent_hours_start: Mapped[Optional[str]] = mapped_column(String(5))  # HH:MM
	silent_hours_end: Mapped[Optional[str]] = mapped_column(String(5))
	escalate_to_human: Mapped[bool] = mapped_column(Boolean, default=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)