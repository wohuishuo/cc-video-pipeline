import unittest

from research_mvp.models import SourceRef, stable_job_id


class SourceIdentityTests(unittest.TestCase):
    def test_equivalent_source_has_stable_job_id(self):
        source = SourceRef(
            platform="bilibili",
            source_id="BV1abc",
            canonical_url="https://www.bilibili.com/video/BV1abc",
        )
        self.assertEqual(
            stable_job_id(source, {"language": "zh"}),
            stable_job_id(source, {"language": "zh"}),
        )

    def test_evidence_affecting_configuration_changes_job_id(self):
        source = SourceRef("local", "sha256:abc", "file:///clip.mp4")
        self.assertNotEqual(
            stable_job_id(source, {"language": "zh"}),
            stable_job_id(source, {"language": "en"}),
        )

    def test_source_ref_rejects_secret_bearing_url(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            SourceRef("example", "123", "https://user:secret@example.com/v/123")


if __name__ == "__main__":
    unittest.main()
