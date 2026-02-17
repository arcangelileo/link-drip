import re
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator


class LinkCreateRequest(BaseModel):
    target_url: str
    custom_slug: str | None = None
    title: str | None = None
    tags: str | None = None  # comma-separated

    @field_validator("target_url")
    @classmethod
    def validate_target_url(cls, v: str) -> str:
        v = v.strip()
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must start with http:// or https://")
        if not parsed.netloc or "." not in parsed.netloc:
            raise ValueError("URL must have a valid domain")
        return v

    @field_validator("custom_slug")
    @classmethod
    def validate_custom_slug(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if not v:
            return None
        if len(v) < 3:
            raise ValueError("Custom slug must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Custom slug must be at most 50 characters")
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", v) and len(v) >= 3:
            if not re.match(r"^[a-z0-9-]+$", v):
                raise ValueError("Slug can only contain lowercase letters, numbers, and hyphens")
            if v.startswith("-") or v.endswith("-"):
                raise ValueError("Slug cannot start or end with a hyphen")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 255:
            raise ValueError("Title must be at most 255 characters")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        # Clean up tags: strip whitespace, remove empties, lowercase
        tags = [t.strip().lower() for t in v.split(",") if t.strip()]
        if not tags:
            return None
        return ",".join(tags)
