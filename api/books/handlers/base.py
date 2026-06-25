import json
import traceback
from typing import Callable

from pydantic import ValidationError

from books.adapters.dynamodb_repository import DynamoDBBookRepository
from books.models.errors import AppError
from books.services.book_service import BookService
from books.utils.response import error_response

# Initialized once on cold start, reused across warm invocations
service = BookService(DynamoDBBookRepository())


def get_role(event: dict) -> str:
    """Extract role from Cognito claims. Returns 'reader' for public endpoints."""
    try:
        claims = event["requestContext"]["authorizer"]["claims"]
        groups = claims.get("cognito:groups", "").split(",")
        return "admin" if "admin" in groups else "reader"
    except (KeyError, TypeError):
        return "reader"


def parse_body(event: dict) -> dict:
    return json.loads(event.get("body") or "{}")


def path_param(event: dict, name: str) -> str:
    return event["pathParameters"][name]


def query_params(event: dict) -> dict:
    return dict(event.get("queryStringParameters") or {})


def handle_errors(fn: Callable) -> Callable:
    """Decorator that catches and maps exceptions to HTTP error responses."""
    def wrapper(event: dict, context) -> dict:
        print(f"Method: {event.get('httpMethod')} Path: {event.get('path')}")
        try:
            return fn(event, context)
        except AppError as e:
            request_id = getattr(context, "aws_request_id", "")
            return error_response(e.status_code, e.code, e.message, request_id)
        except ValidationError as e:
            request_id = getattr(context, "aws_request_id", "")
            return error_response(422, "VALIDATION_ERROR", e.errors()[0]["msg"], request_id)
        except Exception:
            print(traceback.format_exc())
            request_id = getattr(context, "aws_request_id", "")
            return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.", request_id)
    return wrapper
