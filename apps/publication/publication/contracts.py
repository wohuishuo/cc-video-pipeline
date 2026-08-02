"""Verified publication intent contracts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re


class PublicationError(ValueError): pass
PLATFORMS=("youtube","bilibili","douyin","tiktok")
IDENTIFIER=re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def sha256_file(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class PlanSpec:
    video:Path; metadata:Path; targets:tuple[tuple[str,str],...]; credentials:tuple[tuple[str,str],...]=(); public:bool=False

    @classmethod
    def create(cls,video,metadata,targets,*,credentials=None,public=False):
        video_path=Path(video).resolve(); metadata_path=Path(metadata).resolve()
        if not video_path.is_file() or video_path.suffix.lower() not in {".mp4",".mov",".mkv",".webm"}: raise PublicationError("verified video file is required")
        if not metadata_path.is_file(): raise PublicationError("metadata file is required")
        try: value=json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        except (OSError,json.JSONDecodeError) as error: raise PublicationError(f"invalid metadata: {error}") from error
        if not isinstance(value,dict) or not str(value.get("title","")).strip(): raise PublicationError("metadata.title is required")
        if not isinstance(targets,dict) or not targets: raise PublicationError("at least one publication target is required")
        rows=[]
        for platform,account in targets.items():
            if platform not in PLATFORMS or not isinstance(account,str) or not account.strip(): raise PublicationError("targets require supported platforms and account names")
            rows.append((platform,account.strip()))
        credential_rows=[]
        if credentials is not None and not isinstance(credentials,dict): raise PublicationError("credentials must map platform to credential ID")
        for platform,credential_id in (credentials or {}).items():
            if platform not in targets: raise PublicationError("credential platform must have a publication target")
            if not isinstance(credential_id,str) or not IDENTIFIER.fullmatch(credential_id): raise PublicationError("invalid credential ID")
            credential_rows.append((platform,credential_id))
        return cls(video_path,metadata_path,tuple(rows),tuple(credential_rows),bool(public))

    def fingerprint_value(self):
        credentials=dict(self.credentials)
        targets=[]
        for platform,account in self.targets:
            target={"platform":platform,"account":account}
            if platform in credentials: target["credentialId"]=credentials[platform]
            targets.append(target)
        return {"schemaVersion":1,"videoSha256":sha256_file(self.video),"metadataSha256":sha256_file(self.metadata),"targets":targets,"public":self.public}
