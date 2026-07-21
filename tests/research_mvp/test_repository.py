from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research_mvp.models import JobStatus, ResearchDossier, ResearchJob, SourceRef
from research_mvp.repository import ConflictError, FileResearchRepository


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.repo = FileResearchRepository(Path(self.tmp.name))
        self.source = SourceRef("local", "sha256:abc", "file:///clip.mp4")
        self.job = ResearchJob("job-1", self.source, {"language": "zh"})

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_is_idempotent_for_same_job(self):
        self.repo.create_job(self.job)
        self.repo.create_job(self.job)
        self.assertEqual(self.repo.load_job("job-1"), self.job)

    def test_create_rejects_conflicting_existing_job(self):
        self.repo.create_job(self.job)
        changed = ResearchJob("job-1", self.source, {"language": "en"})
        with self.assertRaises(ConflictError):
            self.repo.create_job(changed)

    def test_job_id_cannot_escape_workspace(self):
        with self.assertRaises(ValueError):
            self.repo.load_job("../outside")

    def test_committed_dossier_round_trips(self):
        self.repo.create_job(self.job)
        dossier = ResearchDossier("1", "job-1", JobStatus.COMPLETE, self.source)
        version = self.repo.commit_dossier(dossier)
        self.assertEqual(version, 1)
        self.assertEqual(self.repo.load_dossier("job-1", 1), dossier)


if __name__ == "__main__":
    unittest.main()
