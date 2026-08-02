"""Confirmed, serial and resumable publication execution."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from .contracts import PublicationError, sha256_file
from .planning import atomic, canonical


PRIVATE_GUARANTEED={"youtube"}


@dataclass(frozen=True)
class ExecutionOutcome:
    completed:bool; external_id:str|None; facts:dict[str,Any]; error:str|None=None


@dataclass(frozen=True)
class ExecutionResult:
    result_class:str; receipt_path:Path; manifest_path:Path|None; error:str|None=None


class PlatformIOExecutionAdapter:
    identity="platform-io-upload@1"
    def __init__(self,launcher:Path): self.launcher=Path(launcher).resolve(); self.maximum_active=0
    def execute(self,job,on_log):
        argv=["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(self.launcher),"upload",job["platform"],job["videoPath"],"--metadata",job["metadataPath"],"--account",job["account"],"--execute","--json"]
        if job["visibility"]=="public": argv.append("--public")
        self.maximum_active=1; result=subprocess.run(argv,text=True,capture_output=True,encoding="utf-8",errors="replace")
        try: payload=json.loads(result.stdout)
        except json.JSONDecodeError: payload={}
        if result.returncode!=0 or payload.get("status")!="ok": return ExecutionOutcome(False,None,{"exitCode":result.returncode},str(payload.get("error") or result.stderr[-4000:] or "platform upload failed"))
        return ExecutionOutcome(True,str(payload.get("external_id") or "") or None,{"exitCode":result.returncode,"executed":True,"visibility":job["visibility"]})


class PublicationExecution:
    def execute(self,plan_path,output_dir,operation_id,*,confirmation,adapter,on_log=None):
        plan_path=Path(plan_path).resolve(); output=Path(output_dir).resolve(); output.mkdir(parents=True,exist_ok=True); receipt=output/"publication-receipt.json"; manifest_path=output/"publication-manifest.json"
        if not plan_path.is_file(): return ExecutionResult("REJECTED_MALFORMED",receipt,None,"publication plan missing")
        plan_sha=sha256_file(plan_path)
        if confirmation!=plan_sha: return ExecutionResult("REJECTED_CONFIRMATION",receipt,None,"confirmation must equal publication plan SHA-256")
        try: plan=json.loads(plan_path.read_text(encoding="utf-8-sig")); jobs=plan["jobs"]; video=plan["video"]; metadata=plan["metadata"]
        except (OSError,KeyError,TypeError,json.JSONDecodeError) as error:return ExecutionResult("REJECTED_MALFORMED",receipt,None,str(error))
        if plan.get("schemaVersion")!=1 or not jobs or sha256_file(video["path"])!=video["sha256"] or sha256_file(metadata["path"])!=metadata["sha256"]: return ExecutionResult("REJECTED_CONFLICT",receipt,None,"publication inputs changed")
        blocked=[job["platform"] for job in jobs if job["visibility"]!="public" and job["platform"] not in PRIVATE_GUARANTEED]
        if blocked:return ExecutionResult("REJECTED_POLICY",receipt,None,f"private/draft visibility is not guaranteed for: {', '.join(blocked)}")
        fingerprint=hashlib.sha256(canonical({"planSha256":plan_sha,"adapter":adapter.identity}).encode()).hexdigest(); prior=self._read(receipt)
        if prior and (prior.get("operationId")!=operation_id or prior.get("inputFingerprint")!=fingerprint):return ExecutionResult("REJECTED_CONFLICT",receipt,None,"operation input conflict")
        if prior and prior.get("resultClass")=="COMPLETED" and manifest_path.is_file() and sha256_file(manifest_path)==prior.get("manifestSha256"):return ExecutionResult("DUPLICATE_COMPLETED",receipt,manifest_path)
        reusable={item["jobId"]:item for item in (prior or {}).get("items",[]) if item.get("status")=="COMPLETED"}; items=[]; failures=[]; maximum=0; log=on_log or (lambda _:None)
        for index,job in enumerate(jobs,1):
            if job["id"] in reusable: items.append({**reusable[job["id"]],"reused":True}); continue
            request={**job,"videoPath":video["path"],"metadataPath":metadata["path"]}; log(f"[{index}/{len(jobs)}] publishing {job['platform']}")
            outcome=adapter.execute(request,log); maximum=max(maximum,int(getattr(adapter,"maximum_active",1)))
            if outcome.completed: items.append({"jobId":job["id"],"platform":job["platform"],"status":"COMPLETED","externalId":outcome.external_id,"facts":outcome.facts,"reused":False})
            else: failures.append(job["id"]); items.append({"jobId":job["id"],"platform":job["platform"],"status":"FAILED","error":outcome.error})
            self._checkpoint(receipt,operation_id,fingerprint,plan_path,plan_sha,items,maximum)
        if failures:
            self._checkpoint(receipt,operation_id,fingerprint,plan_path,plan_sha,items,maximum,result_class="FAILED",error=f"{len(failures)} publication(s) failed"); return ExecutionResult("FAILED",receipt,None,"publication failed")
        manifest={"schemaVersion":1,"plan":str(plan_path),"planSha256":plan_sha,"public":bool(plan.get("public")),"publications":items}; atomic(manifest_path,manifest); manifest_sha=sha256_file(manifest_path)
        self._checkpoint(receipt,operation_id,fingerprint,plan_path,plan_sha,items,maximum,result_class="COMPLETED",manifest=manifest_path,manifest_sha=manifest_sha); return ExecutionResult("COMPLETED",receipt,manifest_path)

    @staticmethod
    def _read(path):
        try:return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None
        except (OSError,json.JSONDecodeError):return None
    @staticmethod
    def _checkpoint(path,operation_id,fingerprint,plan,plan_sha,items,maximum,*,result_class="RUNNING",manifest=None,manifest_sha=None,error=None):
        atomic(path,{"schemaVersion":1,"operationId":operation_id,"inputFingerprint":fingerprint,"plan":str(plan),"planSha256":plan_sha,"resultClass":result_class,"items":items,"maximumActiveExecutions":maximum,"manifest":str(manifest) if manifest else None,"manifestSha256":manifest_sha,"error":error})
