import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "credential-vault"
sys.path.insert(0, str(APP))

from credential_vault.vault import CredentialVault, VaultError


NOW = datetime(2026, 8, 2, tzinfo=timezone.utc)


class FakeCipher:
    def protect(self, plaintext: bytes, context: bytes) -> bytes:
        return b"protected:" + context + b":" + plaintext[::-1]

    def unprotect(self, ciphertext: bytes, context: bytes) -> bytes:
        prefix = b"protected:" + context + b":"
        if not ciphertext.startswith(prefix):
            raise VaultError("REJECTED_CIPHERTEXT", "ciphertext context mismatch")
        return ciphertext[len(prefix) :][::-1]


def test_put_replays_exact_input_and_requires_explicit_rotation(tmp_path):
    path = tmp_path / "vault.json"
    vault = CredentialVault(path, cipher=FakeCipher(), clock=lambda: NOW)

    first = vault.put("youtube-main", "youtube", "Main channel", "secret-one")
    replay = vault.put("youtube-main", "youtube", "Main channel", "secret-one")
    conflict = vault.put("youtube-main", "youtube", "Main channel", "secret-two")

    assert first.result_class == "COMPLETED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert conflict.result_class == "REJECTED_CONFLICT"
    persisted = path.read_text(encoding="utf-8")
    assert "secret-one" not in persisted
    assert "secret-two" not in persisted
    assert "protected:" not in persisted
    assert json.loads(persisted)["records"][0]["ciphertext"] == base64.b64encode(
        FakeCipher().protect(b"secret-one", b"credential-vault:v1:youtube-main")
    ).decode("ascii")


def test_describe_is_redacted_and_rotation_changes_secret(tmp_path):
    vault = CredentialVault(tmp_path / "vault.json", cipher=FakeCipher(), clock=lambda: NOW)
    vault.put("douyin-main", "douyin", "Creator account", "old-secret")

    before = vault.describe("douyin-main")
    rotated = vault.rotate("douyin-main", "new-secret")
    secret = vault.resolve_secret("douyin-main")

    assert before.value == {
        "credentialId": "douyin-main",
        "provider": "douyin",
        "label": "Creator account",
        "status": "ACTIVE",
        "createdAt": "2026-08-02T00:00:00+00:00",
        "updatedAt": "2026-08-02T00:00:00+00:00",
        "revokedAt": None,
    }
    assert rotated.result_class == "COMPLETED"
    assert secret == "new-secret"
    assert "new-secret" not in str(rotated.value)


def test_list_records_returns_only_redacted_account_metadata(tmp_path):
    path = tmp_path / "vault.json"
    vault = CredentialVault(path, cipher=FakeCipher(), clock=lambda: NOW)
    vault.put("youtube-main", "youtube", "Main channel", "youtube-secret")
    vault.put("deepseek-api", "deepseek", "Translation", "deepseek-secret")

    result = vault.list_records()

    assert result.result_class == "COMPLETED"
    assert [row["credentialId"] for row in result.value["records"]] == ["deepseek-api", "youtube-main"]
    serialized = json.dumps(result.value)
    assert "ciphertext" not in serialized
    assert "youtube-secret" not in serialized
    assert "deepseek-secret" not in serialized


def test_revoke_destroys_ciphertext_and_blocks_resolution(tmp_path):
    path = tmp_path / "vault.json"
    vault = CredentialVault(path, cipher=FakeCipher(), clock=lambda: NOW)
    vault.put("tiktok-main", "tiktok", "TikTok", "secret")

    revoked = vault.revoke("tiktok-main")

    record = json.loads(path.read_text(encoding="utf-8"))["records"][0]
    assert revoked.result_class == "COMPLETED"
    assert record["ciphertext"] is None
    assert record["status"] == "REVOKED"
    try:
        vault.resolve_secret("tiktok-main")
    except VaultError as error:
        assert error.code == "REJECTED_REVOKED"
    else:
        raise AssertionError("revoked credential resolved")


def test_registry_commit_is_atomic_and_identifiers_are_bounded(tmp_path):
    path = tmp_path / "vault.json"
    vault = CredentialVault(path, cipher=FakeCipher(), clock=lambda: NOW)
    vault.put("youtube-main", "youtube", "Main", "secret")

    assert list(tmp_path.glob(".vault.json.*.tmp")) == []
    for unsafe in ("UPPER", "../escape", "x" * 64):
        try:
            vault.put(unsafe, "youtube", "Main", "secret")
        except VaultError as error:
            assert error.code == "REJECTED_MALFORMED"
        else:
            raise AssertionError(f"unsafe credential ID accepted: {unsafe}")


def test_ciphertext_cannot_be_moved_between_record_contexts(tmp_path):
    path = tmp_path / "vault.json"
    vault = CredentialVault(path, cipher=FakeCipher(), clock=lambda: NOW)
    vault.put("one", "youtube", "One", "secret-one")
    vault.put("two", "youtube", "Two", "secret-two")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["records"][1]["ciphertext"] = data["records"][0]["ciphertext"]
    path.write_text(json.dumps(data), encoding="utf-8")

    try:
        vault.resolve_secret("two")
    except VaultError as error:
        assert error.code == "REJECTED_CIPHERTEXT"
    else:
        raise AssertionError("moved ciphertext resolved under another record")


def test_resolution_rejects_provider_mismatch_before_releasing_secret(tmp_path):
    vault = CredentialVault(tmp_path / "vault.json", cipher=FakeCipher(), clock=lambda: NOW)
    vault.put("youtube-main", "youtube", "Main", "secret")

    try:
        vault.resolve_secret("youtube-main", expected_provider="douyin")
    except VaultError as error:
        assert error.code == "REJECTED_PROVIDER"
    else:
        raise AssertionError("credential released to the wrong provider")
