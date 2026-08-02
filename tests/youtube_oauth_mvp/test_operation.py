import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "youtube-oauth-bootstrap"
sys.path.insert(0, str(APP))

from youtube_oauth.contracts import OAuthClientConfig
from youtube_oauth.flow import OAuthAttempt, OAuthCredential
from youtube_oauth.operation import OAuthBootstrapOperation
from youtube_oauth.vault_writer import VaultWriteResult


class Flow:
    def begin(self, config, port): return OAuthAttempt("https://accounts.google.com/authorize?safe=1", "state-secret", "verifier-secret", f"http://127.0.0.1:{port}/oauth/callback")
    def exchange(self, config, attempt, code): return OAuthCredential("access-secret", "refresh-secret", "https://www.googleapis.com/auth/youtube.upload")


class Receiver:
    port = 49156
    def receive(self, attempt, timeout): return "authorization-secret"
    def close(self): pass


class Vault:
    def __init__(self): self.secret = None
    def store(self, path, credential_id, label, secret): self.secret = secret; return VaultWriteResult(True, {"credentialId": credential_id, "provider": "youtube", "status": "ACTIVE"})


def test_operation_opens_browser_stores_vault_and_commits_only_redacted_receipt(tmp_path):
    config_path = tmp_path / "client.json"; config_path.write_text(json.dumps({"installed": {"client_id": "client", "client_secret": "client-secret"}}), encoding="utf-8")
    vault_path = tmp_path / "vault.json"; output = tmp_path / "out"; opened = []; vault = Vault()
    operation = OAuthBootstrapOperation(flow=Flow(), receiver_factory=lambda: Receiver(), vault_writer=vault, browser_opener=opened.append)

    result = operation.execute(config_path, vault_path, "youtube-main", "Main", output, "operation-1", timeout=10, on_event=lambda event: None)
    receipt = result.receipt_path.read_text(encoding="utf-8")

    assert result.result_class == "COMPLETED"
    assert opened == ["https://accounts.google.com/authorize?safe=1"]
    assert "refresh-secret" in vault.secret
    assert all(secret not in receipt for secret in ("client-secret", "refresh-secret", "access-secret", "authorization-secret", "state-secret", "verifier-secret"))
    assert json.loads(receipt)["credentialId"] == "youtube-main"


def test_browser_launch_failure_keeps_safe_url_event_and_continues(tmp_path):
    config_path = tmp_path / "client.json"; config_path.write_text(json.dumps({"installed": {"client_id": "client", "client_secret": "client-secret"}}), encoding="utf-8")
    events = []; vault = Vault()
    def unavailable(url): raise OSError("browser unavailable")
    operation = OAuthBootstrapOperation(flow=Flow(), receiver_factory=lambda: Receiver(), vault_writer=vault, browser_opener=unavailable)

    result = operation.execute(config_path, tmp_path / "vault.json", "youtube-main", "Main", tmp_path / "out", "operation-2", timeout=10, on_event=events.append)

    assert result.result_class == "COMPLETED"
    assert events[0]["event"] == "authorization"
    assert events[1] == {"event": "browser", "status": "open-failed", "detail": "Open the authorization URL from the previous event."}
