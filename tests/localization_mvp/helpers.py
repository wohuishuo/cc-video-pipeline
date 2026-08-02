import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifests(tmp_path: Path, *, omit_voice_segment: bool = False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"source-video")
    source = tmp_path / "source-manifest.json"
    source.write_text(json.dumps({
        "schemaVersion": 1, "sourceKind": "folder", "source": {},
        "media": [{"id": "m1", "path": str(source_video), "size": source_video.stat().st_size, "extension": ".mp4"}],
    }), encoding="utf-8")
    transcript = tmp_path / "transcript-manifest.json"
    transcript.write_text(json.dumps({"schemaVersion":1,"sourceManifest":str(source),"sourceManifestSha256":digest(source)}),encoding="utf-8")
    translations=[]; voice_clips=[]
    language_words={"ru-RU":["Привет","Мир"],"en-US":["Hello","World"]}
    for language, words in language_words.items():
        folder=tmp_path/language; folder.mkdir()
        document=folder/"translation.json"
        segments=[
            {"id":1,"start":0.0,"end":2.0,"sourceText":"一","translatedText":words[0]},
            {"id":2,"start":3.0,"end":4.0,"sourceText":"二","translatedText":words[1]},
        ]
        document.write_text(json.dumps({"schemaVersion":1,"source":{"mediaId":"m1","language":"zh"},"targetLanguage":language,"reviewStatus":"MACHINE","segments":segments},ensure_ascii=False),encoding="utf-8")
        srt=folder/"translation.srt"; srt.write_text(f"1\n00:00:00,000 --> 00:00:02,000\n{words[0]}\n",encoding="utf-8")
        translations.append({"mediaId":"m1","targetLanguage":language,"translationPath":str(document),"translationSha256":digest(document),"srtPath":str(srt),"srtSha256":digest(srt),"reviewStatus":"MACHINE","segmentCount":2})
        for segment in segments:
            if omit_voice_segment and language=="ru-RU" and segment["id"]==2: continue
            clip=folder/f"{segment['id']}.mp3"; clip.write_bytes(f"audio-{language}-{segment['id']}".encode())
            voice_clips.append({"targetLanguage":language,"mediaId":"m1","segmentId":segment["id"],"translationSha256":digest(document),"start":segment["start"],"end":segment["end"],"text":segment["translatedText"],"textSha256":hashlib.sha256(segment["translatedText"].encode()).hexdigest(),"voice":f"{language}-Voice","clip":{"path":str(clip),"sha256":digest(clip),"duration":2.5 if segment["id"]==2 else 1.0,"size":clip.stat().st_size}})
    translation=tmp_path/"translation-manifest.json"
    translation.write_text(json.dumps({"schemaVersion":1,"transcriptManifest":str(transcript),"transcriptManifestSha256":digest(transcript),"expectedMediaIds":["m1"],"targetLanguages":["ru-RU","en-US"],"translations":translations},ensure_ascii=False),encoding="utf-8")
    voice=tmp_path/"voice-manifest.json"
    voice.write_text(json.dumps({"schemaVersion":1,"translationManifest":str(translation),"translationManifestSha256":digest(translation),"voices":{"ru-RU":"ru-RU-Voice","en-US":"en-US-Voice"},"clips":voice_clips},ensure_ascii=False),encoding="utf-8")
    return source, translation, voice
