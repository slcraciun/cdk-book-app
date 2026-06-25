from books.handlers.base import get_role, handle_errors, parse_body, service
from books.utils.response import success_response


@handle_errors
def handler(event: dict, context) -> dict:
    book = service.create_book(parse_body(event), get_role(event))
    return success_response(201, book)
