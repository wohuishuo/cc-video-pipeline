import json
from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "youtube-publisher"
sys.path.insert(0, str(APP))

from youtube_publisher.contracts import CredentialError, YouTubeCredential, load_metadata


def test_refresh_credential_is_complete_and_redacted():
    raw = json.dumps({"clientId": "client", "clientSecret": "secret", "refreshToken": "refresh"})

    credential = YouTubeCredential.parse(raw)

    assert credential.refreshable
    assert "secret" not in repr(credential)
    assert "refresh" not in repr(credential)


def test_partial_refresh_credential_is_rejected_without_echoing_secret():
    raw = json.dumps({"clientId": "client", "clientSecret": "do-not-echo"})

    with pytest.raises(CredentialError) as failure:
        YouTubeCredential.parse(raw)

    assert "do-not-echo" not in str(failure.value)


def test_metadata_is_normalized_for_private_upload(tmp_path):
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps({"title": " Demo ", "description": "Text", "tags": ["one", "#two"], "categoryId": 22}), encoding="utf-8")

    metadata = load_metadata(path)

    assert metadata == {"snippet": {"title": "Demo", "description": "Text", "tags": ["one", "two"], "categoryId": "22"}, "status": {"privacyStatus": "private"}}
