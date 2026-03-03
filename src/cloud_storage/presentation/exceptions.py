from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from cloud_storage.application.exceptions import (
    AlreadyExistsError,
    ApplicationError,
    NotDirectoryError,
    NotFoundError,
    PasswordRequirementError,
    WrongPasswordError,
)
from cloud_storage.domain.exceptions import DomainError


class UnauthorizedError(ApplicationError):
    def __init__(self):
        super().__init__(message="User unauthorized!")


class ExceptionResponseFactory:
    def __init__(self, status_code: int):
        self.status_code = status_code

    def __call__(self, request: Request, exception: Exception) -> JSONResponse:
        return JSONResponse(
            content={"message": getattr(exception, "message", "Internal Server Error")},
            status_code=self.status_code,
        )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, ExceptionResponseFactory(400))
    app.add_exception_handler(NotDirectoryError, ExceptionResponseFactory(400))
    app.add_exception_handler(NotFoundError, ExceptionResponseFactory(404))
    app.add_exception_handler(PasswordRequirementError, ExceptionResponseFactory(400))
    app.add_exception_handler(AlreadyExistsError, ExceptionResponseFactory(409))
    app.add_exception_handler(WrongPasswordError, ExceptionResponseFactory(401))
    app.add_exception_handler(UnauthorizedError, ExceptionResponseFactory(401))
    app.add_exception_handler(ApplicationError, ExceptionResponseFactory(500))
    app.add_exception_handler(Exception, ExceptionResponseFactory(500))
