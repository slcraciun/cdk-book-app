class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BookNotFoundError(AppError):
    status_code = 404
    code = "BOOK_NOT_FOUND"

    def __init__(self, isbn: str):
        super().__init__(f"Book with ISBN '{isbn}' not found.")


class IsbnConflictError(AppError):
    status_code = 409
    code = "ISBN_CONFLICT"

    def __init__(self, isbn: str):
        super().__init__(f"A book with ISBN '{isbn}' already exists.")


class IsbnMismatchError(AppError):
    status_code = 400
    code = "ISBN_MISMATCH"

    def __init__(self):
        super().__init__("ISBN in the request body does not match the path parameter.")


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"

    def __init__(self):
        super().__init__("You do not have permission to perform this action.")


class MethodNotAllowedError(AppError):
    status_code = 405
    code = "METHOD_NOT_ALLOWED"

    def __init__(self):
        super().__init__("Method not allowed.")
