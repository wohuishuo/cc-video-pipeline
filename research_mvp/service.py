from dataclasses import replace

from .models import JobStatus, ResearchDossier, ResearchJob, stable_job_id
from .ports import EvidenceCollector, SourceConnector
from .repository import ConflictError, FileResearchRepository


class ResearchService:
    def __init__(
        self,
        repository: FileResearchRepository,
        connector: SourceConnector,
        collector: EvidenceCollector,
    ):
        self.repository = repository
        self.connector = connector
        self.collector = collector

    def create(
        self, raw_source: str, config: dict[str, object]
    ) -> ResearchDossier:
        source = self.connector.resolve(raw_source)
        job_id = stable_job_id(source, config)
        job = ResearchJob(job_id, source, config)
        try:
            current = self.repository.create_job(job)
        except ConflictError:
            current = self.repository.load_job(job_id)
            if current.source != source or current.config != config:
                raise
        if current.dossier_version is not None:
            return self.repository.load_dossier(job_id)
        return self._run(current)

    def retry(self, job_id: str) -> ResearchDossier:
        job = self.repository.load_job(job_id)
        if job.status != JobStatus.FAILED:
            if job.dossier_version is not None:
                return self.repository.load_dossier(job_id)
            raise ValueError(
                "only failed or completed jobs can be retried idempotently"
            )
        return self._run(replace(job, status=JobStatus.PENDING, error=None))

    def status(self, job_id: str) -> ResearchJob:
        return self.repository.load_job(job_id)

    def show(self, job_id: str) -> ResearchDossier:
        return self.repository.load_dossier(job_id)

    def _run(self, job: ResearchJob) -> ResearchDossier:
        collecting = replace(job, status=JobStatus.COLLECTING, error=None)
        self.repository.save_job(collecting)
        try:
            facts = self.connector.facts(job.source)
            evidence, gaps = self.collector.collect(
                job.source,
                self.repository.workspace / job.job_id / "evidence",
            )
            status = (
                JobStatus.COMPLETE_WITH_GAPS if gaps else JobStatus.COMPLETE
            )
            dossier = ResearchDossier(
                schema_version="1",
                job_id=job.job_id,
                status=status,
                source=job.source,
                facts=facts,
                evidence=evidence,
                gaps=gaps,
            )
            self.repository.commit_dossier(dossier)
            return dossier
        except Exception as error:
            self.repository.save_job(
                replace(job, status=JobStatus.FAILED, error=str(error))
            )
            raise
