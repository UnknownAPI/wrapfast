from dataclasses import dataclass
from typing import Protocol


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


class Transport(Protocol):
    def send(self, request: HttpRequest) -> HttpResponse:
        ...


class AsyncTransport(Protocol):
    async def send(self, request: HttpRequest) -> HttpResponse:
        ...
