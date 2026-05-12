from typing import Any, Protocol


class PresentationCodec(Protocol):
    content_type: str

    def encode(self, obj: Any) -> bytes: ...
    def decode[T](self, data: bytes, target: type[T]) -> T: ...
