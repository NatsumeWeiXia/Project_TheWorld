from fastapi import status


class AppError(Exception):
    def __init__(self, code: int, message: str, http_status: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class ErrorCodes:
    OK = 0
    VALIDATION = 1001
    NOT_FOUND = 1002
    CONFLICT = 1003
    INHERITANCE_CYCLE = 1004
    INVALID_SCHEMA = 1005
    RETRIEVAL_UNAVAILABLE = 2001
    VECTOR_TIMEOUT = 2002
    INTERNAL = 9000
