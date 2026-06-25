import pytest

from books.models.errors import BookNotFoundError, ForbiddenError, IsbnConflictError


class TestCreateBook:
    def test_create_success(self, service, sample_book):
        result = service.create_book(sample_book, role="admin")
        assert result["isbn"] == sample_book["isbn"]
        assert result["name"] == sample_book["name"]
        assert "createdAt" in result
        assert "updatedAt" in result

    def test_create_forbidden_for_reader(self, service, sample_book):
        with pytest.raises(ForbiddenError):
            service.create_book(sample_book, role="reader")

    def test_create_duplicate_isbn_raises(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        with pytest.raises(IsbnConflictError):
            service.create_book(sample_book, role="admin")

    def test_create_stores_all_fields(self, service, sample_book):
        result = service.create_book(sample_book, role="admin")
        assert result["authors"] == sample_book["authors"]
        assert result["languages"] == ["EN"]
        assert result["countries"] == ["US"]
        assert result["numberOfPages"] == sample_book["numberOfPages"]
        assert result["releaseDate"] == sample_book["releaseDate"]


class TestGetBook:
    def test_get_existing_book(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        result = service.get_book(sample_book["isbn"])
        assert result["isbn"] == sample_book["isbn"]

    def test_get_nonexistent_book_raises(self, service):
        with pytest.raises(BookNotFoundError):
            service.get_book("978-0-00-000000-0")


class TestUpdateBook:
    def test_update_success(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        result = service.update_book(sample_book["isbn"], {"name": "New Title"}, role="admin")
        assert result["name"] == "New Title"

    def test_update_forbidden_for_reader(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        with pytest.raises(ForbiddenError):
            service.update_book(sample_book["isbn"], {"name": "New Title"}, role="reader")

    def test_update_nonexistent_book_raises(self, service):
        with pytest.raises(BookNotFoundError):
            service.update_book("978-0-00-000000-0", {"name": "New Title"}, role="admin")

    def test_update_isbn_in_payload_is_ignored(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        result = service.update_book(
            sample_book["isbn"],
            {"isbn": "978-0-00-000000-0", "name": "New Title"},
            role="admin",
        )
        assert result["isbn"] == sample_book["isbn"]
        assert result["name"] == "New Title"

    def test_update_sets_updated_at(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        result = service.update_book(sample_book["isbn"], {"name": "New Title"}, role="admin")
        assert "updatedAt" in result

    def test_partial_update_preserves_other_fields(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        result = service.update_book(sample_book["isbn"], {"numberOfPages": 300}, role="admin")
        assert result["name"] == sample_book["name"]
        assert result["numberOfPages"] == 300


class TestDeleteBook:
    def test_delete_success(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        service.delete_book(sample_book["isbn"], role="admin")
        with pytest.raises(BookNotFoundError):
            service.get_book(sample_book["isbn"])

    def test_delete_forbidden_for_reader(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        with pytest.raises(ForbiddenError):
            service.delete_book(sample_book["isbn"], role="reader")

    def test_delete_nonexistent_book_raises(self, service):
        with pytest.raises(BookNotFoundError):
            service.delete_book("978-0-00-000000-0", role="admin")


class TestListBooks:
    def test_list_returns_all_books(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        result = service.list_books({})
        assert result["count"] == 1
        assert result["items"][0]["isbn"] == sample_book["isbn"]

    def test_list_empty_table(self, service):
        result = service.list_books({})
        assert result["count"] == 0
        assert result["items"] == []

    def test_list_filter_by_language(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        result = service.list_books({"languages": "EN"})
        assert result["count"] == 1

    def test_list_filter_no_match_returns_empty(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        result = service.list_books({"languages": "FR"})
        assert result["count"] == 0

    def test_list_next_token_is_none_when_no_more_pages(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        result = service.list_books({})
        assert result["nextToken"] is None


class TestCreateBooksBatch:
    def test_batch_all_success(self, service, sample_book):
        second = sample_book.copy()
        second["isbn"] = "978-0-7432-7356-5"
        result = service.create_books_batch({"books": [sample_book, second]}, role="admin")
        assert len(result["created"]) == 2
        assert result["failed"] == []

    def test_batch_partial_failure_on_duplicate(self, service, sample_book):
        service.create_book(sample_book, role="admin")
        result = service.create_books_batch({"books": [sample_book]}, role="admin")
        assert len(result["created"]) == 0
        assert len(result["failed"]) == 1
        assert result["failed"][0]["isbn"] == sample_book["isbn"]

    def test_batch_forbidden_for_reader(self, service, sample_book):
        with pytest.raises(ForbiddenError):
            service.create_books_batch({"books": [sample_book]}, role="reader")
