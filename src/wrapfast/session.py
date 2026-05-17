# session.py
from abc import ABC, abstractmethod


class Session[T_Req, T_Resp](ABC):
    """Domain-level session concerns: auth on requests, error-checking on responses."""

    @abstractmethod
    def wrap(self, request: T_Req) -> T_Req: ...

    @abstractmethod
    def unwrap(self, response: T_Resp) -> T_Resp: ...
