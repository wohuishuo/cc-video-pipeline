"""Strictly serial, resumable localized derivative loop."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .contracts import LocalizationError, load_composition_inputs, sha256_file


def _canonical(value:Any)->str: return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def _atomic_json(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True); partial=path.with_name(f".{path.name}.partial")
    partial.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8"); os.replace(partial,path)


@dataclass(frozen=True)
class LocalizationResult:
    result_class:str; receipt_path:Path; manifest_path:Path|None; error:str|None=None


def _valid_derivative(value:Any)->bool:
    try:
        path=Path(value["path"]).resolve()
        return path.is_file() and path.stat().st_size==value["size"] and sha256_file(path)==value["sha256"] and float(value["duration"])>0 and int(value["width"])>0 and int(value["height"])>0 and bool(value["videoCodec"]) and bool(value["audioCodec"])
    except (KeyError,TypeError,ValueError,OSError): return False


class LocalizationLoop:
    def execute(self,source_manifest,translation_manifest,voice_manifest,output_dir,operation_id,*,adapter,source_volume=0.12,on_log=None):
        inputs=load_composition_inputs(source_manifest,translation_manifest,voice_manifest)
        if not operation_id.strip() or not adapter.identity.strip() or not 0<=source_volume<=1: raise LocalizationError("operation, adapter and source volume are invalid")
        output=Path(output_dir).resolve(); output.mkdir(parents=True,exist_ok=True)
        receipt_path=output/"localization-receipt.json"; manifest_path=output/"localization-manifest.json"
        fingerprint=hashlib.sha256(_canonical({"schemaVersion":1,"sourceManifestSha256":inputs.source_manifest_sha256,"translationManifestSha256":inputs.translation_manifest_sha256,"voiceManifestSha256":inputs.voice_manifest_sha256,"sourceVolume":source_volume,"adapter":adapter.identity}).encode()).hexdigest()
        prior=None
        if receipt_path.is_file():
            try: prior=json.loads(receipt_path.read_text(encoding="utf-8-sig"))
            except (OSError,json.JSONDecodeError): pass
        if prior and (prior.get("operationId")!=operation_id or prior.get("inputFingerprint")!=fingerprint): return LocalizationResult("REJECTED_CONFLICT",receipt_path,None,"operation input conflict")
        if prior and prior.get("resultClass")=="COMPLETED" and manifest_path.is_file() and sha256_file(manifest_path)==prior.get("manifestSha256"): return LocalizationResult("DUPLICATE_COMPLETED",receipt_path,manifest_path)
        reusable={}
        for item in (prior or {}).get("items",[]):
            if item.get("status")=="COMPLETED" and _valid_derivative(item.get("derivative")): reusable[(item.get("targetLanguage"),item.get("mediaId"))]=item
        log=on_log or (lambda _message:None); items=[]; derivatives=[]; failures=[]; maximum_active=0
        for index,job in enumerate(inputs.jobs,1):
            key=(job.target_language,job.media_id); reused=reusable.get(key)
            if reused and reused.get("sourceSha256")==job.source_sha256 and reused.get("translationSha256")==job.translation_sha256 and reused.get("srtSha256")==job.srt_sha256:
                items.append({**reused,"reused":True}); derivatives.append(reused["derivative"]); log(f"[{index}/{len(inputs.jobs)}] reused {key[0]}/{key[1]}")
                self._checkpoint(receipt_path,operation_id,fingerprint,adapter.identity,source_volume,items,maximum_active)
                continue
            identity=hashlib.sha256(f"{key[0]}\0{key[1]}".encode()).hexdigest()[:20]
            final=output/"videos"/f"{identity}.mp4"; partial=final.with_name(f".{identity}.partial.mp4")
            log(f"[{index}/{len(inputs.jobs)}] composing {key[0]}/{key[1]}")
            try:
                partial.parent.mkdir(parents=True,exist_ok=True)
                if partial.exists(): partial.unlink()
                probe=adapter.compose(job,partial,log,source_volume=source_volume); maximum_active=max(maximum_active,int(getattr(adapter,"maximum_active",1)))
                if not partial.is_file() or partial.stat().st_size<=0: raise LocalizationError("composition adapter produced no file")
                os.replace(partial,final)
                derivative={"targetLanguage":key[0],"mediaId":key[1],"path":str(final),"sha256":sha256_file(final),"size":final.stat().st_size,"duration":float(probe.duration),"width":int(probe.width),"height":int(probe.height),"videoCodec":str(probe.video_codec),"audioCodec":str(probe.audio_codec)}
                derivatives.append(derivative); items.append({"targetLanguage":key[0],"mediaId":key[1],"sourceSha256":job.source_sha256,"translationSha256":job.translation_sha256,"srtSha256":job.srt_sha256,"status":"COMPLETED","derivative":derivative,"reused":False})
            except Exception as error:
                if partial.exists(): partial.unlink()
                failures.append(key); items.append({"targetLanguage":key[0],"mediaId":key[1],"status":"FAILED","error":f"{type(error).__name__}: {error}"[-4000:]}); log(f"[{index}/{len(inputs.jobs)}] failed {key[0]}/{key[1]}: {error}")
            self._checkpoint(receipt_path,operation_id,fingerprint,adapter.identity,source_volume,items,maximum_active)
        if failures:
            self._checkpoint(receipt_path,operation_id,fingerprint,adapter.identity,source_volume,items,maximum_active,result_class="FAILED",error=f"{len(failures)} derivative(s) failed")
            if manifest_path.exists(): manifest_path.unlink()
            return LocalizationResult("FAILED",receipt_path,None,f"{len(failures)} derivative(s) failed")
        manifest={"schemaVersion":1,"sourceManifest":str(inputs.source_manifest),"sourceManifestSha256":inputs.source_manifest_sha256,"translationManifest":str(inputs.translation_manifest),"translationManifestSha256":inputs.translation_manifest_sha256,"voiceManifest":str(inputs.voice_manifest),"voiceManifestSha256":inputs.voice_manifest_sha256,"sourceVolume":source_volume,"targetLanguages":list(inputs.target_languages),"expectedMediaIds":list(inputs.expected_media_ids),"derivatives":derivatives}
        _atomic_json(manifest_path,manifest); manifest_sha=sha256_file(manifest_path)
        self._checkpoint(receipt_path,operation_id,fingerprint,adapter.identity,source_volume,items,maximum_active,result_class="COMPLETED",manifest=manifest_path,manifest_sha=manifest_sha)
        return LocalizationResult("COMPLETED",receipt_path,manifest_path)

    @staticmethod
    def _checkpoint(path,operation_id,fingerprint,adapter,source_volume,items,maximum_active,*,result_class="RUNNING",error=None,manifest=None,manifest_sha=None):
        _atomic_json(path,{"schemaVersion":1,"operationId":operation_id,"inputFingerprint":fingerprint,"adapter":adapter,"sourceVolume":source_volume,"resultClass":result_class,"items":items,"maximumActiveCompositions":maximum_active,"manifest":str(manifest) if manifest else None,"manifestSha256":manifest_sha,"error":error})
