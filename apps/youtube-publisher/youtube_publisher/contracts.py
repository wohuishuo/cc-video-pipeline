"""Validated, redacted input contracts for private YouTube publication."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


class CredentialError(ValueError):
    pass


class MetadataError(ValueError):
    pass


@dataclass(frozen=True, repr=False)
class YouTubeCredential:
    access_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None

    @classmethod
    def parse(cls, raw: str) -> "YouTubeCredential":
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise CredentialError("credential must be a JSON object") from error
        if not isinstance(value, dict):
            raise CredentialError("credential must be a JSON object")

        def optional(name: str) -> str | None:
            item = value.get(name)
            if item is None:
                return None
            if not isinstance(item, str) or not item.strip():
                raise CredentialError(f"credential field {name} must be a non-empty string")
            return item.strip()

        credential = cls(
            access_token=optional("accessToken"),
            client_id=optional("clientId"),
            client_secret=optional("clientSecret"),
            refresh_token=optional("refreshToken"),
        )
        refresh_values = (credential.client_id, credential.client_secret, credential.refresh_token)
        if any(refresh_values) and not all(refresh_values):
            raise CredentialError("refresh credential requires clientId, clientSecret and refreshToken")
        if not credential.access_token and not all(refresh_values):
            raise CredentialError("credential requires accessToken or a complete refresh credential")
        return credential

    @property
    def refreshable(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def __repr__(self) -> str:
        return "YouTubeCredential(<redacted>)"


def load_metadata(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise MetadataError("metadata must be a readable JSON object") from error
    if not isinstance(value, dict):
        raise MetadataError("metadata must be a JSON object")
    title = value.get("title")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 100:
        raise MetadataError("metadata.title must contain 1 to 100 characters")
    description = value.get("description", "")
    if not isinstance(description, str) or len(description) > 5000:
        raise MetadataError("metadata.description must be a string of at most 5000 characters")
    raw_tags = value.get("tags", [])
    if not isinstance(raw_tags, list) or not all(isinstance(tag, str) for tag in raw_tags):
        raise MetadataError("metadata.tags must be a string array")
    tags = [tag.strip().lstrip("#") for tag in raw_tags if tag.strip().lstrip("#")]
    category_id = str(value.get("categoryId", "22"))
    if not re.fullmatch(r"[0-9]{1,3}", category_id):
        raise MetadataError("metadata.categoryId must be numeric")
    snippet: dict[str, Any] = {
        "title": title.strip(),
        "description": description,
        "tags": tags,
        "categoryId": category_id,
    }
    status: dict[str, Any] = {"privacyStatus": "private"}
    if "selfDeclaredMadeForKids" in value:
        if not isinstance(value["selfDeclaredMadeForKids"], bool):
            raise MetadataError("metadata.selfDeclaredMadeForKids must be boolean")
        status["selfDeclaredMadeForKids"] = value["selfDeclaredMadeForKids"]
    if "containsSyntheticMedia" in value:
        if not isinstance(value["containsSyntheticMedia"], bool):
            raise MetadataError("metadata.containsSyntheticMedia must be boolean")
        status["containsSyntheticMedia"] = value["containsSyntheticMedia"]
    return {"snippet": snippet, "status": status}
