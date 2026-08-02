"""Atomic, idempotent publication planning."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .contracts import PlanSpec, sha256_file


def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True); partial=path.with_name(f".{path.name}.partial"); partial.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8"); os.replace(partial,path)


@dataclass(frozen=True)
class PlanningResult:
    result_class:str; receipt_path:Path; plan_path:Path|None; error:str|None=None


class PublicationPlanner:
    def execute(self,spec:PlanSpec,output_dir,operation_id):
        output=Path(output_dir).resolve(); output.mkdir(parents=True,exist_ok=True); receipt=output/"planning-receipt.json"; plan_path=output/"publication-plan.json"
        fingerprint=hashlib.sha256(canonical(spec.fingerprint_value()).encode()).hexdigest(); prior=self._read(receipt)
        if prior and (prior.get("operationId")!=operation_id or prior.get("inputFingerprint")!=fingerprint): return PlanningResult("REJECTED_CONFLICT",receipt,None,"operation input conflict")
        if prior and prior.get("resultClass")=="COMPLETED" and plan_path.is_file() and sha256_file(plan_path)==prior.get("planSha256"): return PlanningResult("DUPLICATE_COMPLETED",receipt,plan_path)
        metadata=json.loads(spec.metadata.read_text(encoding="utf-8-sig")); video_sha=sha256_file(spec.video); metadata_sha=sha256_file(spec.metadata); visibility="public" if spec.public else "private-or-draft"
        jobs=[]; credentials=dict(spec.credentials)
        for ordinal,(platform,account) in enumerate(spec.targets,1):
            credential_id=credentials.get(platform); identity_input=f"{video_sha}\0{metadata_sha}\0{platform}\0{account}\0{visibility}" + (f"\0{credential_id}" if credential_id else ""); identity=hashlib.sha256(identity_input.encode()).hexdigest()
            job={"ordinal":ordinal,"id":identity,"platform":platform,"account":account,"visibility":visibility}
            if credential_id: job["credentialId"]=credential_id
            jobs.append(job)
        plan={"schemaVersion":1,"video":{"path":str(spec.video),"sha256":video_sha,"size":spec.video.stat().st_size},"metadata":{"path":str(spec.metadata),"sha256":metadata_sha,"title":str(metadata["title"]).strip()},"public":spec.public,"jobs":jobs}
        atomic(plan_path,plan); plan_sha=sha256_file(plan_path); atomic(receipt,{"schemaVersion":1,"operationId":operation_id,"inputFingerprint":fingerprint,"resultClass":"COMPLETED","plan":str(plan_path),"planSha256":plan_sha,"jobCount":len(jobs)})
        return PlanningResult("COMPLETED",receipt,plan_path)

    @staticmethod
    def _read(path):
        try:return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None
        except (OSError,json.JSONDecodeError):return None
