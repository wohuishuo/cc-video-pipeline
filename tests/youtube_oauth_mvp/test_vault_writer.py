import json
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "youtube-oauth-bootstrap"
sys.path.insert(0, str(APP))

from youtube_oauth.vault_writer import ProcessResult, VaultWriter


def test_vault_writer_injects_secret_only_in_child_environment(tmp_path):
    seen = {}
    def runner(argv, env):
        seen["argv"] = list(argv); seen["secret"] = env.get("YOUTUBE_OAUTH_CREDENTIAL")
        return ProcessResult(0, json.dumps({"resultClass": "COMPLETED", "value": {"credentialId": "youtube-main", "provider": "youtube"}}), "")
    secret = '{"clientId":"client","clientSecret":"secret","refreshToken":"refresh"}'

    result = VaultWriter(tmp_path / "vault.ps1", runner=runner).store(tmp_path / "vault.json", "youtube-main", "Main YouTube", secret)

    assert result.completed
    assert seen["secret"] == secret
    assert secret not in " ".join(seen["argv"])
    assert secret not in json.dumps(result.value)


def test_vault_writer_uses_rotate_when_credential_already_exists(tmp_path):
    calls = []
    def runner(argv, env):
        calls.append(list(argv))
        if "describe" in argv:
            return ProcessResult(0, '{"resultClass":"COMPLETED","value":{"credentialId":"youtube-main","provider":"youtube","status":"ACTIVE"}}', "")
        return ProcessResult(0, '{"resultClass":"COMPLETED","value":{"credentialId":"youtube-main","provider":"youtube","status":"ACTIVE"}}', "")

    result = VaultWriter(tmp_path / "vault.ps1", runner=runner).store(tmp_path / "vault.json", "youtube-main", "Main", '{"refreshToken":"secret"}')

    assert result.completed
    assert "rotate" in calls[1]
    assert "put" not in calls[1]


def test_vault_writer_bounds_child_launch_failure_without_secret(tmp_path):
    secret = '{"refreshToken":"must-not-leak"}'
    def runner(argv, env): raise OSError(f"launch failed with {env.get('YOUTUBE_OAUTH_CREDENTIAL')}")

    result = VaultWriter(tmp_path / "vault.ps1", runner=runner).store(tmp_path / "vault.json", "youtube-main", "Main", secret)

    assert not result.completed
    assert secret not in (result.error or "")
