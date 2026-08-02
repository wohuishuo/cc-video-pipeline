"""Strict redacted contracts for Google desktop OAuth client configuration."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from urllib.parse import urlsplit


class ClientConfigError(ValueError):
    pass


@dataclass(frozen=True, repr=False)
class OAuthClientConfig:
    client_id: str
    client_secret: str

    @classmethod
    def load(cls, path: Path) -> "OAuthClientConfig":
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            raise ClientConfigError("OAuth client config must be readable JSON") from error
        installed = value.get("installed") if isinstance(value, dict) else None
        if not isinstance(installed, dict):
            raise ClientConfigError("OAuth client config must use the desktop installed application type")
        client_id = installed.get("client_id"); client_secret = installed.get("client_secret")
        if not isinstance(client_id, str) or not client_id.strip() or not isinstance(client_secret, str) or not client_secret.strip():
            raise ClientConfigError("desktop OAuth client ID and secret are required")
        auth_uri = installed.get("auth_uri")
        token_uri = installed.get("token_uri")
        if auth_uri is not None and not cls._trusted(auth_uri, "accounts.google.com"):
            raise ClientConfigError("OAuth authorization endpoint is not trusted")
        if token_uri is not None and not cls._trusted(token_uri, "oauth2.googleapis.com"):
            raise ClientConfigError("OAuth token endpoint is not trusted")
        return cls(client_id.strip(), client_secret.strip())

    @staticmethod
    def _trusted(value: object, host: str) -> bool:
        if not isinstance(value, str):
            return False
        parsed = urlsplit(value)
        return parsed.scheme == "https" and parsed.hostname == host

    def __repr__(self) -> str:
        return "OAuthClientConfig(<redacted>)"
