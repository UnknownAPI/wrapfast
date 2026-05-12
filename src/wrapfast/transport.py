from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class HttpRequest:
    method: str
    url: str
    headers: dict[str, str]
    data: bytes


@dataclass
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    data: bytes


class Transport(ABC):
    @abstractmethod
    def send(self, request: HttpRequest) -> HttpResponse: ...


class AsyncTransport(ABC):
    @abstractmethod
    async def send(self, request: HttpRequest) -> HttpResponse: ...
