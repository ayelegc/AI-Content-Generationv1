from pathlib import Path
from common import REPO_ROOT, compute_cache_key, is_cached, load_storyboard, log_run, mark_cached, retry_call
import math
import os
import struct
import subprocess
import time
import urllib.request
import json
import wave


def _write_gentle_score_wav(out_wav: Path, duration_sec: float, tempo_bpm: int = 74) -> None:
    sample_rate = 24000
    n_samples = int(sample_rate * duration_sec)
    beat_sec = 60.0 / max(40, tempo_bpm)
    # Warm D minor / F major gentle progression frequencies
    freqs = [146.83, 174.61, 220.00, 196.00]
    with wave.open(str(out_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            bar_idx = int(t / (beat_sec * 4)) % len(freqs)
            f0 = freqs[bar_idx]
            env = 0.5 * (1.0 - math.cos(2.0 * math.pi * min(1.0, (t % (beat_sec * 4)) / (beat_sec * 4))))
            fade = min(1.0, t / 1.5, max(0.0, (duration_sec - t) / 2.0))
            val = 0.06 * env * fade * (0.7 * math.sin(2.0 * math.pi * f0 * t) + 0.3 * math.sin(2.0 * math.pi * (f0 * 1.5) * t))
            sample = int(max(-32767, min(32767, val * 32767)))
            frames.extend(struct.pack("<h", sample))
        wf.writeframes(bytes(frames))


def run(storyboard_path: Path = REPO_ROOT / "storyboard.json", force: bool = False) -> Path:
    sb = load_storyboard(storyboard_path)
    out_dir = REPO_ROOT / "outputs" / "music"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_wav = out_dir / "score.wav"
    endpoint = os.getenv("ACESTEP_ENDPOINT_URL", "").strip()

    total_dur = max(1.0, sum(s["duration_sec"] for s in sb["shots"]))
    cues = sb.get("music_cues", [])
    primary_cue = cues[0] if cues else {"caption": "gentle acoustic underscore", "tempo_bpm": 74, "key": "D minor", "seed": 3001}

    payload = {
        "total_duration_sec": total_dur,
        "cues": cues,
        "endpoint": endpoint or "procedural-score-fallback",
    }
    key = compute_cache_key("music", payload)
    t0 = time.perf_counter()

    if not force and is_cached(key, out_wav):
        log_run("music", "ace-step-1.5/score-synth", {"duration_sec": total_dur}, primary_cue.get("seed"), time.perf_counter() - t0, 0.0, "ok", cached=True)
        return out_wav

    def _gen_music():
        if endpoint:
            body = json.dumps({
                "caption": primary_cue.get("caption", ""),
                "tempo_bpm": primary_cue.get("tempo_bpm", 74),
                "key": primary_cue.get("key", "D minor"),
                "duration_sec": total_dur,
                "seed": primary_cue.get("seed", 3001),
                "instrumental": primary_cue.get("instrumental", True),
            }).encode("utf-8")
            req = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                import base64
                if data.get("audio_base64"):
                    with open(out_wav, "wb") as f:
                        f.write(base64.b64decode(data["audio_base64"]))
                    return "ace-step-1.5"
        _write_gentle_score_wav(out_wav, total_dur, tempo_bpm=primary_cue.get("tempo_bpm", 74))
        return "procedural-underscore-fallback"

    model_used = retry_call(_gen_music)
    mark_cached(key, out_wav, {"cache_key": key, "model_used": model_used})
    log_run(
        "music",
        model_used,
        {"duration_sec": total_dur, "tempo_bpm": primary_cue.get("tempo_bpm", 74)},
        primary_cue.get("seed"),
        time.perf_counter() - t0,
        0.0,
        "ok",
        cached=False,
    )
    return out_wav


if __name__ == "__main__":
    run()
