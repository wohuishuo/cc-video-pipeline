from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"localization"
sys.path.insert(0,str(APP))

from .helpers import manifests  # noqa: E402
from localization_app.contracts import load_composition_inputs  # noqa: E402
from localization_app.ffmpeg import FfmpegCompositionAdapter, ProbeResult, build_ffmpeg_argv  # noqa: E402


def test_builder_delays_voice_fits_overlong_clip_mixes_bed_and_burns_subtitles(tmp_path):
    job=load_composition_inputs(*manifests(tmp_path)).jobs[0]
    output=tmp_path/"localized.mp4"
    argv=build_ffmpeg_argv(job,output,source_has_audio=True,source_volume=0.12)
    graph=argv[argv.index("-filter_complex")+1]
    assert argv[:4]==["ffmpeg","-hide_banner","-loglevel","error"]
    assert argv.count("-i")==3
    assert "[1:a]adelay=0|0[v0]" in graph
    assert "[2:a]atempo=2.000000,atempo=1.250000,adelay=3000|3000[v1]" in graph
    assert "[0:a]volume=0.120000[bed]" in graph
    assert "[bed][voice]amix=inputs=2:normalize=0:duration=longest[aout]" in graph
    assert "subtitles='" in graph and "force_style='FontName=Arial" in graph
    assert argv[argv.index("-c:v")+1]=="libx264"
    assert argv[argv.index("-pix_fmt")+1]=="yuv420p"
    assert argv[argv.index("-c:a")+1]=="aac"
    assert argv[argv.index("-b:a")+1]=="192k"
    assert argv[-1]==str(output)


def test_builder_uses_voice_only_when_source_has_no_audio(tmp_path):
    job=load_composition_inputs(*manifests(tmp_path)).jobs[0]
    argv=build_ffmpeg_argv(job,tmp_path/"out.mp4",source_has_audio=False,source_volume=0.12)
    graph=argv[argv.index("-filter_complex")+1]
    assert "[0:a]" not in graph
    assert "[voice]anull[aout]" in graph


def test_adapter_publishes_only_probe_verified_output(tmp_path):
    job=load_composition_inputs(*manifests(tmp_path)).jobs[0]
    output=tmp_path/"out.mp4"; calls=[]
    expected=ProbeResult(4.2,320,240,"h264","aac",True)
    def runner(argv):
        calls.append(argv); Path(argv[-1]).write_bytes(b"mp4")
    adapter=FfmpegCompositionAdapter(command_runner=runner,source_probe=lambda _:True,output_probe=lambda _:expected)
    result=adapter.compose(job,output,lambda _message:None,source_volume=0.12)
    assert result==expected
    assert output.read_bytes()==b"mp4"
    assert len(calls)==1
