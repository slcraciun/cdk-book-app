import os
from functools import reduce
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from books.models.errors import BookNotFoundError, IsbnConflictError


class DynamoDBBookRepository:
    def __init__(self):
        self._table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

    def create(self, item: dict) -> dict:
        """Write a new book item. Raises IsbnConflictError if the ISBN already exists."""
        try:
            self._table.put_item(
                Item=item,
                ConditionExpression=Attr("isbn").not_exists(),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise IsbnConflictError(item["isbn"]) from e
            raise
        return item

    def get_by_isbn(self, isbn: str) -> Optional[dict]:
        """Return the book with the given ISBN, or None if it does not exist."""
        response = self._table.get_item(Key={"isbn": isbn})
        return response.get("Item")

    def update(self, isbn: str, fields: dict) -> dict:
        """Partially update a book. Raises BookNotFoundError if the ISBN does not exist.

        Builds a dynamic UpdateExpression from the provided fields dict.
        Field name aliases (#) are used to avoid conflicts with DynamoDB reserved words.
        Returns the full updated item via ReturnValues=ALL_NEW.
        """
        update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in fields)
        expr_names  = {f"#{k}": k for k in fields}
        expr_values = {f":{k}": v for k, v in fields.items()}

        try:
            response = self._table.update_item(
                Key={"isbn": isbn},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ConditionExpression=Attr("isbn").exists(),
                ReturnValues="ALL_NEW",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise BookNotFoundError(isbn) from e
            raise
        return response["Attributes"]

    def delete(self, isbn: str) -> None:
        """Delete a book by ISBN. Raises BookNotFoundError if the ISBN does not exist."""
        try:
            self._table.delete_item(
                Key={"isbn": isbn},
                ConditionExpression=Attr("isbn").exists(),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise BookNotFoundError(isbn) from e
            raise

    def query_with_filter(
        self,
        filters: dict,
        limit: int,
        last_key: Optional[dict],
    ) -> tuple[list, Optional[dict]]:
        """Scan the table with optional AND filter and pagination.

        Returns a tuple of (items, last_evaluated_key). Pass last_evaluated_key
        as last_key on the next call to retrieve the following page.
        """
        filter_expr = self._build_filter_expression(filters)

        kwargs: dict = {"Limit": limit}
        if filter_expr is not None:
            kwargs["FilterExpression"] = filter_expr
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key

        response = self._table.scan(**kwargs)
        return response.get("Items", []), response.get("LastEvaluatedKey")

    @staticmethod
    def _build_filter_expression(filters: dict) -> Optional[Attr]:
        """Build a combined AND FilterExpression from the filters dict.

        - author            → contains(authors, val)
        - languages/countries → contains(field, val)
        - other fields      → exact equality match

        When a filter value is a list (comma-separated in the request),
        each value in the list is combined with OR within that field:
          ?countries=EN,RO  →  contains(countries, EN) | contains(countries, RO)

        Multiple fields are combined with AND:
          ?countries=EN&languages=FR  →  contains(countries, EN) & contains(languages, FR)
        """
        def _field_condition(key: str, val) -> Attr:
            values = val if isinstance(val, list) else [val]

            if key in ("authors", "languages", "countries"):
                conditions = [Attr(key).contains(v) for v in values]
            else:
                conditions = [Attr(key).eq(v) for v in values]

            return reduce(lambda a, b: a | b, conditions)

        expr = None
        for key, val in filters.items():
            condition = _field_condition(key, val)
            expr = condition if expr is None else expr & condition
        return expr
