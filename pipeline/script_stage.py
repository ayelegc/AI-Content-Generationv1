from pathlib import Path
from common import REPO_ROOT, compute_cache_key, is_cached, load_storyboard, log_run, mark_cached, retry_call
import json
import time


def run(storyboard_path: Path = REPO_ROOT / "storyboard.json", force: bool = False) -> Path:
    t0 = time.perf_counter()
    sb = load_storyboard(storyboard_path)
    out_dir = REPO_ROOT / "outputs" / "script"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "validated_script.json"

    payload = {
        "title": sb["title"],
        "language": sb["language"],
        "shots": [
            {
                "shot_id": s["shot_id"],
                "duration_sec": s["duration_sec"],
                "narration_local": s["narration_local"],
                "narration_en": s["narration_en"],
            }
            for s in sb["shots"]
        ],
    }
    key = compute_cache_key("script", payload)
    if not force and is_cached(key, out_file):
        log_run("script", "schema-validator", {"shots": len(sb["shots"])}, None, time.perf_counter() - t0, 0.0, "ok", cached=True)
        return out_file

    def _build():
        total_dur = sum(s["duration_sec"] for s in sb["shots"])
        word_count_en = sum(len(s["narration_en"].split()) for s in sb["shots"])
        doc = {
            "title": sb["title"],
            "logline": sb.get("logline", ""),
            "language": sb["language"],
            "total_shots": len(sb["shots"]),
            "total_duration_sec": total_dur,
            "english_word_count": word_count_en,
            "shots": payload["shots"],
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
        return doc

    retry_call(_build)
    mark_cached(key, out_file, {"cache_key": key})
    log_run("script", "schema-validator", {"shots": len(sb["shots"])}, None, time.perf_counter() - t0, 0.0, "ok", cached=False)
    return out_file


if __name__ == "__main__":
    run()
