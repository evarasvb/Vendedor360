from typing import Optional

from pydantic import AnyHttpUrl, BaseModel, Field, HttpUrl, ValidationError


class MediaUrl(BaseModel):
	url: HttpUrl = Field(...)


def is_nonempty_string(value: Optional[str]) -> bool:
	return bool(value and value.strip())