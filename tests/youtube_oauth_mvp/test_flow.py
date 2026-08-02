import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "youtube-oauth-bootstrap"
sys.path.insert(0, str(APP))

from youtube_oauth.contracts import OAuthClientConfig
from youtube_oauth.flow import HttpResponse, OAuthError, OAuthFlow, YOUTUBE_UPLOAD_SCOPE


class Transport:
    def __init__(self, response): self.response = response; self.calls = []
    def post_form(self, url, fields): self.calls.append((url, dict(fields))); return self.response


def config():
    return OAuthClientConfig("desktop-client", "client-secret")


def test_authorization_uses_loopback_state_pkce_and_minimum_scope():
    flow = OAuthFlow(Transport(HttpResponse(500, b"")), random_token=lambda size: "v" * size)

    attempt = flow.begin(config(), 49152)
    query = parse_qs(urlsplit(attempt.authorization_url).query)

    assert attempt.redirect_uri == "http://127.0.0.1:49152/oauth/callback"
    assert query["scope"] == [YOUTUBE_UPLOAD_SCOPE]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert query["state"] == [attempt.state]
    assert query["code_challenge_method"] == ["S256"]
    assert "client-secret" not in attempt.authorization_url


def test_callback_requires_exact_path_state_and_one_code():
    flow = OAuthFlow(Transport(HttpResponse(500, b"")), random_token=lambda size: "x" * size)
    attempt = flow.begin(config(), 49153)

    assert flow.accept_callback(attempt, f"/oauth/callback?state={attempt.state}&code=one") == "one"
    with pytest.raises(OAuthError, match="state"):
        flow.accept_callback(attempt, "/oauth/callback?state=wrong&code=one")
    with pytest.raises(OAuthError, match="path"):
        flow.accept_callback(attempt, f"/wrong?state={attempt.state}&code=one")


def test_token_exchange_requires_refresh_token_and_exact_upload_scope():
    response = HttpResponse(200, json.dumps({"access_token": "short", "refresh_token": "long", "scope": YOUTUBE_UPLOAD_SCOPE, "token_type": "Bearer"}).encode())
    transport = Transport(response); flow = OAuthFlow(transport, random_token=lambda size: "z" * size); attempt = flow.begin(config(), 49154)

    credential = flow.exchange(config(), attempt, "authorization-code")

    assert credential.refresh_token == "long"
    sent = transport.calls[0][1]
    assert sent["code_verifier"] == attempt.verifier
    assert sent["redirect_uri"] == attempt.redirect_uri
    assert "long" not in repr(credential)


@pytest.mark.parametrize("payload", [
    {"access_token": "short", "scope": YOUTUBE_UPLOAD_SCOPE},
    {"access_token": "short", "refresh_token": "long", "scope": "https://www.googleapis.com/auth/youtube.readonly"},
])
def test_incomplete_or_wrong_scope_exchange_is_rejected(payload):
    flow = OAuthFlow(Transport(HttpResponse(200, json.dumps(payload).encode())), random_token=lambda size: "q" * size); attempt = flow.begin(config(), 49155)

    with pytest.raises(OAuthError):
        flow.exchange(config(), attempt, "code")
