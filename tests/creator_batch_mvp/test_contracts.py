import json
from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "creator-batch"
sys.path.insert(0, str(APP))

from creator_batch.contracts import BatchContractError, BatchPolicy, CreatorSource


def write_manifest(tmp_path, *, items=None, platform="douyin"):
    value = {
        "schemaVersion": 1,
        "platform": platform,
        "requestedUrl": "https://www.douyin.com/user/creator",
        "creator": {"id": "creator-1", "name": "Creator"},
        "adapter": "fixture@1",
        "maxItems": 0,
        "complete": True,
        "truncated": False,
        "items": items
        or [
            {
                "ordinal": 1,
                "id": "video-1",
                "url": "https://www.douyin.com/video/1",
                "title": "First",
                "publishedAt": 123,
            },
            {
                "ordinal": 2,
                "id": "video-2",
                "url": "https://www.douyin.com/video/2",
                "title": "Second",
                "publishedAt": None,
            },
        ],
    }
    path = tmp_path / "creator-manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_creator_source_loads_ordered_manifest_and_commits_its_fingerprint(tmp_path):
    source = CreatorSource.load(write_manifest(tmp_path))

    assert source.platform == "douyin"
    assert [item.id for item in source.items] == ["video-1", "video-2"]
    assert len(source.manifest_sha256) == 64
    assert source.to_public_dict()["expectedItemIds"] == ["video-1", "video-2"]


@pytest.mark.parametrize(
    "items",
    [
        [{"ordinal": 2, "id": "video-1", "url": "https://www.douyin.com/video/1", "title": "First", "publishedAt": None}],
        [
            {"ordinal": 1, "id": "duplicate", "url": "https://www.douyin.com/video/1", "title": "First", "publishedAt": None},
            {"ordinal": 2, "id": "duplicate", "url": "https://www.douyin.com/video/2", "title": "Second", "publishedAt": None},
        ],
        [{"ordinal": 1, "id": "video-1", "url": "https://example.com/video/1", "title": "First", "publishedAt": None}],
    ],
)
def test_creator_source_rejects_broken_order_identity_or_platform_url(tmp_path, items):
    with pytest.raises(BatchContractError):
        CreatorSource.load(write_manifest(tmp_path, items=items))


def test_batch_policy_requires_exact_language_voice_coverage_and_safe_ranges():
    policy = BatchPolicy.create(
        ["ru-RU", "en-US"],
        {"ru-RU": "ru-RU-DmitryNeural", "en-US": "en-US-GuyNeural"},
        source_volume=0.12,
        translation_batch_size=8,
        max_height=1080,
    )

    assert policy.target_languages == ("ru-RU", "en-US")
    assert policy.to_public_dict()["targetVoices"]["ru-RU"] == "ru-RU-DmitryNeural"
    assert policy.voice_provider == "edge"
    assert "qwenDevice" not in policy.to_public_dict()

    qwen = BatchPolicy.create(
        ["ru-RU", "en-US"], {"ru-RU": "Ryan", "en-US": "Aiden"},
        voice_provider="qwen3",
    )
    original = BatchPolicy.create(
        ["kk-KZ"], {"kk-KZ": "original-audio"}, voice_provider="original",
    )
    assert qwen.to_public_dict()["voiceProvider"] == "qwen3"
    assert qwen.to_public_dict()["qwenDevice"] == "auto"
    assert original.to_public_dict()["voiceProvider"] == "original"
    assert "qwenDevice" not in original.to_public_dict()

    with pytest.raises(BatchContractError, match="Qwen3-TTS"):
        BatchPolicy.create(
            ["kk-KZ"], {"kk-KZ": "Ryan"}, voice_provider="qwen3"
        )
    with pytest.raises(BatchContractError, match="voice provider"):
        BatchPolicy.create(
            ["ru-RU"], {"ru-RU": "voice"}, voice_provider="unknown"
        )
    with pytest.raises(BatchContractError, match="Qwen device"):
        BatchPolicy.create(
            ["ru-RU"], {"ru-RU": "Ryan"}, voice_provider="qwen3", qwen_device="metal"
        )

    invalid = [
        ([], {}, 0.12, 8, 1080),
        (["ru-RU", "ru-RU"], {"ru-RU": "voice"}, 0.12, 8, 1080),
        (["xx-XX"], {"xx-XX": "voice"}, 0.12, 8, 1080),
        (["ru-RU"], {"en-US": "voice"}, 0.12, 8, 1080),
        (["ru-RU"], {"ru-RU": ""}, 0.12, 8, 1080),
        (["ru-RU"], {"ru-RU": "voice"}, 1.01, 8, 1080),
        (["ru-RU"], {"ru-RU": "voice"}, 0.12, 0, 1080),
        (["ru-RU"], {"ru-RU": "voice"}, 0.12, 8, 720),
    ]
    for languages, voices, volume, batch_size, height in invalid:
        with pytest.raises(BatchContractError):
            BatchPolicy.create(
                languages,
                voices,
                source_volume=volume,
                translation_batch_size=batch_size,
                max_height=height,
            )


def test_contract_representations_do_not_expose_unmodeled_secret_material(tmp_path):
    source = CreatorSource.load(write_manifest(tmp_path))
    policy = BatchPolicy.create(["kk-KZ"], {"kk-KZ": "kk-KZ-DauletNeural"})

    rendered = repr(source) + repr(policy) + json.dumps(policy.to_public_dict())

    assert "cookie" not in rendered.lower()
    assert "secret" not in rendered.lower()
