from typing import Protocol

from .transport import HttpRequest, HttpResponse


class Session(Protocol):
    def wrap_request(self, request: HttpRequest) -> HttpRequest:
        ...

    def unwrap_response(self, response: HttpResponse) -> HttpResponse:
        ...
