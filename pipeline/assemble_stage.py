from pathlib import Path
from common import REPO_ROOT, compute_cache_key, is_cached, load_storyboard, log_run, mark_cached, retry_call
import shutil
import subprocess
import time


def _format_srt_time(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    hrs = ms // 3600000
    ms %= 3600000
    mins = ms // 60000
    ms %= 60000
    secs = ms // 1000
    rem_ms = ms % 1000
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{rem_ms:03d}"


def _wrap_subtitle(text: str, max_chars: int = 40) -> str:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        candidate = f"{cur} {w}".strip()
        if len(candidate) <= max_chars:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = w
        if len(lines) == 2:
            break
    if cur and len(lines) < 2:
        lines.append(cur)
    return "\n".join(lines[:2])


def write_subtitles_srt(sb: dict, srt_path: Path) -> None:
    cursor = 0.0
    blocks: list[str] = []
    for idx, shot in enumerate(sb["shots"], start=1):
        start = cursor
        end = cursor + float(shot["duration_sec"])
        cursor = end
        sub_text = _wrap_subtitle(shot.get("narration_en", ""), max_chars=40)
        blocks.append(f"{idx}\n{_format_srt_time(start)} --> {_format_srt_time(end)}\n{sub_text}\n")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _build_aspect_export(
    sb: dict,
    aspect: str,
    srt_path: Path,
    score_wav: Path,
    out_mp4: Path,
    work_dir: Path,
) -> None:
    if aspect == "16:9":
        w, h = 1280, 720
        crop_vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,fps=24,format=yuv420p"
    else:
        w, h = 720, 1280
        crop_vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=24,format=yuv420p"

    # Normalize each shot to exact aspect and concat
    norm_clips: list[Path] = []
    for shot in sb["shots"]:
        sid = shot["shot_id"]
        src_clip = REPO_ROOT / "outputs" / "shots" / f"{sid}.mp4"
        dst_clip = work_dir / f"{aspect.replace(':', 'x')}_{sid}.mp4"
        if _has_ffmpeg() and src_clip.exists():
            cmd = [
                "ffmpeg", "-y", "-i", str(src_clip),
                "-t", f"{float(shot['duration_sec']):.2f}",
                "-vf", crop_vf,
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(dst_clip),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0 and dst_clip.exists():
                norm_clips.append(dst_clip)
                continue
        if src_clip.exists():
            shutil.copyfile(src_clip, dst_clip)
            norm_clips.append(dst_clip)

    # End card (3 seconds, explicit AI disclosure)
    end_card_clip = work_dir / f"{aspect.replace(':', 'x')}_endcard.mp4"
    if _has_ffmpeg():
        draw_cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=#141414:s={w}x{h}:d=3:r=24",
            "-vf", (
                f"drawtext=text='Made with AI — Heritage Short Pipeline':"
                f"fontcolor=white:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2-20,"
                f"drawtext=text='Narration: Gemini TTS | Visuals & Score: Open & Hosted AI':"
                f"fontcolor=#CCCCCC:fontsize=18:x=(w-text_w)/2:y=(h-text_h)/2+24,"
                f"format=yuv420p"
            ),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(end_card_clip),
        ]
        r_ec = subprocess.run(draw_cmd, capture_output=True, text=True)
        if r_ec.returncode != 0:
            shutil.copyfile(norm_clips[-1], end_card_clip)
    else:
        shutil.copyfile(norm_clips[-1], end_card_clip)

    all_clips = norm_clips + [end_card_clip]
    concat_list = work_dir / f"concat_{aspect.replace(':', 'x')}.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for c in all_clips:
            f.write(f"file '{c.resolve()}'\n")

    concat_video = work_dir / f"body_{aspect.replace(':', 'x')}.mp4"
    if _has_ffmpeg():
        cmd_concat = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(concat_video),
        ]
        subprocess.run(cmd_concat, capture_output=True, text=True)

    # Combine narration segments in order
    nar_concat_list = work_dir / "nar_concat.txt"
    nar_combined = work_dir / "narration_full.wav"
    nar_files = [REPO_ROOT / "outputs" / "narration" / f"{s['shot_id']}.wav" for s in sb["shots"] if (REPO_ROOT / "outputs" / "narration" / f"{s['shot_id']}.wav").exists()]
    if _has_ffmpeg() and nar_files:
        with open(nar_concat_list, "w", encoding="utf-8") as f:
            for nf in nar_files:
                f.write(f"file '{nf.resolve()}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(nar_concat_list), "-c:a", "pcm_s16le", str(nar_combined)],
            capture_output=True,
            text=True,
        )

    # Mix score with sidechain ducking under narration + loudness normalization (-14 LUFS target)
    mixed_audio = work_dir / f"mix_{aspect.replace(':', 'x')}.aac"
    if _has_ffmpeg() and score_wav.exists() and nar_combined.exists():
        filter_complex = (
            "[1:a]volume=0.35[mus];"
            "[0:a]asplit=2[sc][voice];"
            "[mus][sc]sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500[ducked];"
            "[voice][ducked]amix=inputs=2:duration=first:weights=1.2 1.0,"
            "loudnorm=I=-14:TP=-1.0:LRA=11[aout]"
        )
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(nar_combined),
                "-i", str(score_wav),
                "-filter_complex", filter_complex,
                "-map", "[aout]",
                "-c:a", "aac", "-b:a", "192k",
                str(mixed_audio),
            ],
            capture_output=True,
            text=True,
        )

    if _has_ffmpeg() and concat_video.exists():
        sub_escaped = str(srt_path.resolve()).replace(":", "\\:")
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", str(concat_video),
        ]
        if mixed_audio.exists():
            mux_cmd.extend(["-i", str(mixed_audio)])
        mux_cmd.extend([
            "-vf", f"subtitles='{sub_escaped}'",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
        ])
        if mixed_audio.exists():
            mux_cmd.extend(["-c:a", "aac", "-shortest"])
        mux_cmd.append(str(out_mp4))
        res_mux = subprocess.run(mux_cmd, capture_output=True, text=True)
        if res_mux.returncode == 0 and out_mp4.exists():
            return

    # Fallback if ffmpeg is not installed in environment
    if concat_video.exists():
        shutil.copyfile(concat_video, out_mp4)
    elif norm_clips:
        shutil.copyfile(norm_clips[0], out_mp4)


