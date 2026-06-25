"""Business logic for book management operations."""

from datetime import datetime, timezone
from typing import Optional

from books.models.book import BookBatchCreate, BookCreate, BookUpdate
from books.models.errors import BookNotFoundError, ForbiddenError
from books.ports.book_repository import IBookRepository
from books.utils.pagination import decode_token, encode_token


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class BookService:
    """Business logic for book management. Role enforcement happens here."""

    def __init__(self, repository: IBookRepository):
        self._repo = repository

    def create_book(self, data: dict, role: str) -> dict:
        """Validate and persist a new book. Admin only."""
        if role != "admin":
            raise ForbiddenError()
        book = BookCreate(**data)
        item = {
            **book.model_dump(mode="json"),
            "releaseDate": str(book.releaseDate),
            "createdAt": _utcnow(),
            "updatedAt": _utcnow(),
        }
        return self._repo.create(item)

    def create_books_batch(self, data: dict, role: str) -> dict:
        """Create multiple books in a single request. Admin only.

        Processes each book independently — partial success is possible.
        Returns created items and a list of failures with their reasons.
        """
        if role != "admin":
            raise ForbiddenError()
        batch = BookBatchCreate(**data)
        created, failed = [], []
        for book_data in batch.books:
            try:
                item = self.create_book(book_data.model_dump(mode="json"), role)
                created.append(item)
            except Exception as e:
                failed.append({"isbn": book_data.isbn, "reason": str(e)})
        return {"created": created, "failed": failed}

    def get_book(self, isbn: str) -> dict:
        """Return a book by ISBN. Raises BookNotFoundError if not found."""
        item = self._repo.get_by_isbn(isbn)
        if not item:
            raise BookNotFoundError(isbn)
        return item

    def update_book(self, isbn: str, data: dict, role: str) -> dict:
        """Partially update a book. isbn is stripped before validation. Admin only."""
        if role != "admin":
            raise ForbiddenError()
        data.pop("isbn", None)  # isbn cannot be changed — strip before validation
        update = BookUpdate(**data)
        fields = update.model_dump(mode="json", exclude_unset=True)
        if "releaseDate" in fields and fields["releaseDate"] is not None:
            fields["releaseDate"] = str(update.releaseDate)
        fields["updatedAt"] = _utcnow()
        return self._repo.update(isbn, fields)

    def delete_book(self, isbn: str, role: str) -> None:
        """Delete a book by ISBN. Admin only."""
        if role != "admin":
            raise ForbiddenError()
        self._repo.delete(isbn)

    def list_books(
        self,
        filters: dict,
        limit: int = 50,
        next_token: Optional[str] = None,
    ) -> dict:
        """Return a paginated list of books matching the given filters."""
        last_key = decode_token(next_token)
        items, last_key = self._repo.query_with_filter(filters, limit, last_key)
        return {
            "items": items,
            "count": len(items),
            "nextToken": encode_token(last_key),
        }
