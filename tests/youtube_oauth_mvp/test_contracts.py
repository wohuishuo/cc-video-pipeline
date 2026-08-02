import json
from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "youtube-oauth-bootstrap"
sys.path.insert(0, str(APP))

from youtube_oauth.contracts import ClientConfigError, OAuthClientConfig


def test_desktop_client_config_is_parsed_and_redacted(tmp_path):
    path = tmp_path / "client.json"
    path.write_text(json.dumps({"installed": {"client_id": "desktop-client", "client_secret": "never-show", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": ["http://localhost"]}}), encoding="utf-8")

    config = OAuthClientConfig.load(path)

    assert config.client_id == "desktop-client"
    assert "never-show" not in repr(config)


def test_web_client_or_untrusted_endpoint_is_rejected_without_secret_echo(tmp_path):
    path = tmp_path / "client.json"
    path.write_text(json.dumps({"web": {"client_id": "web", "client_secret": "never-show", "token_uri": "https://attacker.example/token"}}), encoding="utf-8")

    with pytest.raises(ClientConfigError) as failure:
        OAuthClientConfig.load(path)

    assert "never-show" not in str(failure.value)
