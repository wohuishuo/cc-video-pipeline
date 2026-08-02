from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "workspace-access"
sys.path.insert(0, str(APP))

from workspace_access.registry import AccessRegistry, RegistryError


NOW = datetime(2026, 8, 2, 7, 0, tzinfo=timezone.utc)


def test_workspace_init_replays_same_contract_and_rejects_changed_identity(tmp_path):
    registry = AccessRegistry(tmp_path / "access.json", clock=lambda: NOW)
    root = tmp_path / "media"
    root.mkdir()
    second_root = tmp_path / "exports"
    second_root.mkdir()

    first = registry.initialize_workspace("local", "Local Studio", [root, second_root])
    replay = registry.initialize_workspace("local", "Local Studio", [second_root, root])
    conflict = registry.initialize_workspace("local", "Changed", [root])

    assert first.result_class == "COMPLETED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert conflict.result_class == "REJECTED_CONFLICT"
    assert first.value["allowedRoots"] == sorted(
        [str(root.resolve()), str(second_root.resolve())], key=str.casefold
    )


def test_issue_authorize_and_revoke_never_persist_plaintext_token(tmp_path):
    path = tmp_path / "access.json"
    registry = AccessRegistry(path, clock=lambda: NOW)
    root = tmp_path / "media"
    root.mkdir()
    registry.initialize_workspace("local", "Local Studio", [root])

    issued = registry.issue_token(
        "local", "desktop", ["runs:read", "runs:write"], ttl=timedelta(hours=4)
    )
    token = issued.value["token"]
    token_id = issued.value["tokenId"]
    persisted = path.read_text(encoding="utf-8")

    assert issued.result_class == "COMPLETED"
    assert token.startswith(f"vgst_{token_id}_")
    assert token not in persisted
    assert "tokenSha256" in persisted
    authorized = registry.authorize(token, "local", "runs:write")
    denied_scope = registry.authorize(token, "local", "publication:execute")
    assert authorized.result_class == "AUTHORIZED"
    assert "token" not in json.dumps(authorized.value).lower()
    assert denied_scope.result_class == "REJECTED_UNAUTHORIZED"

    revoked = registry.revoke_token("local", token_id)
    assert revoked.result_class == "COMPLETED"
    assert registry.authorize(token, "local", "runs:read").result_class == "REJECTED_UNAUTHORIZED"
    assert registry.revoke_token("local", token_id).result_class == "DUPLICATE_COMPLETED"


def test_expired_wrong_workspace_and_malformed_tokens_are_rejected(tmp_path):
    current = [NOW]
    registry = AccessRegistry(tmp_path / "access.json", clock=lambda: current[0])
    root = tmp_path / "media"
    root.mkdir()
    registry.initialize_workspace("one", "One", [root])
    registry.initialize_workspace("two", "Two", [root])
    issued = registry.issue_token("one", "short", ["runs:read"], ttl=timedelta(minutes=5))
    token = issued.value["token"]

    assert registry.authorize("not-a-token", "one", "runs:read").result_class == "REJECTED_UNAUTHORIZED"
    assert registry.authorize(token, "two", "runs:read").result_class == "REJECTED_UNAUTHORIZED"
    current[0] = NOW + timedelta(minutes=6)
    assert registry.authorize(token, "one", "runs:read").result_class == "REJECTED_UNAUTHORIZED"


def test_registry_rejects_unknown_scope_and_unsafe_identifiers(tmp_path):
    registry = AccessRegistry(tmp_path / "access.json", clock=lambda: NOW)
    root = tmp_path / "media"
    root.mkdir()
    registry.initialize_workspace("local", "Local", [root])

    try:
        registry.issue_token("local", "bad", ["everything"], ttl=timedelta(hours=1))
    except RegistryError as error:
        assert error.code == "REJECTED_MALFORMED"
    else:
        raise AssertionError("unknown scope accepted")

    try:
        registry.initialize_workspace("../escape", "Bad", [root])
    except RegistryError as error:
        assert error.code == "REJECTED_MALFORMED"
    else:
        raise AssertionError("unsafe workspace ID accepted")


def test_describe_workspace_returns_roots_without_credential_metadata(tmp_path):
    registry = AccessRegistry(tmp_path / "access.json", clock=lambda: NOW)
    root = tmp_path / "media"
    root.mkdir()
    registry.initialize_workspace("local", "Local", [root])
    registry.issue_token("local", "browser", ["runs:read"], ttl=timedelta(hours=1))

    described = registry.describe_workspace("local")

    assert described.result_class == "COMPLETED"
    assert described.value == {
        "workspaceId": "local",
        "displayName": "Local",
        "allowedRoots": [str(root.resolve())],
    }
    assert "credential" not in json.dumps(described.value).lower()
