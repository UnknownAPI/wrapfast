# wrapfast

**wrapfast** is a small Python library with a big opinion: API clients stay maintainable when you **separate concerns** instead of growing a single “do everything” class.

It exists to promote **good practice**, **clear organisation**, and **real flexibility** when you wrap REST (or HTTP-shaped) APIs in Python. You compose a pipeline from a few roles—each one easy to test, swap, or extend—instead of hard‑coding `requests.get` next to auth logic next to JSON parsing next to URL strings scattered across the codebase.

---

## The idea in one glance

| Piece | Responsibility |
|--------|----------------|
| **`Transport`** | How a request leaves your process and bytes come back (`requests`, `httpx`, a mock, async later). |
| **`Presentation`** | How domain objects become `HttpRequest` (encode), and `HttpResponse` becomes intermediate objects (decode), and intermediate objects become final domain models (narrow). |
| **`Session`** | Cross-cutting behaviour on the intermediate types (e.g. `JsonRequest`, `JsonResponse`): tokens, headers, error-checking. |
| **`Endpoint`** | A named operation: HTTP method, path, and the response type you expect. |
| **`HttpClient`** | The orchestrator: `Session.wrap` → `Presentation.encode` → `Transport.send` → `Presentation.decode` → `Session.unwrap` → `Presentation.narrow`. |

That split is the point: **organisation** (each type has one job), **good practice** (test transports and codecs without the network; test sessions without JSON details), and **flexibility** (change transport or codec without rewriting your endpoints).

---

## Code that shows the shape

This is intentionally dense: it is the whole architecture on one screen, using **Pydantic** for request/response models and JSON.

```python
import json
import requests
from dataclasses import dataclass
from typing import Any
from pydantic import BaseModel, ConfigDict

from wrapfast import (
    Endpoint,
    HttpClient,
    HttpRequest,
    HttpResponse,
    Presentation,
    Session,
    Transport,
)

@dataclass
class JsonRequest:
    headers: dict[str, str]
    body: dict[str, Any]

@dataclass
class JsonResponse:
    status: int
    body: Any

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str

GET_USER = Endpoint("GET", "users/1", User)

class RequestsTransport(Transport):
    def send(self, request: HttpRequest) -> HttpResponse:
        r = requests.request(
            request.method,
            request.url,
            headers=request.headers,
            data=request.data or None,
            timeout=30,
        )
        return HttpResponse(
            status_code=r.status_code, 
            headers={k.lower(): v for k, v in r.headers.items()}, 
            data=r.content
        )

class BearerSession(Session[JsonRequest, JsonResponse]):
    def __init__(self, token: str) -> None:
        self._token = token

    def wrap(self, request: JsonRequest) -> JsonRequest:
        request.headers["Authorization"] = f"Bearer {self._token}"
        return request

    def unwrap(self, response: JsonResponse) -> JsonResponse:
        if response.status == 401:
            raise RuntimeError("Unauthorized")
        return response

class PydanticPresentation(Presentation[JsonRequest, JsonResponse]):
    def encode(self, request: JsonRequest, *, method: str, url: str) -> HttpRequest:
        return HttpRequest(
            method=method,
            url=url,
            headers={"Content-Type": "application/json", **request.headers},
            data=json.dumps(request.body).encode("utf-8") if request.body else b"",
        )

    def decode(self, response: HttpResponse) -> JsonResponse:
        body = json.loads(response.data) if response.data else {}
        return JsonResponse(status=response.status_code, body=body)

    def narrow[T](self, response: JsonResponse, target: type[T]) -> T:
        if issubclass(target, BaseModel):
            return target.model_validate(response.body)
        raise TypeError("target must be a BaseModel subclass")

client = HttpClient[JsonRequest, JsonResponse](
    base_url="https://api.example.com/",
    transport=RequestsTransport(),
    session=BearerSession("<access token>"),
    presentation=PydanticPresentation(),
)

user = client.send(GET_USER, JsonRequest(headers={}, body={}))  # User: validated model
```

Add **`pydantic`** and **`requests`** to your environment when using this pattern (also bundled as the optional **`examples`** extra in this repo).

**`HttpClient`** is the spine: it does not know *which* HTTP library you use, *how* you authenticate, or *how* bodies are serialised. Those are **policies** you inject. Your API surface becomes a set of **`Endpoint`** values plus **Pydantic models** (or other types you teach the codec)—easier to read, review, and reuse.

`Presentation`, `Transport`, and `Session` are abstract bases (`abc.ABC`). Codecs implement `encode`, `decode`, and `narrow`; transports and sessions implement the `send` / `wrap` / `unwrap` hooks shown above.

---

## Why it matters

- **Tests**: fake `Transport` returns canned `HttpResponse`; no sockets.
- **Auth**: evolve `Session` (login, refresh, header rules) without touching codecs.
- **Formats**: swap JSON for another presentation at the edge without renaming your domain models’ usage sites.
- **Readability**: endpoints read like a table of operations; the “how we call HTTP” story lives in a few small classes.

---

## Project layout & example

| Path | Path Role |
|------|------|
| `src/wrapfast/` | Installable package: `HttpClient`, protocols, `Endpoint`. |
| `examples/dummyjson_requests.py` | End‑to‑end sample: `requests`, Pydantic, bearer **session** (login, `/auth/me`, refresh). |

After `pip install wrapfast`, use `import wrapfast`. From a clone without installing, add the `src` directory to `PYTHONPATH` (see **`examples/dummyjson_requests.py`**). A fuller DummyJSON walkthrough lives in that example.

---

## Requirements

Python **3.13+** (see `pyproject.toml`). The library itself has no required runtime dependencies; pair it with **your** transport and codec. The README snippet and **`examples`** extra use **Pydantic** and **`requests`**.

---

## License

This project is released under the [**0BSD**](https://opensource.org/licenses/0BSD) license (see [`LICENSE`](LICENSE)): use it for anything, with no attribution requirement and minimal legal boilerplate. It is one of the most permissive widely used open-source terms for software.
