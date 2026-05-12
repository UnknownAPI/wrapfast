from abc import ABC, abstractmethod

from .transport import HttpRequest, HttpResponse


class Session(ABC):
    @abstractmethod
    def wrap_request(self, request: HttpRequest) -> HttpRequest: ...

    @abstractmethod
    def unwrap_response(self, response: HttpResponse) -> HttpResponse: ...
