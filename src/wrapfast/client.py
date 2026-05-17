from dataclasses import dataclass

from .presentation import Presentation
from .session import Session
from .transport import Transport


@dataclass(frozen=True)
class Endpoint[T_Response]:
    method: str
    path: str
    response_type: type[T_Response]


class HttpClient[T_Req, T_Resp]:
    def __init__(
        self,
        base_url: str,
        transport: Transport,
        session: Session[T_Req, T_Resp],
        presentation: Presentation[T_Req, T_Resp],
    ) -> None:
        self._base_url = base_url
        self._transport = transport
        self._session = session
        self._presentation = presentation

    def send[T_Response](
        self,
        endpoint: Endpoint[T_Response],
        request: T_Req,
    ) -> T_Response:
        wrapped = self._session.wrap(request)
        http_req = self._presentation.encode(
            wrapped, method=endpoint.method, url=f"{self._base_url}{endpoint.path}"
        )
        http_resp = self._transport.send(http_req)
        base_resp = self._presentation.decode(http_resp)
        validated = self._session.unwrap(base_resp)
        return self._presentation.narrow(validated, endpoint.response_type)
