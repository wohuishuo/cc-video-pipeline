"""State/PKCE authorization and token exchange for one desktop consent."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import secrets
from typing import Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from .contracts import OAuthClientConfig


AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


class OAuthError(RuntimeError):
    pass


@dataclass(frozen=True, repr=False)
class OAuthAttempt:
    authorization_url: str
    state: str
    verifier: str
    redirect_uri: str

    def __repr__(self) -> str:
        return "OAuthAttempt(<ephemeral>)"


@dataclass(frozen=True, repr=False)
class OAuthCredential:
    access_token: str
    refresh_token: str
    scope: str

    def __repr__(self) -> str:
        return "OAuthCredential(<redacted>)"


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes


class StdlibTokenTransport:
    def post_form(self, url: str, fields: Mapping[str, str]) -> HttpResponse:
        request = Request(url, data=urlencode(fields).encode("ascii"), headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        try:
            with urlopen(request, timeout=60) as response:
                return HttpResponse(response.status, response.read())
        except HTTPError as error:
            return HttpResponse(error.code, error.read())


class OAuthFlow:
    def __init__(self, transport=None, *, random_token: Callable[[int], str] = secrets.token_urlsafe):
        self.transport = transport or StdlibTokenTransport()
        self.random_token = random_token

    def begin(self, config: OAuthClientConfig, port: int) -> OAuthAttempt:
        if not (1024 <= int(port) <= 65535):
            raise OAuthError("loopback port is invalid")
        state = self.random_token(32)
        verifier = self.random_token(64)
        if len(state) < 32 or not (43 <= len(verifier) <= 128):
            raise OAuthError("secure OAuth state generation failed")
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
        redirect_uri = f"http://127.0.0.1:{port}/oauth/callback"
        query = urlencode({
            "client_id": config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": YOUTUBE_UPLOAD_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        return OAuthAttempt(f"{AUTHORIZATION_ENDPOINT}?{query}", state, verifier, redirect_uri)

    @staticmethod
    def accept_callback(attempt: OAuthAttempt, target: str) -> str:
        parsed = urlsplit(target)
        if parsed.path != "/oauth/callback":
            raise OAuthError("OAuth callback path does not match")
        query = parse_qs(parsed.query, keep_blank_values=True)
        if query.get("state") != [attempt.state]:
            raise OAuthError("OAuth callback state does not match")
        if query.get("error"):
            raise OAuthError("YouTube authorization was denied")
        codes = query.get("code", [])
        if len(codes) != 1 or not codes[0]:
            raise OAuthError("OAuth callback must contain one authorization code")
        return codes[0]

    def exchange(self, config: OAuthClientConfig, attempt: OAuthAttempt, code: str) -> OAuthCredential:
        try:
            response = self.transport.post_form(TOKEN_ENDPOINT, {
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "code": code,
                "code_verifier": attempt.verifier,
                "grant_type": "authorization_code",
                "redirect_uri": attempt.redirect_uri,
            })
        except OSError as error:
            raise OAuthError("Google token exchange could not be reached") from error
        if response.status != 200:
            raise OAuthError("Google rejected the authorization-code exchange")
        try:
            value = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise OAuthError("Google token response was invalid") from error
        if not isinstance(value, dict):
            raise OAuthError("Google token response was invalid")
        access_token = value.get("access_token"); refresh_token = value.get("refresh_token"); scope = value.get("scope")
        granted = set(scope.split()) if isinstance(scope, str) else set()
        if not isinstance(access_token, str) or not access_token or not isinstance(refresh_token, str) or not refresh_token:
            raise OAuthError("Google token response omitted access or refresh credentials")
        if granted != {YOUTUBE_UPLOAD_SCOPE}:
            raise OAuthError("Google did not grant the exact YouTube upload scope")
        return OAuthCredential(access_token, refresh_token, YOUTUBE_UPLOAD_SCOPE)