def run(storyboard_path: Path = REPO_ROOT / "storyboard.json", force: bool = False) -> list[Path]:
    sb = load_storyboard(storyboard_path)
    out_dir = REPO_ROOT / "outputs" / "final"
    work_dir = out_dir / "_work"
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    srt_path = out_dir / "subtitles_en.srt"
    write_subtitles_srt(sb, srt_path)

    score_wav = REPO_ROOT / "outputs" / "music" / "score.wav"
    exported: list[Path] = []

    for aspect in sb.get("aspect_ratios", ["16:9", "9:16"]):
        tag = aspect.replace(":", "x")
        out_mp4 = out_dir / f"heritage_short_{tag}.mp4"
        payload = {
            "aspect": aspect,
            "shots": sb["shots"],
            "music_cues": sb.get("music_cues", []),
            "srt_text": srt_path.read_text(encoding="utf-8"),
        }
        key = compute_cache_key(f"assemble_{tag}", payload)
        t0 = time.perf_counter()

        if not force and is_cached(key, out_mp4):
            log_run("assemble", "ffmpeg-pipeline", {"aspect": aspect}, None, time.perf_counter() - t0, 0.0, "ok", cached=True)
            exported.append(out_mp4)
            continue

        retry_call(lambda asp=aspect, dst=out_mp4: _build_aspect_export(sb, asp, srt_path, score_wav, dst, work_dir))
        mark_cached(key, out_mp4, {"cache_key": key, "aspect": aspect})
        log_run("assemble", "ffmpeg-pipeline", {"aspect": aspect, "loudness_target": "-14 LUFS"}, None, time.perf_counter() - t0, 0.0, "ok", cached=False)
        exported.append(out_mp4)

    return exported


if __name__ == "__main__":
    run()
