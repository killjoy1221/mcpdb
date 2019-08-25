import abc
from typing import Tuple, Any


class BaseHttpError(Exception, abc.ABC):
    _code: int

    @property
    def response(self) -> Tuple[Any, int]:
        return dict(
            error=type(self).__name__,
            message=str(self)
        ), self._code


def _create_error(name, code):
    class ExHttpError(BaseHttpError):
        _code = code

    ExHttpError.__name__ = name
    return ExHttpError


BadRequest = _create_error("Bad Request", 400)
Unauthorized = _create_error("Unauthorized", 401)
Forbidden = _create_error("Forbidden", 403)
NotFound = _create_error("Not Found", 404)

InternalServerError = _create_error("Internal Server Error", 500)
