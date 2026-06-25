import re
from datetime import date
from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict, field_validator

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class BookCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    isbn: str
    name: str
    authors: list[str]
    languages: list[str]
    countries: list[str]
    numberOfPages: int
    releaseDate: date

    @field_validator("numberOfPages")
    @classmethod
    def pages_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("numberOfPages must be a positive integer.")
        return v

    @field_validator("authors", "languages", "countries")
    @classmethod
    def list_must_not_be_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("must contain at least one item.")
        return v

    @field_validator("languages")
    @classmethod
    def normalize_languages(cls, v: list[str]) -> list[str]:
        # Normalize to ISO 639-1 uppercase codes (e.g. "en", "English" → "EN")
        return [lang.strip().upper() for lang in v]

    @field_validator("countries")
    @classmethod
    def normalize_countries(cls, v: list[str]) -> list[str]:
        # Normalize to ISO 3166-1 alpha-2 uppercase codes (e.g. "us", "US" → "US")
        return [country.strip().upper() for country in v]

    @field_validator("releaseDate", mode="before")
    @classmethod
    def release_date_must_be_iso8601(cls, v) -> str:
        if isinstance(v, str) and not _ISO_DATE_RE.match(v):
            raise ValueError("releaseDate must be in ISO 8601 format: YYYY-MM-DD.")
        return v

    @field_validator("isbn")
    @classmethod
    def isbn_must_be_valid(cls, v: str) -> str:
        digits = v.replace("-", "").replace(" ", "")
        if len(digits) not in (10, 13) or not digits.isdigit():
            raise ValueError("ISBN must be 10 or 13 digits.")
        return v


class BookUpdate(BaseModel):
    """All fields optional. isbn is intentionally excluded — it cannot be changed."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: Optional[str] = None
    authors: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    countries: Optional[list[str]] = None
    numberOfPages: Optional[int] = None
    releaseDate: Optional[date] = None

    @field_validator("numberOfPages")
    @classmethod
    def pages_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("numberOfPages must be a positive integer.")
        return v

    @field_validator("authors", "languages", "countries")
    @classmethod
    def list_must_not_be_empty(cls, v: Optional[list]) -> Optional[list]:
        if v is not None and not v:
            raise ValueError("must contain at least one item.")
        return v

    @field_validator("releaseDate", mode="before")
    @classmethod
    def release_date_must_be_iso8601(cls, v) -> str:
        if isinstance(v, str) and not _ISO_DATE_RE.match(v):
            raise ValueError("releaseDate must be in ISO 8601 format: YYYY-MM-DD.")
        return v

    @field_validator("languages")
    @classmethod
    def normalize_languages(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return [lang.strip().upper() for lang in v] if v else v

    @field_validator("countries")
    @classmethod
    def normalize_countries(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return [country.strip().upper() for country in v] if v else v


class BookBatchCreate(BaseModel):
    """Request body for batch book creation. Maximum 10 books per request."""

    MAX_BATCH_SIZE: ClassVar[int] = 10

    books: list[BookCreate]

    @field_validator("books")
    @classmethod
    def validate_books_list(cls, v: list) -> list:
        if not v:
            raise ValueError("books list must not be empty.")
        if len(v) > BookBatchCreate.MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size must not exceed {BookBatchCreate.MAX_BATCH_SIZE} books per request."
            )
        return v


class BookResponse(BaseModel):
    isbn: str
    name: str
    authors: list[str]
    languages: list[str]
    countries: list[str]
    numberOfPages: int
    releaseDate: str
    createdAt: str
    updatedAt: str
