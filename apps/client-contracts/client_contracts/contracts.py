"""Transport-neutral client contract owner."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any


CONTRACT_VERSION="1.0"
COMMANDS=("CMD-RUN-CREATE","CMD-RUN-START","CMD-RUN-CANCEL","CMD-RUN-RETRY")
IDENTITY=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SEMVER=re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


@dataclass(frozen=True)
class ContractResult:
    result_class:str
    value:dict[str,Any]


class ContractError(ValueError):
    def __init__(self,code:str,message:str): super().__init__(message); self.code=code


class ClientContracts:
    def bundle(self)->dict[str,Any]:
        envelope={"required":["contractId","contractVersion","operationId","correlationId","payload"],"additionalProperties":False}
        return {
            "schemaVersion":1,
            "contractVersion":CONTRACT_VERSION,
            "compatibility":{"minimumClientVersion":"1.0.0","supportedClientMajor":1},
            "commands":{command:{**envelope,"contractId":command} for command in COMMANDS},
            "endpoints":{
                "GET /api/v1/health":{"scope":None,"projection":"health"},
                "GET /api/v1/contracts":{"scope":None,"projection":"client-contracts"},
                "GET /api/v1/capabilities":{"scope":"runs:read","projection":"capabilities"},
                "GET /api/v1/queue":{"scope":"runs:read","projection":"queue"},
                "GET /api/v1/runs":{"scope":"runs:read","projection":"run-list"},
                "GET /api/v1/runs/{runId}":{"scope":"runs:read","projection":"run-detail"},
                "POST /api/v1/runs":{"scope":"runs:write","command":"CMD-RUN-CREATE"},
                "POST /api/v1/runs/{runId}/start":{"scope":"runs:write","command":"CMD-RUN-START"},
                "POST /api/v1/runs/{runId}/cancel":{"scope":"runs:write","command":"CMD-RUN-CANCEL"},
                "POST /api/v1/runs/{runId}/retry":{"scope":"runs:write","command":"CMD-RUN-RETRY"},
                "GET /api/v1/folders":{"scope":"artifacts:read","projection":"folder-list"},
            },
            "ownership":{"runState":"Video Graph Studio","workspaceAdmission":"Workspace Access","clientProjection":"disposable"},
        }

    def show(self)->ContractResult:
        bundle=self.bundle(); data=self._encoded(bundle)
        return ContractResult("COMPLETED",{"bundle":bundle,"sha256":hashlib.sha256(data).hexdigest()})

    def export(self,path:Path)->ContractResult:
        target=Path(path).resolve(); data=self._encoded(self.bundle()); digest=hashlib.sha256(data).hexdigest()
        if target.is_file() and target.read_bytes()==data: return ContractResult("DUPLICATE_COMPLETED",{"path":str(target),"sha256":digest,"contractVersion":CONTRACT_VERSION})
        target.parent.mkdir(parents=True,exist_ok=True); descriptor,name=tempfile.mkstemp(prefix=f".{target.name}.",suffix=".tmp",dir=target.parent); temporary=Path(name)
        try:
            with os.fdopen(descriptor,"wb") as stream: stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary,target)
        finally: temporary.unlink(missing_ok=True)
        return ContractResult("COMPLETED",{"path":str(target),"sha256":digest,"contractVersion":CONTRACT_VERSION})

    @staticmethod
    def _encoded(bundle:dict[str,Any])->bytes:
        return (json.dumps(bundle,ensure_ascii=False,indent=2)+"\n").encode("utf-8")

    def validate_command(self,value:Any,expected_contract:str)->ContractResult:
        if expected_contract not in COMMANDS: raise ContractError("REJECTED_MALFORMED","unknown expected contract")
        required={"contractId","contractVersion","operationId","correlationId","payload"}
        if not isinstance(value,dict) or set(value)!=required: raise ContractError("REJECTED_MALFORMED","command fields do not match the envelope")
        if value["contractId"]!=expected_contract: raise ContractError("REJECTED_CONTRACT","command contract ID mismatch")
        if value["contractVersion"]!=CONTRACT_VERSION: raise ContractError("REJECTED_VERSION","unsupported contract version")
        if not isinstance(value["payload"],dict) or not all(isinstance(value[key],str) and IDENTITY.fullmatch(value[key]) for key in ("operationId","correlationId")): raise ContractError("REJECTED_MALFORMED","invalid command identity or payload")
        return ContractResult("VALID",{"contractId":expected_contract,"contractVersion":CONTRACT_VERSION})

    def check_client(self,version:str)->ContractResult:
        match=SEMVER.fullmatch(version) if isinstance(version,str) else None
        if not match: raise ContractError("REJECTED_MALFORMED","client version must be semantic x.y.z")
        major,minor,patch=map(int,match.groups()); compatible=major==1 and (major,minor,patch)>=(1,0,0)
        return ContractResult("COMPATIBLE" if compatible else "REJECTED_CLIENT",{"clientVersion":version,"contractVersion":CONTRACT_VERSION,"minimumClientVersion":"1.0.0","supportedClientMajor":1})
