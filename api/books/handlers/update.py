from books.handlers.base import get_role, handle_errors, parse_body, path_param, service
from books.utils.response import success_response


@handle_errors
def handler(event: dict, context) -> dict:
    isbn = path_param(event, "isbn")
    book = service.update_book(isbn, parse_body(event), get_role(event))
    return success_response(200, book)
