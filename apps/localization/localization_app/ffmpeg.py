"""Pure FFmpeg planning and production composition adapter."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Callable

from .contracts import CompositionJob, LocalizationError


@dataclass(frozen=True)
class ProbeResult:
    duration:float; width:int; height:int; video_codec:str; audio_codec:str; has_audio:bool


def _escape_filter_path(path:Path)->str:
    return str(path.resolve()).replace("\\","/").replace(":","\\:").replace("'","\\'")


def _atempo(factor:float)->list[float]:
    values=[]
    while factor>2.0:
        values.append(2.0); factor/=2.0
    if factor>1.000001: values.append(factor)
    return values


def build_ffmpeg_argv(job:CompositionJob,output:Path,*,source_has_audio:bool,source_volume:float)->list[str]:
    if not 0<=source_volume<=1: raise LocalizationError("source volume must be between 0 and 1")
    argv=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(job.source_path)]
    for clip in job.clips: argv.extend(["-i",str(clip.path)])
    filters=[]; labels=[]
    for index,(segment,clip) in enumerate(zip(job.segments,job.clips,strict=True)):
        chain=[]; window=segment.end-segment.start
        if clip.duration>window:
            chain.extend(f"atempo={value:.6f}" for value in _atempo(clip.duration/window))
        chain.append(f"adelay={round(segment.start*1000)}|{round(segment.start*1000)}")
        label=f"v{index}"; labels.append(f"[{label}]")
        filters.append(f"[{index+1}:a]"+",".join(chain)+f"[{label}]")
    if len(labels)==1: filters.append(f"{labels[0]}anull[voice]")
    else: filters.append("".join(labels)+f"amix=inputs={len(labels)}:normalize=0:duration=longest[voice]")
    if source_has_audio:
        filters.append(f"[0:a]volume={source_volume:.6f}[bed]")
        filters.append("[bed][voice]amix=inputs=2:normalize=0:duration=longest[aout]")
    else: filters.append("[voice]anull[aout]")
    style="FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,MarginV=36"
    filters.append(f"[0:v]subtitles='{_escape_filter_path(job.srt_path)}':force_style='{style}'[vout]")
    argv.extend(["-filter_complex",";".join(filters),"-map","[vout]","-map","[aout]","-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart","-shortest","-f","mp4",str(output)])
    return argv


class FfmpegCompositionAdapter:
    identity="ffmpeg-localization@1"
    def __init__(self,*,command_runner=None,source_probe=None,output_probe=None):
        self.command_runner=command_runner or self._run
        self.source_probe=source_probe or self._source_has_audio
        self.output_probe=output_probe or self._probe_output
        self.active=0; self.maximum_active=0

    def compose(self,job,output,on_log,*,source_volume):
        self.active+=1; self.maximum_active=max(self.maximum_active,self.active)
        try:
            has_audio=bool(self.source_probe(job.source_path)); argv=build_ffmpeg_argv(job,output,source_has_audio=has_audio,source_volume=source_volume)
            output.parent.mkdir(parents=True,exist_ok=True); self.command_runner(argv)
            if not output.is_file() or output.stat().st_size<=0: raise LocalizationError("FFmpeg did not produce output")
            probe=self.output_probe(output)
            if probe.duration<=0 or probe.width<=0 or probe.height<=0 or not probe.video_codec or not probe.has_audio or not probe.audio_codec:
                raise LocalizationError("localized output failed probe verification")
            on_log(f"Verified {probe.duration:.3f}s {probe.width}x{probe.height} {probe.video_codec}/{probe.audio_codec}")
            return probe
        finally: self.active-=1

    @staticmethod
    def _run(argv):
        completed=subprocess.run(argv,capture_output=True,text=True,encoding="utf-8",errors="replace")
        if completed.returncode!=0: raise RuntimeError((completed.stderr or completed.stdout or "ffmpeg failed")[-4000:])

    @staticmethod
    def _source_has_audio(path):
        completed=subprocess.run(["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=index","-of","json",str(path)],capture_output=True,text=True,encoding="utf-8",errors="replace")
        if completed.returncode!=0: raise RuntimeError((completed.stderr or "ffprobe failed")[-2000:])
        return bool(json.loads(completed.stdout).get("streams"))

    @staticmethod
    def _probe_output(path):
        completed=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,codec_name,width,height","-of","json",str(path)],capture_output=True,text=True,encoding="utf-8",errors="replace")
        if completed.returncode!=0: raise RuntimeError((completed.stderr or "ffprobe failed")[-2000:])
        value=json.loads(completed.stdout); streams=value.get("streams",[]); video=next((row for row in streams if row.get("codec_type")=="video"),{}); audio=next((row for row in streams if row.get("codec_type")=="audio"),{})
        return ProbeResult(float(value.get("format",{}).get("duration",0)),int(video.get("width",0)),int(video.get("height",0)),str(video.get("codec_name","")),str(audio.get("codec_name","")),bool(audio))
