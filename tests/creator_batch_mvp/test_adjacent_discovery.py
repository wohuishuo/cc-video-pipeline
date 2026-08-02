import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "creator-batch"))
sys.path.insert(0, str(ROOT / "apps" / "creator-discovery"))

from creator_batch.contracts import BatchPolicy, CreatorSource
from creator_batch.operation import BatchOperation, ItemProcessResult
from creator_discovery.contracts import CreatorItem, DiscoveryPage, ProfileSpec
from creator_discovery.operation import DiscoveryOperation


class Enumerator:
    identity = "adjacent-enumerator@1"

    def enumerate(self, spec, cookies, cursor, on_log):
        yield DiscoveryPage(
            "creator-1",
            "Creator",
            (
                CreatorItem("video-1", "https://www.douyin.com/video/1", "One"),
                CreatorItem("video-2", "https://www.douyin.com/video/2", "Two"),
            ),
            None,
            False,
        )


class Processor:
    def process(self, item, item_root, child_prefix, policy, cookies, on_log):
        manifest = Path(item_root) / "localization-manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"schemaVersion": 1, "itemId": item.id}), encoding="utf-8")
        return ItemProcessResult(True, manifest, 1)


def test_real_discovery_manifest_drives_real_batch_continuation_owner(tmp_path):
    discovery = DiscoveryOperation().execute(
        ProfileSpec.from_url("https://www.douyin.com/user/creator", max_items=2),
        tmp_path / "discovery",
        "discover-1",
        enumerator=Enumerator(),
    )
    source = CreatorSource.load(discovery.manifest_path)
    result = BatchOperation().execute(
        source,
        BatchPolicy.create(["ru-RU"], {"ru-RU": "ru-RU-DmitryNeural"}),
        tmp_path / "batch",
        "batch-1",
        processor=Processor(),
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert discovery.result_class == "COMPLETED"
    assert result.result_class == "COMPLETED"
    assert manifest["creatorManifestSha256"] == source.manifest_sha256
    assert manifest["expectedItemIds"] == ["video-1", "video-2"]
