from books.handlers.base import handle_errors, query_params, service
from books.utils.response import success_response


def _parse_params(event: dict) -> tuple[dict, int, str | None]:
    """Extract and normalise query parameters.

    Comma-separated values on the same field are split into a list for OR filtering.
    Example: ?countries=EN,RO  →  {"countries": ["EN", "RO"]}
    """
    raw = query_params(event)
    next_token = raw.pop("nextToken", None)
    limit = int(raw.pop("limit", 50))
    filters = {k: v.split(",") if "," in v else v for k, v in raw.items()}
    return filters, limit, next_token


@handle_errors
def handler(event: dict, context) -> dict:
    filters, limit, next_token = _parse_params(event)
    result = service.list_books(filters, limit, next_token)
    return success_response(200, result)
