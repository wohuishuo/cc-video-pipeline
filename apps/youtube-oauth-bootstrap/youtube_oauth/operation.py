"""One redacted desktop consent operation composed with Credential Vault."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4
import webbrowser

from .callback import LoopbackReceiver
from .contracts import ClientConfigError, OAuthClientConfig
from .flow import OAuthError, OAuthFlow
from .vault_writer import VaultWriter


@dataclass(frozen=True)
class OAuthBootstrapResult:
    result_class: str
    receipt_path: Path
    value: dict[str, Any]
    error: str | None = None


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, path)


class OAuthBootstrapOperation:
    def __init__(self, *, flow=None, receiver_factory=LoopbackReceiver, vault_writer=None, browser_opener: Callable[[str], Any] = webbrowser.open):
        self.flow = flow or OAuthFlow(); self.receiver_factory = receiver_factory; self.vault_writer = vault_writer; self.browser_opener = browser_opener

    def execute(self, client_config_path: Path, vault_path: Path, credential_id: str, label: str, output_dir: Path, operation_id: str, *, timeout: float = 300, on_event: Callable[[dict[str, Any]], None] | None = None) -> OAuthBootstrapResult:
        receipt = Path(output_dir).resolve() / "youtube-oauth-receipt.json"; event = on_event or (lambda _: None)
        if not operation_id.strip() or not credential_id.strip() or not label.strip() or timeout <= 0 or timeout > 900:
            return OAuthBootstrapResult("REJECTED_MALFORMED", receipt, {}, "operation, credential, label and bounded timeout are required")
        try:
            config = OAuthClientConfig.load(client_config_path)
        except ClientConfigError as error:
            return OAuthBootstrapResult("REJECTED_MALFORMED", receipt, {}, str(error))
        try:
            receiver = self.receiver_factory()
        except OSError:
            return OAuthBootstrapResult("FAILED", receipt, {}, "loopback callback could not be started")
        try:
            attempt = self.flow.begin(config, receiver.port)
            event({"event": "authorization", "url": attempt.authorization_url})
            try:
                self.browser_opener(attempt.authorization_url)
            except OSError:
                event({"event": "browser", "status": "open-failed", "detail": "Open the authorization URL from the previous event."})
            code = receiver.receive(attempt, timeout)
            credential = self.flow.exchange(config, attempt, code)
            secret_json = json.dumps({"clientId": config.client_id, "clientSecret": config.client_secret, "refreshToken": credential.refresh_token}, separators=(",", ":"))
            writer = self.vault_writer
            if writer is None:
                raise OAuthError("Credential Vault writer is not configured")
            stored = writer.store(vault_path, credential_id, label, secret_json)
            secret_json = ""
            if not stored.completed:
                raise OAuthError(stored.error or "Credential Vault rejected storage")
            value = {"credentialId": credential_id, "provider": "youtube", "status": stored.value.get("status", "ACTIVE"), "scope": credential.scope}
            _atomic(receipt, {"schemaVersion": 1, "operationId": operation_id, "resultClass": "COMPLETED", **value})
            return OAuthBootstrapResult("COMPLETED", receipt, value)
        except OAuthError as error:
            return OAuthBootstrapResult("FAILED", receipt, {}, str(error))
        finally:
            receiver.close()
