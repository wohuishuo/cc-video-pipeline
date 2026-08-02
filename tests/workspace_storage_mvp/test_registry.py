from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "workspace-storage"
sys.path.insert(0, str(APP))

from workspace_storage.registry import StorageRegistry, StorageRegistryError


def test_provision_replays_and_keeps_workspace_namespaces_disjoint(tmp_path):
    registry = StorageRegistry(tmp_path / "storage.json")
    storage_root = tmp_path / "runtime"

    first = registry.provision_workspace("alpha", storage_root, quota_bytes=10_000)
    replay = registry.provision_workspace("alpha", storage_root, quota_bytes=10_000)
    second = registry.provision_workspace("beta", storage_root, quota_bytes=20_000)

    assert first.result_class == "COMPLETED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert second.result_class == "COMPLETED"
    assert first.value["roots"]["state"] != second.value["roots"]["state"]
    assert set(first.value["roots"]) == {"state", "artifacts", "temp"}
    assert all(Path(value).is_dir() for value in first.value["roots"].values())


def test_provision_rejects_changed_root_or_quota(tmp_path):
    registry = StorageRegistry(tmp_path / "storage.json")
    first_root = tmp_path / "one"
    second_root = tmp_path / "two"
    registry.provision_workspace("alpha", first_root, quota_bytes=10_000)

    assert registry.provision_workspace("alpha", first_root, quota_bytes=20_000).result_class == "REJECTED_CONFLICT"
    try:
        registry.provision_workspace("beta", second_root, quota_bytes=10_000)
    except StorageRegistryError as error:
        assert error.code == "REJECTED_CONFLICT"
    else:
        raise AssertionError("changed storage root accepted")


def test_resolve_path_confines_relative_paths_to_selected_namespace(tmp_path):
    registry = StorageRegistry(tmp_path / "storage.json")
    registry.provision_workspace("alpha", tmp_path / "runtime", quota_bytes=10_000)

    resolved = registry.resolve_path("alpha", "artifacts", "runs/one/video.mp4")
    assert resolved.result_class == "COMPLETED"
    assert Path(resolved.value["path"]).is_relative_to(
        Path(registry.describe_workspace("alpha").value["roots"]["artifacts"])
    )

    for unsafe in (
        "../escape.txt",
        "C:drive-relative.txt",
        str((tmp_path / "absolute.txt").resolve()),
    ):
        try:
            registry.resolve_path("alpha", "artifacts", unsafe)
        except StorageRegistryError as error:
            assert error.code == "REJECTED_PATH"
        else:
            raise AssertionError(f"unsafe path accepted: {unsafe}")


def test_provision_rejects_a_file_colliding_with_namespace_directory(tmp_path):
    storage_root = tmp_path / "runtime"
    artifact_root = storage_root / "workspaces" / "alpha" / "artifacts"
    artifact_root.parent.mkdir(parents=True)
    artifact_root.write_text("collision", encoding="utf-8")
    registry = StorageRegistry(tmp_path / "storage.json")

    try:
        registry.provision_workspace("alpha", storage_root, quota_bytes=10_000)
    except StorageRegistryError as error:
        assert error.code == "REJECTED_PATH"
    else:
        raise AssertionError("file collision accepted")


def test_capacity_counts_workspace_files_and_returns_bounded_decision(tmp_path):
    registry = StorageRegistry(tmp_path / "storage.json")
    provisioned = registry.provision_workspace("alpha", tmp_path / "runtime", quota_bytes=10)
    artifact = Path(provisioned.value["roots"]["artifacts"]) / "sample.bin"
    artifact.write_bytes(b"123456")

    allowed = registry.check_capacity("alpha", required_bytes=4)
    denied = registry.check_capacity("alpha", required_bytes=5)

    assert allowed.result_class == "ALLOWED"
    assert denied.result_class == "REJECTED_QUOTA"
    assert allowed.value == {
        "workspaceId": "alpha",
        "quotaBytes": 10,
        "usageBytes": 6,
        "availableBytes": 4,
        "requiredBytes": 4,
    }


def test_registry_commit_is_atomic_and_description_is_public(tmp_path):
    path = tmp_path / "storage.json"
    registry = StorageRegistry(path)
    registry.provision_workspace("alpha", tmp_path / "runtime", quota_bytes=10_000)

    described = registry.describe_workspace("alpha")

    assert described.result_class == "COMPLETED"
    assert described.value["workspaceId"] == "alpha"
    assert "credential" not in str(described.value).lower()
    assert list(tmp_path.glob(".storage.json.*.tmp")) == []
