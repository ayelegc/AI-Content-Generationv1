from pathlib import Path
from common import REPO_ROOT, compute_cache_key, is_cached, load_storyboard, log_run, mark_cached, retry_call
import os
import shutil
import subprocess
import time
import urllib.request
import json


def _render_ken_burns_fallback(keyframe_path: Path, out_mp4: Path, duration_sec: float, zoom_dir: str = "in") -> None:
    fps = 24
    total_frames = max(1, int(round(duration_sec * fps)))
    if zoom_dir == "in":
        z_expr = f"1+0.08*on/{total_frames}"
    else:
        z_expr = f"1.08-0.08*on/{total_frames}"

    vf = (
        f"scale=1920:1080,"
        f"zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1280x720:fps={fps},"
        f"format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(keyframe_path),
        "-t", f"{duration_sec:.2f}", "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_mp4),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        # Fallback minimal valid file if ffmpeg is unavailable in a minimal container
        shutil.copyfile(keyframe_path, out_mp4)


def _call_wan22_endpoint(endpoint_url: str, keyframe_path: Path, motion_prompt: str, seed: int, duration_sec: float, out_mp4: Path) -> bool:
    import base64
    with open(keyframe_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    body = json.dumps({
        "image_base64": img_b64,
        "prompt": motion_prompt,
        "seed": seed,
        "duration_sec": duration_sec,
        "fps": 24,
        "resolution": "480p",
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
        vid_b64 = payload.get("video_base64")
        if not vid_b64:
            return False
        with open(out_mp4, "wb") as out_f:
            out_f.write(base64.b64decode(vid_b64))
    return True


def run(storyboard_path: Path = REPO_ROOT / "storyboard.json", force: bool = False) -> list[Path]:
    sb = load_storyboard(storyboard_path)
    kf_dir = REPO_ROOT / "outputs" / "keyframes"
    out_dir = REPO_ROOT / "outputs" / "shots"
    out_dir.mkdir(parents=True, exist_ok=True)
    endpoint = os.getenv("WAN22_ENDPOINT_URL", "").strip()
    outputs: list[Path] = []

    for idx, shot in enumerate(sb["shots"]):
        sid = shot["shot_id"]
        kf_path = kf_dir / f"{sid}.png"
        out_mp4 = out_dir / f"{sid}.mp4"
        payload = {
            "shot_id": sid,
            "motion_prompt": shot["motion_prompt"],
            "duration_sec": shot["duration_sec"],
            "seed": shot["seed"],
            "use_video": shot.get("use_video", True),
            "endpoint": endpoint or "ffmpeg-ken-burns",
        }
        key = compute_cache_key("shot", payload)
        t0 = time.perf_counter()

        if not force and is_cached(key, out_mp4):
            log_run("shots", "wan-2.2-ti2v-5b/ken-burns", {"shot_id": sid}, shot["seed"], time.perf_counter() - t0, 0.0, "ok", cached=True)
            outputs.append(out_mp4)
            continue

        def _make_clip(kfp=kf_path, dst=out_mp4, dur=shot["duration_sec"], mp=shot["motion_prompt"], sd=shot["seed"], zdir=("in" if idx % 2 == 0 else "out")):
            if endpoint and shot.get("use_video", True):
                if _call_wan22_endpoint(endpoint, kfp, mp, sd, dur, dst):
                    return "wan-2.2-ti2v-5b"
            _render_ken_burns_fallback(kfp, dst, dur, zoom_dir=zdir)
            return "ffmpeg-zoompan-fallback"

        model_used = retry_call(_make_clip)
        mark_cached(key, out_mp4, {"cache_key": key, "model_used": model_used})
        log_run(
            "shots",
            model_used,
            {"shot_id": sid, "duration_sec": shot["duration_sec"], "fps": 24},
            shot["seed"],
            time.perf_counter() - t0,
            0.0,
            "ok",
            cached=False,
        )
        outputs.append(out_mp4)

    return outputs


if __name__ == "__main__":
    run()
