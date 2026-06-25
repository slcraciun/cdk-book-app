from typing import Optional

from books.models.errors import BookNotFoundError, IsbnConflictError


class InMemoryBookRepository:
    """Pure Python test double for IBookRepository. No AWS dependencies."""

    def __init__(self):
        self._store: dict[str, dict] = {}

    def create(self, item: dict) -> dict:
        if item["isbn"] in self._store:
            raise IsbnConflictError(item["isbn"])
        self._store[item["isbn"]] = item
        return item

    def get_by_isbn(self, isbn: str) -> Optional[dict]:
        return self._store.get(isbn)

    def update(self, isbn: str, fields: dict) -> dict:
        if isbn not in self._store:
            raise BookNotFoundError(isbn)
        self._store[isbn] = {**self._store[isbn], **fields}
        return self._store[isbn]

    def delete(self, isbn: str) -> None:
        if isbn not in self._store:
            raise BookNotFoundError(isbn)
        del self._store[isbn]

    def query_with_filter(
        self,
        filters: dict,
        limit: int,
        last_key: Optional[dict],
    ) -> tuple[list, Optional[dict]]:
        items = list(self._store.values())
        for key, val in filters.items():
            vals = val if isinstance(val, list) else [val]
            if key in ("authors", "languages", "countries"):
                items = [i for i in items if any(v in i.get(key, []) for v in vals)]
            else:
                items = [i for i in items if i.get(key) in vals]
        return items[:limit], None
