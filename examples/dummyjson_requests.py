"""
Example: wrapfast HttpClient + DummyJSON (https://dummyjson.com) using `requests`,
Pydantic models, and a **Session** that injects ``Authorization: Bearer …`` after login
and updates tokens after refresh.

Install from the repo root::

    pip install requests pydantic
    # or: uv venv && uv sync --extra examples

Run::

    python examples/dummyjson_requests.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, ConfigDict

# Repo layout: package lives under src/wrapfast/ (add ``src`` so ``import wrapfast`` works without install).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wrapfast import Endpoint, HttpClient, HttpRequest, HttpResponse


def _url_resource_path(url: str) -> str:
    """``https://dummyjson.com/auth/me`` -> ``auth/me``."""
    return urlparse(url).path.lstrip("/")


class RequestsTransport:
    """Bridge wrapfast's HttpRequest/HttpResponse to the `requests` library."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def send(self, request: HttpRequest) -> HttpResponse:
        resp = requests.request(
            method=request.method,
            url=request.url,
            headers=request.headers,
            data=request.data or None,
            timeout=self._timeout,
        )
        return HttpResponse(
            status_code=resp.status_code,
            headers={k.lower(): v for k, v in resp.headers.items()},
            data=resp.content,
        )


# --- DummyJSON shapes (subset of real responses; extra JSON keys ignored) ---


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    username: str
    email: str
    firstName: str
    lastName: str
    gender: str
    image: str
    accessToken: str
    refreshToken: str


class MeResponse(BaseModel):
    """Subset of ``GET /auth/me`` (current user)."""

    model_config = ConfigDict(extra="ignore")

    id: int
    username: str
    email: str
    firstName: str
    lastName: str


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refreshToken: str
    expiresInMins: int | None = None


class RefreshResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    accessToken: str
    refreshToken: str


class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    description: str | None = None
    price: float | None = None
    brand: str | None = None


class DummyJsonBearerSession:
    """Session that attaches a bearer access token to outbound requests.

    DummyJSON expects ``Authorization: Bearer <accessToken>`` for endpoints such as
    ``GET /auth/me``. Password login must **not** send a stale bearer token, so
    ``POST /auth/login`` is excluded from injection.

    Use :meth:`bind_login` after a successful login and :meth:`apply_refresh` after
    ``POST /auth/refresh`` so subsequent calls use the latest tokens.
    """

    #: Path prefixes that must not receive ``Authorization`` (password login).
    _no_bearer_paths: frozenset[str] = frozenset({"auth/login"})

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    def bind_login(self, login: LoginResponse) -> None:
        """Store tokens from ``POST /auth/login``."""
        self._access_token = login.accessToken
        self._refresh_token = login.refreshToken

    def apply_refresh(self, tokens: RefreshResponse) -> None:
        """Replace tokens after ``POST /auth/refresh``."""
        self._access_token = tokens.accessToken
        self._refresh_token = tokens.refreshToken

    def clear(self) -> None:
        """Drop tokens (e.g. logout)."""
        self._access_token = None
        self._refresh_token = None

    def wrap_request(self, request: HttpRequest) -> HttpRequest:
        path = _url_resource_path(request.url)
        if self._access_token is None or path in self._no_bearer_paths:
            return request
        headers = {**request.headers, "authorization": f"Bearer {self._access_token}"}
        return HttpRequest(
            method=request.method,
            url=request.url,
            headers=headers,
            data=request.data,
        )

    def unwrap_response(self, response: HttpResponse) -> HttpResponse:
        """Hook for logging, retry, or error mapping; pass-through here."""
        return response


class PydanticJsonCodec:
    """JSON codec using Pydantic ``model_dump_json`` / ``model_validate_json``."""

    content_type = "application/json"

    def encode(self, obj: object) -> bytes:
        if obj is None:
            return b""
        if isinstance(obj, BaseModel):
            return obj.model_dump_json(exclude_none=True, by_alias=True).encode("utf-8")
        raise TypeError(
            f"PydanticJsonCodec.encode expects None or BaseModel, got {type(obj).__name__}"
        )

    def decode(self, data: bytes, target: type):
        if not isinstance(target, type) or not issubclass(target, BaseModel):
            raise TypeError(
                f"PydanticJsonCodec.decode expects a BaseModel subclass, got {target!r}"
            )
        return target.model_validate_json(data)


# Paths must not start with "/" if ``base_url`` ends with "/" (see HttpClient URL rules).
AUTH_LOGIN = Endpoint("POST", "auth/login", LoginRequest, LoginResponse)
AUTH_ME = Endpoint("GET", "auth/me", type(None), MeResponse)
AUTH_REFRESH = Endpoint("POST", "auth/refresh", RefreshRequest, RefreshResponse)
PRODUCT_BY_ID = Endpoint("GET", "products/1", type(None), Product)


def main() -> None:
    base_url = "https://dummyjson.com/"
    session = DummyJsonBearerSession()
    codec = PydanticJsonCodec()
    client = HttpClient(
        base_url=base_url,
        transport=RequestsTransport(),
        session=session,
        presentation_codec=codec,
    )

    # Public data: no bearer required (session has no token yet).
    product = client.send(PRODUCT_BY_ID, None)
    print("1) GET /products/1 (no session token) ->", product.title)

    # Login: session skips Authorization on auth/login (see wrap_request).
    logged_in = client.send(
        AUTH_LOGIN,
        LoginRequest(username="emilys", password="emilyspass"),
    )
    session.bind_login(logged_in)
    print("2) POST /auth/login -> tokens stored on session")

    # Authenticated route: HttpClient builds the request; session adds Bearer.
    me = client.send(AUTH_ME, None)
    print(
        "3) GET /auth/me (Bearer from session) ->",
        me.firstName,
        me.lastName,
        f"<{me.email}>",
    )

    # Refresh: body carries refreshToken; session still adds current access Bearer.
    refreshed = client.send(
        AUTH_REFRESH,
        RefreshRequest(refreshToken=session.refresh_token or ""),
    )
    session.apply_refresh(refreshed)
    print("4) POST /auth/refresh -> session updated with new access + refresh tokens")

    me_again = client.send(AUTH_ME, None)
    print(
        "5) GET /auth/me again (new bearer) -> still",
        me_again.username,
    )

    session.clear()
    print(
        "6) session.clear() - without new login, /auth/me would return 401 "
        "and decoding would fail unless you handle errors."
    )


if __name__ == "__main__":
    main()
