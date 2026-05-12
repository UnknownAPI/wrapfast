from dataclasses import dataclass

from .presentation import PresentationCodec
from .session import Session
from .transport import HttpRequest, Transport


@dataclass
class Endpoint[T_Request, T_Response]:
    method: str
    path: str
    request_type: type[T_Request]
    response_type: type[T_Response]


class HttpClient:
    def __init__(
        self,
        base_url: str,
        transport: Transport,
        session: Session,
        presentation_codec: PresentationCodec,
    ) -> None:
        self._base_url = base_url
        self._transport = transport
        self._session = session
        self._presentation_codec = presentation_codec

    def send[T_Request, T_Response](
        self, endpoint: Endpoint[T_Request, T_Response], request: T_Request
    ) -> T_Response:
        http_req = HttpRequest(
            method=endpoint.method,
            url=f"{self._base_url}{endpoint.path}"
            if not endpoint.path.startswith("/")
            else endpoint.path,
            headers={"Content-Type": self._presentation_codec.content_type},
            data=self._presentation_codec.encode(request),
        )
        http_req = self._session.wrap_request(http_req)
        http_resp = self._transport.send(http_req)
        http_resp = self._session.unwrap_response(http_resp)
        return self._presentation_codec.decode(http_resp.data, endpoint.response_type)
