from src.transport import HttpRequest, HttpResponse
from typing import Protocol

class Session(Protocol):
    def wrap_request(self, request: HttpRequest) -> HttpRequest:
        ...
    def unwrap_response(self, response: HttpResponse) -> HttpResponse:
        ...
