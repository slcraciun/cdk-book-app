from typing import Optional, Protocol


class IBookRepository(Protocol):
    def create(self, item: dict) -> dict: ...

    def get_by_isbn(self, isbn: str) -> Optional[dict]: ...

    def update(self, isbn: str, fields: dict) -> dict: ...

    def delete(self, isbn: str) -> None: ...

    def query_with_filter(
        self,
        filters: dict,
        limit: int,
        last_key: Optional[dict],
    ) -> tuple[list, Optional[dict]]: ...
