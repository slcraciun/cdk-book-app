import pytest
from pydantic import ValidationError

from books.models.book import BookBatchCreate, BookCreate, BookUpdate


class TestBookCreate:
    def test_valid_book(self, sample_book):
        book = BookCreate(**sample_book)
        assert book.isbn == "978-0-06-112008-4"
        assert book.name == "To Kill a Mockingbird"

    def test_languages_normalized_to_uppercase(self, sample_book):
        sample_book["languages"] = ["en", "Fr"]
        book = BookCreate(**sample_book)
        assert book.languages == ["EN", "FR"]

    def test_countries_normalized_to_uppercase(self, sample_book):
        sample_book["countries"] = ["us", "Gb"]
        book = BookCreate(**sample_book)
        assert book.countries == ["US", "GB"]

    def test_missing_required_field_raises(self, sample_book):
        del sample_book["name"]
        with pytest.raises(ValidationError):
            BookCreate(**sample_book)

    def test_invalid_isbn_raises(self, sample_book):
        sample_book["isbn"] = "invalid"
        with pytest.raises(ValidationError, match="ISBN must be 10 or 13 digits"):
            BookCreate(**sample_book)

    def test_negative_pages_raises(self, sample_book):
        sample_book["numberOfPages"] = -1
        with pytest.raises(ValidationError, match="numberOfPages must be a positive integer"):
            BookCreate(**sample_book)

    def test_zero_pages_raises(self, sample_book):
        sample_book["numberOfPages"] = 0
        with pytest.raises(ValidationError, match="numberOfPages must be a positive integer"):
            BookCreate(**sample_book)

    def test_empty_authors_raises(self, sample_book):
        sample_book["authors"] = []
        with pytest.raises(ValidationError, match="must contain at least one item"):
            BookCreate(**sample_book)

    def test_invalid_release_date_format_raises(self, sample_book):
        sample_book["releaseDate"] = "11-07-1960"
        with pytest.raises(ValidationError, match="ISO 8601"):
            BookCreate(**sample_book)

    def test_valid_isbn_10(self, sample_book):
        sample_book["isbn"] = "0061120081"
        book = BookCreate(**sample_book)
        assert book.isbn == "0061120081"


class TestBookUpdate:
    def test_all_fields_optional(self):
        update = BookUpdate()
        assert update.name is None
        assert update.numberOfPages is None

    def test_partial_update(self):
        update = BookUpdate(name="New Title")
        assert update.name == "New Title"
        assert update.authors is None

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            BookUpdate(unknownField="value")

    def test_isbn_not_a_field(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            BookUpdate(isbn="978-0-06-112008-4")

    def test_languages_normalized_to_uppercase(self):
        update = BookUpdate(languages=["en", "fr"])
        assert update.languages == ["EN", "FR"]

    def test_negative_pages_raises(self):
        with pytest.raises(ValidationError, match="numberOfPages must be a positive integer"):
            BookUpdate(numberOfPages=-5)


class TestBookBatchCreate:
    def test_valid_batch(self, sample_book):
        batch = BookBatchCreate(books=[sample_book])
        assert len(batch.books) == 1

    def test_empty_books_list_raises(self):
        with pytest.raises(ValidationError, match="must not be empty"):
            BookBatchCreate(books=[])

    def test_exceeds_max_batch_size_raises(self, sample_book):
        books = []
        for i in range(BookBatchCreate.MAX_BATCH_SIZE + 1):
            book = sample_book.copy()
            book["isbn"] = f"978000000{i:04d}"  # valid 13-digit ISBN
            books.append(book)
        with pytest.raises(ValidationError, match="must not exceed"):
            BookBatchCreate(books=books)
