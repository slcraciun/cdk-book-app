from books.handlers.base import get_role, handle_errors, path_param, service
from books.utils.response import success_response


@handle_errors
def handler(event: dict, context) -> dict:
    service.delete_book(path_param(event, "isbn"), get_role(event))
    return success_response(204, {})
