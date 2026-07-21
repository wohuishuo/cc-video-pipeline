from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research_mvp.models import JobStatus, SourceRef
from research_mvp.repository import FileResearchRepository
from research_mvp.service import ResearchService
from tests.research_mvp.fakes import FakeCollector, FakeConnector


class ResearchServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.repo = FileResearchRepository(self.workspace)
        self.source = SourceRef(
            "bilibili",
            "BV1abc",
            "https://www.bilibili.com/video/BV1abc",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def service(self, collector):
        return ResearchService(
            self.repo, FakeConnector(self.source), collector
        )

    def test_create_commits_useful_dossier(self):
        dossier = self.service(FakeCollector()).create(
            "raw", {"language": "zh"}
        )
        self.assertEqual(dossier.status, JobStatus.COMPLETE)
        self.assertEqual(dossier.facts["title"], "Fixture video")

    def test_optional_gap_is_explicit_terminal_result(self):
        dossier = self.service(
            FakeCollector(gaps=("visual_evidence_unavailable",))
        ).create("raw", {})
        self.assertEqual(dossier.status, JobStatus.COMPLETE_WITH_GAPS)
        self.assertEqual(
            dossier.gaps, ("visual_evidence_unavailable",)
        )

    def test_failure_can_be_retried_without_new_job_identity(self):
        failing = self.service(
            FakeCollector(error=RuntimeError("collector unavailable"))
        )
        with self.assertRaisesRegex(RuntimeError, "collector unavailable"):
            failing.create("raw", {})
        job = next(self.workspace.iterdir()).name
        self.assertEqual(self.repo.load_job(job).status, JobStatus.FAILED)
        recovered = self.service(FakeCollector()).retry(job)
        self.assertEqual(recovered.job_id, job)
        self.assertEqual(recovered.status, JobStatus.COMPLETE)

    def test_same_source_and_config_is_idempotent(self):
        service = self.service(FakeCollector())
        first = service.create("raw", {"language": "zh"})
        second = service.create("raw", {"language": "zh"})
        self.assertEqual(first, second)
        self.assertEqual(
            self.repo.load_job(first.job_id).dossier_version, 1
        )


if __name__ == "__main__":
    unittest.main()
