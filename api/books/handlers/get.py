from books.handlers.base import handle_errors, path_param, service
from books.utils.response import success_response


@handle_errors
def handler(event: dict, context) -> dict:
    book = service.get_book(path_param(event, "isbn"))
    return success_response(200, book)
