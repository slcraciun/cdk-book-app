from books.handlers.base import get_role, handle_errors, parse_body, service
from books.utils.response import success_response


@handle_errors
def handler(event: dict, context) -> dict:
    result = service.create_books_batch(parse_body(event), get_role(event))
    status_code = 201 if not result["failed"] else 207
    return success_response(status_code, result)
