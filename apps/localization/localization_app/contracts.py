"""Public input contracts for localized video composition."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


class LocalizationError(ValueError):
    pass


def sha256_file(path: str | Path) -> str:
    digest=hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda:source.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path, label: str) -> dict[str,Any]:
    if not path.is_file(): raise LocalizationError(f"{label} missing: {path}")
    try: value=json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError) as error: raise LocalizationError(f"invalid {label}: {error}") from error
    if not isinstance(value,dict) or value.get("schemaVersion")!=1: raise LocalizationError(f"invalid {label} contract")
    return value


def _verified(raw_path: Any, expected: Any, label: str) -> Path:
    path=Path(str(raw_path)).resolve()
    if not isinstance(expected,str) or len(expected)!=64 or not path.is_file() or sha256_file(path)!=expected:
        raise LocalizationError(f"{label} fingerprint mismatch")
    return path


@dataclass(frozen=True)
class CompositionSegment:
    id:int; start:float; end:float; text:str


@dataclass(frozen=True)
class VoiceClip:
    segment_id:int; path:Path; sha256:str; duration:float; size:int; voice:str


@dataclass(frozen=True)
class CompositionJob:
    target_language:str; media_id:str; source_path:Path; source_sha256:str
    translation_path:Path; translation_sha256:str; srt_path:Path; srt_sha256:str
    segments:tuple[CompositionSegment,...]; clips:tuple[VoiceClip,...]


@dataclass(frozen=True)
class CompositionInput:
    source_manifest:Path; source_manifest_sha256:str
    translation_manifest:Path; translation_manifest_sha256:str
    voice_manifest:Path; voice_manifest_sha256:str
    target_languages:tuple[str,...]; expected_media_ids:tuple[str,...]; jobs:tuple[CompositionJob,...]


def load_composition_inputs(source_manifest,translation_manifest,voice_manifest)->CompositionInput:
    source_path=Path(source_manifest).resolve(); translation_path=Path(translation_manifest).resolve(); voice_path=Path(voice_manifest).resolve()
    source=_json(source_path,"source manifest"); translation=_json(translation_path,"translation manifest"); voice=_json(voice_path,"voice manifest")
    source_sha=sha256_file(source_path); translation_sha=sha256_file(translation_path); voice_sha=sha256_file(voice_path)
    transcript_path=_verified(translation.get("transcriptManifest"),translation.get("transcriptManifestSha256"),"transcript manifest")
    transcript=_json(transcript_path,"transcript manifest")
    if Path(str(transcript.get("sourceManifest",""))).resolve()!=source_path or transcript.get("sourceManifestSha256")!=source_sha:
        raise LocalizationError("source lineage mismatch")
    if Path(str(voice.get("translationManifest",""))).resolve()!=translation_path or voice.get("translationManifestSha256")!=translation_sha:
        raise LocalizationError("voice translation lineage mismatch")
    media_rows=source.get("media"); media_ids=translation.get("expectedMediaIds"); languages=translation.get("targetLanguages"); translation_rows=translation.get("translations")
    if not isinstance(media_rows,list) or not isinstance(media_ids,list) or not media_ids or not isinstance(languages,list) or not languages or not isinstance(translation_rows,list):
        raise LocalizationError("manifest owner fields are invalid")
    media_by_id={str(row.get("id")):row for row in media_rows if isinstance(row,dict)}
    if list(media_by_id)!=media_ids: raise LocalizationError("source and translation coverage mismatch")
    expected_pairs=[(language,media_id) for language in languages for media_id in media_ids]
    if [(row.get("targetLanguage"),row.get("mediaId")) for row in translation_rows]!=expected_pairs:
        raise LocalizationError("translation coverage mismatch")
    clip_rows=voice.get("clips"); voices=voice.get("voices")
    if not isinstance(clip_rows,list) or not isinstance(voices,dict) or set(voices)!=set(languages):
        raise LocalizationError("voice owner fields are invalid")
    clips_by_job:dict[tuple[str,str],list[dict[str,Any]]]={}
    for clip in clip_rows:
        if not isinstance(clip,dict): raise LocalizationError("invalid voice clip row")
        clips_by_job.setdefault((str(clip.get("targetLanguage")),str(clip.get("mediaId"))),[]).append(clip)
    jobs=[]
    for row in translation_rows:
        language=str(row["targetLanguage"]); media_id=str(row["mediaId"]); media=media_by_id[media_id]
        source_file=Path(str(media.get("path",""))).resolve()
        if not source_file.is_file() or source_file.stat().st_size!=media.get("size"): raise LocalizationError("source media fingerprint mismatch")
        document_path=_verified(row.get("translationPath"),row.get("translationSha256"),"translation")
        srt_path=_verified(row.get("srtPath"),row.get("srtSha256"),"subtitle")
        document=_json(document_path,"translation document"); raw_segments=document.get("segments")
        if document.get("targetLanguage")!=language or document.get("source",{}).get("mediaId")!=media_id or not isinstance(raw_segments,list) or len(raw_segments)!=row.get("segmentCount"):
            raise LocalizationError("translation document mismatch")
        segments=tuple(CompositionSegment(int(item["id"]),float(item["start"]),float(item["end"]),str(item["translatedText"]).strip()) for item in raw_segments)
        if [item.id for item in segments]!=list(range(1,len(segments)+1)) or any(item.start<0 or item.end<=item.start or not item.text for item in segments):
            raise LocalizationError("invalid composition segments")
        raw_clips=clips_by_job.get((language,media_id),[])
        if [item.get("segmentId") for item in raw_clips]!=[item.id for item in segments]: raise LocalizationError("voice coverage mismatch")
        clips=[]
        for segment,item in zip(segments,raw_clips,strict=True):
            data=item.get("clip",{}); clip_path=_verified(data.get("path"),data.get("sha256"),"voice clip")
            if item.get("translationSha256")!=row.get("translationSha256") or item.get("text")!=segment.text or float(item.get("start"))!=segment.start or float(item.get("end"))!=segment.end or item.get("voice")!=voices[language] or data.get("size")!=clip_path.stat().st_size or float(data.get("duration",0))<=0:
                raise LocalizationError("voice clip lineage mismatch")
            clips.append(VoiceClip(segment.id,clip_path,str(data["sha256"]),float(data["duration"]),int(data["size"]),str(item["voice"])))
        jobs.append(CompositionJob(language,media_id,source_file,sha256_file(source_file),document_path,str(row["translationSha256"]),srt_path,str(row["srtSha256"]),segments,tuple(clips)))
    if set(clips_by_job)!=set(expected_pairs): raise LocalizationError("voice coverage mismatch")
    return CompositionInput(source_path,source_sha,translation_path,translation_sha,voice_path,voice_sha,tuple(languages),tuple(media_ids),tuple(jobs))
