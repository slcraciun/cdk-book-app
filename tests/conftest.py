import pytest
from books.services.book_service import BookService

from tests.fakes.in_memory_repository import InMemoryBookRepository

SAMPLE_BOOK_DATA = {
    "isbn": "978-0-06-112008-4",
    "name": "To Kill a Mockingbird",
    "authors": ["Harper Lee"],
    "languages": ["EN"],
    "countries": ["US"],
    "numberOfPages": 281,
    "releaseDate": "1960-07-11",
}


@pytest.fixture
def repo():
    return InMemoryBookRepository()


@pytest.fixture
def service(repo):
    return BookService(repo)


@pytest.fixture
def sample_book():
    return SAMPLE_BOOK_DATA.copy()
