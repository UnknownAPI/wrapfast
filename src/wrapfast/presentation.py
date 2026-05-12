from abc import ABC, abstractmethod
from typing import Any


class PresentationCodec(ABC):
    @abstractmethod
    def get_content_type(self) -> str: ...

    @abstractmethod
    def encode(self, obj: Any) -> bytes: ...

    @abstractmethod
    def decode(self, data: bytes, target: type) -> Any: ...
