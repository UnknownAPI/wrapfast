# wrapfast

**wrapfast** is a small Python library with a big opinion: API clients stay maintainable when you **separate concerns** instead of growing a single “do everything” class.

It exists to promote **good practice**, **clear organisation**, and **real flexibility** when you wrap REST (or HTTP-shaped) APIs in Python. You compose a pipeline from a few roles—each one easy to test, swap, or extend—instead of hard‑coding `requests.get` next to auth logic next to JSON parsing next to URL strings scattered across the codebase.

---

## The idea in one glance

| Piece | Responsibility |
|--------|----------------|
| **`Transport`** | How a request leaves your process and bytes come back (`requests`, `httpx`, a mock, async later). |
| **`Session`** | Cross‑cutting behaviour around the wire call: tokens, headers, cookies, tracing, optional response handling. |
| **`PresentationCodec`** | How typed domain objects become bytes and back (JSON + Pydantic, `msgspec`, plain `dict`, …). |
| **`Endpoint`** | A named operation: HTTP method, path, and the request/response types you expect. |
| **`HttpClient`** | The thin orchestrator: build `HttpRequest` → session → transport → session → decode. |

That split is the point: **organisation** (each type has one job), **good practice** (test transports and codecs without the network; test sessions without JSON details), and **flexibility** (change transport or codec without rewriting your endpoints).

---

## Code that shows the shape

This is intentionally dense: it is the whole architecture on one screen.

```python
import json
from dataclasses import dataclass

import requests

from wrapfast import (
    Endpoint,
    HttpClient,
    HttpRequest,
    HttpResponse,
    PresentationCodec,
    Session,
    Transport,
)

# Typed operation: "GET /users/1" → User (no body on the wire for this GET)
@dataclass
class User:
    id: int
    name: str

GET_USER = Endpoint("GET", "users/1", type(None), User)


class RequestsTransport(Transport):
    def send(self, request: HttpRequest) -> HttpResponse:
        r = requests.request(
            request.method,
            request.url,
            headers=request.headers,
            data=request.data or None,
            timeout=30,
        )
        return HttpResponse(r.status_code, {k.lower(): v for k, v in r.headers.items()}, r.content)


class BearerSession(Session):
    def __init__(self, token: str) -> None:
        self._token = token

    def wrap_request(self, request: HttpRequest) -> HttpRequest:
        h = {**request.headers, "authorization": f"Bearer {self._token}"}
        return HttpRequest(request.method, request.url, h, request.data)

    def unwrap_response(self, response: HttpResponse) -> HttpResponse:
        return response  # e.g. 401 → refresh token, logging, metrics


class JsonCodec(PresentationCodec):
    """Tiny stand-in; use Pydantic in production (see examples/)."""

    content_type = "application/json"

    def encode(self, obj: object) -> bytes:
        return b"" if obj is None else json.dumps(obj).encode()

    def decode(self, data: bytes, target: type):
        d = json.loads(data.decode())
        if target is User:
            return User(id=d["id"], name=d["name"])
        raise TypeError(target)


client = HttpClient(
    base_url="https://api.example.com/",
    transport=RequestsTransport(),
    session=BearerSession("<access token>"),
    presentation_codec=JsonCodec(),
)

user = client.send(GET_USER, None)  # User: types follow you, not the wire
```

**`HttpClient`** is the spine: it does not know *which* HTTP library you use, *how* you authenticate, or *how* bodies are serialised. Those are **policies** you inject. Your API surface becomes a set of **`Endpoint`** values plus plain data types—easier to read, review, and reuse.

---

## Why it matters

- **Tests**: fake `Transport` returns canned `HttpResponse`; no sockets.
- **Auth**: evolve `Session` (login, refresh, header rules) without touching codecs.
- **Formats**: swap JSON for another codec at the edge without renaming your domain models’ usage sites.
- **Readability**: endpoints read like a table of operations; the “how we call HTTP” story lives in a few small classes.

---

## Project layout & example

| Path | Role |
|------|------|
| `src/wrapfast/` | Installable package: `HttpClient`, protocols, `Endpoint`. |
| `examples/dummyjson_requests.py` | End‑to‑end sample: `requests`, Pydantic, bearer **session** (login, `/auth/me`, refresh). |

After `pip install wrapfast`, use `import wrapfast`. From a clone without installing, add the `src` directory to `PYTHONPATH` (see **`examples/dummyjson_requests.py`**). A fuller DummyJSON walkthrough lives in that example.

---

## Requirements

Python **3.13+** (see `pyproject.toml`). Runtime dependencies are intentionally minimal; pair the library with **your** transport and codec (e.g. `requests` + Pydantic via the `examples` optional extra).

---

## License

This project is released under the [**0BSD**](https://opensource.org/licenses/0BSD) license (see [`LICENSE`](LICENSE)): use it for anything, with no attribution requirement and minimal legal boilerplate. It is one of the most permissive widely used open-source terms for software.
