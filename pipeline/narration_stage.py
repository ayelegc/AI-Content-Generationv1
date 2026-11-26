from pathlib import Path
from common import REPO_ROOT, compute_cache_key, is_cached, load_storyboard, log_run, mark_cached, retry_call
import base64
import json
import math
import os
import struct
import time
import urllib.request
import wave


def _write_paced_tone_wav(out_wav: Path, duration_sec: float, text: str) -> None:
    """Deterministic placeholder voice-cadence WAV when offline or no GEMINI_API_KEY is set."""
    sample_rate = 24000
    n_samples = max(1, int(sample_rate * duration_sec))
    syllables = max(4, len(text.split()) * 2)
    with wave.open(str(out_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            cadence = 0.5 + 0.5 * math.sin(2.0 * math.pi * (syllables / max(1.0, duration_sec)) * t)
            env = min(1.0, t / 0.15, max(0.0, (duration_sec - t) / 0.2))
            val = 0.04 * cadence * env * math.sin(2.0 * math.pi * 190.0 * t)
            sample = int(max(-32767, min(32767, val * 32767)))
            frames.extend(struct.pack("<h", sample))
        wf.writeframes(bytes(frames))


def _call_gemini_tts(api_key: str, text: str, voice_name: str = "Aoede", style_prompt: str = "calm, warm, unhurried documentary narrator") -> bytes | None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
    prompt_text = f"Say in a {style_prompt}: {text}"
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice_name}
                }
            },
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    for p in parts:
        inline = p.get("inlineData")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])
    return None


def run(storyboard_path: Path = REPO_ROOT / "storyboard.json", force: bool = False) -> list[Path]:
    sb = load_storyboard(storyboard_path)
    out_dir = REPO_ROOT / "outputs" / "narration"
    out_dir.mkdir(parents=True, exist_ok=True)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    voice_name = "Aoede"
    style_hint = "calm, warm, unhurried storytelling tone"
    files: list[Path] = []

    for shot in sb["shots"]:
        sid = shot["shot_id"]
        text_local = shot.get("narration_local", "")
        out_wav = out_dir / f"{sid}.wav"
        payload = {
            "shot_id": sid,
            "language": sb["language"],
            "text_local": text_local,
            "voice": voice_name,
            "style": style_hint,
        }
        key = compute_cache_key("narration", payload)
        t0 = time.perf_counter()

        if not force and is_cached(key, out_wav):
            log_run("narration", "gemini-3.8-flash-tts", {"shot_id": sid, "lang": sb["language"]}, None, time.perf_counter() - t0, 0.0, "ok", cached=True)
            files.append(out_wav)
            continue

        def _synth(txt=text_local, dur=shot["duration_sec"], dst=out_wav):
            if api_key and txt.strip():
                audio_bytes = _call_gemini_tts(api_key, txt, voice_name=voice_name, style_prompt=style_hint)
                if audio_bytes:
                    with open(dst, "wb") as f:
                        f.write(audio_bytes)
                    return "gemini-3.8-flash-tts"
            _write_paced_tone_wav(dst, dur, txt)
            return "tts-cadence-fallback"

        model_used = retry_call(_synth)
        mark_cached(key, out_wav, {"cache_key": key, "model_used": model_used})
        log_run(
            "narration",
            model_used,
            {"shot_id": sid, "language": sb["language"], "chars": len(text_local)},
            None,
            time.perf_counter() - t0,
            0.0,
            "ok",
            cached=False,
        )
        files.append(out_wav)

    return files


if __name__ == "__main__":
    run()
