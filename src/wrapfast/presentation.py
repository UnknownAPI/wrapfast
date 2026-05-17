from abc import ABC, abstractmethod

from .transport import HttpRequest, HttpResponse


class Presentation[T_Req, T_Resp](ABC):
    """Bridges domain base types ↔ HTTP, with per-endpoint narrowing."""

    @abstractmethod
    def encode(self, request: T_Req, *, method: str, url: str) -> HttpRequest: ...

    @abstractmethod
    def decode(self, response: HttpResponse) -> T_Resp: ...

    @abstractmethod
    def narrow[T](self, response: T_Resp, target: type[T]) -> T: ...
