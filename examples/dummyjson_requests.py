"""
Example: wrapfast HttpClient + DummyJSON (https://dummyjson.com) using `requests`,
Pydantic models, and a **Session** that injects ``Authorization: Bearer …`` after login.

Install from the repo root::

    pip install requests pydantic
    # or: uv venv && uv sync --extra examples

Run::

    python examples/dummyjson_requests.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict

# Repo layout: package lives under src/wrapfast/ (add ``src`` so ``import wrapfast`` works without install).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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


class AuthError(Exception):
    pass


class AuthSession(Session[JsonRequest, JsonResponse]):
    def __init__(self, token: str | None = None) -> None:
        self.token = token

    def wrap(self, request: JsonRequest) -> JsonRequest:
        if self.token:
            request.headers["Authorization"] = f"Bearer {self.token}"
        return request

    def unwrap(self, response: JsonResponse) -> JsonResponse:
        if response.status == 401:
            raise AuthError("Unauthorized")
        return response


class JsonPresentation(Presentation[JsonRequest, JsonResponse]):
    def encode(self, request: JsonRequest, *, method: str, url: str) -> HttpRequest:
        headers = {"Content-Type": "application/json", **request.headers}
        data = json.dumps(request.body).encode("utf-8") if request.body else b""
        return HttpRequest(method=method, url=url, headers=headers, data=data)

    def decode(self, response: HttpResponse) -> JsonResponse:
        body = json.loads(response.data) if response.data else {}
        return JsonResponse(status=response.status_code, body=body)

    def narrow[T](self, response: JsonResponse, target: type[T]) -> T:
        if issubclass(target, BaseModel):
            return target.model_validate(response.body)
        return target(response.body)  # type: ignore


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
            data=r.content,
        )


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    username: str
    email: str
    firstName: str
    lastName: str


def main() -> None:
    # 1. We authenticate to get a token
    login_client = HttpClient[JsonRequest, JsonResponse](
        base_url="https://dummyjson.com",
        transport=RequestsTransport(),
        session=AuthSession(),  # no token yet
        presentation=JsonPresentation(),
    )

    class LoginResponse(BaseModel):
        token: str

    login_endpoint = Endpoint("POST", "/auth/login", LoginResponse)
    login_res = login_client.send(
        login_endpoint,
        JsonRequest(
            headers={},
            body={"username": "emilys", "password": "emilyspass", "expiresInMins": 60},
        ),
    )

    print(f"Logged in, token: {login_res.token[:10]}...")

    # 2. Use the token for an authenticated request
    client = HttpClient[JsonRequest, JsonResponse](
        base_url="https://dummyjson.com",
        transport=RequestsTransport(),
        session=AuthSession(login_res.token),
        presentation=JsonPresentation(),
    )

    get_me = Endpoint("GET", "/auth/me", UserResponse)
    user = client.send(get_me, JsonRequest(headers={}, body={}))
    print(f"Me: {user.firstName} {user.lastName} ({user.email})")


if __name__ == "__main__":
    main()
