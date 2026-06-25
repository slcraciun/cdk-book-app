import os

import boto3
import pytest
from moto import mock_aws

from books.adapters.dynamodb_repository import DynamoDBBookRepository
from books.models.errors import BookNotFoundError, IsbnConflictError


@pytest.fixture
def dynamodb_table():
    with mock_aws():
        os.environ["TABLE_NAME"] = "books-test"
        os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName="books-test",
            KeySchema=[{"AttributeName": "isbn", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "isbn", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield DynamoDBBookRepository()


@pytest.fixture
def sample_item():
    return {
        "isbn": "978-0-06-112008-4",
        "name": "To Kill a Mockingbird",
        "authors": ["Harper Lee"],
        "languages": ["EN"],
        "countries": ["US"],
        "numberOfPages": 281,
        "releaseDate": "1960-07-11",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }


class TestCreate:
    def test_create_success(self, dynamodb_table, sample_item):
        result = dynamodb_table.create(sample_item)
        assert result["isbn"] == sample_item["isbn"]

    def test_create_returns_item(self, dynamodb_table, sample_item):
        result = dynamodb_table.create(sample_item)
        assert result["name"] == sample_item["name"]

    def test_create_duplicate_raises(self, dynamodb_table, sample_item):
        dynamodb_table.create(sample_item)
        with pytest.raises(IsbnConflictError):
            dynamodb_table.create(sample_item)


class TestGetByIsbn:
    def test_get_existing_item(self, dynamodb_table, sample_item):
        dynamodb_table.create(sample_item)
        result = dynamodb_table.get_by_isbn(sample_item["isbn"])
        assert result["isbn"] == sample_item["isbn"]
        assert result["name"] == sample_item["name"]

    def test_get_nonexistent_returns_none(self, dynamodb_table):
        result = dynamodb_table.get_by_isbn("978-0-00-000000-0")
        assert result is None


class TestUpdate:
    def test_update_success(self, dynamodb_table, sample_item):
        dynamodb_table.create(sample_item)
        result = dynamodb_table.update(sample_item["isbn"], {"name": "New Title"})
        assert result["name"] == "New Title"

    def test_update_preserves_other_fields(self, dynamodb_table, sample_item):
        dynamodb_table.create(sample_item)
        result = dynamodb_table.update(sample_item["isbn"], {"numberOfPages": 300})
        assert result["name"] == sample_item["name"]
        assert result["numberOfPages"] == 300

    def test_update_nonexistent_raises(self, dynamodb_table):
        with pytest.raises(BookNotFoundError):
            dynamodb_table.update("978-0-00-000000-0", {"name": "New Title"})

    def test_update_returns_full_item(self, dynamodb_table, sample_item):
        dynamodb_table.create(sample_item)
        result = dynamodb_table.update(sample_item["isbn"], {"name": "New Title"})
        assert "createdAt" in result
        assert "updatedAt" in result


class TestDelete:
    def test_delete_success(self, dynamodb_table, sample_item):
        dynamodb_table.create(sample_item)
        dynamodb_table.delete(sample_item["isbn"])
        assert dynamodb_table.get_by_isbn(sample_item["isbn"]) is None

    def test_delete_nonexistent_raises(self, dynamodb_table):
        with pytest.raises(BookNotFoundError):
            dynamodb_table.delete("978-0-00-000000-0")


class TestQueryWithFilter:
    def test_no_filter_returns_all(self, dynamodb_table, sample_item):
        dynamodb_table.create(sample_item)
        items, last_key = dynamodb_table.query_with_filter({}, limit=50, last_key=None)
        assert len(items) == 1

    def test_filter_by_language(self, dynamodb_table, sample_item):
        dynamodb_table.create(sample_item)
        items, _ = dynamodb_table.query_with_filter({"languages": "EN"}, limit=50, last_key=None)
        assert len(items) == 1

    def test_filter_no_match_returns_empty(self, dynamodb_table, sample_item):
        dynamodb_table.create(sample_item)
        items, _ = dynamodb_table.query_with_filter({"languages": "FR"}, limit=50, last_key=None)
        assert len(items) == 0

    def test_filter_by_author(self, dynamodb_table, sample_item):
        dynamodb_table.create(sample_item)
        items, _ = dynamodb_table.query_with_filter(
            {"authors": "Harper Lee"}, limit=50, last_key=None
        )
        assert len(items) == 1

    def test_multi_value_or_filter(self, dynamodb_table, sample_item):
        second = {**sample_item, "isbn": "978-0-7432-7356-5", "languages": ["FR"]}
        dynamodb_table.create(sample_item)
        dynamodb_table.create(second)
        items, _ = dynamodb_table.query_with_filter(
            {"languages": ["EN", "FR"]}, limit=50, last_key=None
        )
        assert len(items) == 2

    def test_cross_field_and_filter(self, dynamodb_table, sample_item):
        second = {**sample_item, "isbn": "978-0-7432-7356-5", "countries": ["GB"]}
        dynamodb_table.create(sample_item)
        dynamodb_table.create(second)
        items, _ = dynamodb_table.query_with_filter(
            {"languages": "EN", "countries": "US"}, limit=50, last_key=None
        )
        assert len(items) == 1
        assert items[0]["isbn"] == sample_item["isbn"]

    def test_limit_caps_results(self, dynamodb_table, sample_item):
        for i in range(5):
            item = {**sample_item, "isbn": f"978000000{i:04d}"}
            dynamodb_table.create(item)
        items, _ = dynamodb_table.query_with_filter({}, limit=2, last_key=None)
        assert len(items) == 2
