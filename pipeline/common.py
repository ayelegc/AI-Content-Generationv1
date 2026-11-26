import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict

try:
    import jsonschema
except ImportError:
    jsonschema = None


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "storyboard.schema.json"
STORYBOARD_PATH = REPO_ROOT / "storyboard.json"
RUNS_LOG_PATH = REPO_ROOT / "runs.jsonl"
CACHE_DIR = REPO_ROOT / "outputs" / ".cache"


def load_storyboard(path: Path = STORYBOARD_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    validate_storyboard(data)
    return data


def validate_storyboard(data: Dict[str, Any], schema_path: Path = SCHEMA_PATH) -> None:
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    if jsonschema is not None:
        jsonschema.validate(instance=data, schema=schema)
    else:
        required = schema.get("required", [])
        for key in required:
            if key not in data:
                raise ValueError(f"Storyboard missing required field: {key}")
        shots = data.get("shots", [])
        if not (8 <= len(shots) <= 12):
            raise ValueError(f"Storyboard must have 8-12 shots, got {len(shots)}")


def compute_cache_key(stage: str, payload: Dict[str, Any]) -> str:
    canonical = json.dumps({"stage": stage, "payload": payload}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def is_cached(cache_key: str, artifact_path: Path) -> bool:
    meta_path = CACHE_DIR / f"{cache_key}.json"
    return meta_path.exists() and artifact_path.exists()


def mark_cached(cache_key: str, artifact_path: Path, info: Dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta_path = CACHE_DIR / f"{cache_key}.json"
    record = {
        "cache_key": cache_key,
        "artifact_path": str(artifact_path.relative_to(REPO_ROOT)),
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "info": info,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)


def log_run(
    stage: str,
    model: str,
    params: Dict[str, Any],
    seed: int | None,
    latency_sec: float,
    cost_usd_est: float,
    status: str,
    cached: bool = False,
    notes: str = "",
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "model": model,
        "params": params,
        "seed": seed,
        "latency_sec": round(latency_sec, 3),
        "cost_usd_est": round(cost_usd_est, 6),
        "status": status,
        "cached": cached,
        "notes": notes,
    }
    with open(RUNS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def retry_call(fn: Callable[[], Any], max_attempts: int = 3, base_delay_sec: float = 1.5) -> Any:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts:
                sleep_for = base_delay_sec * (2 ** (attempt - 1))
                time.sleep(sleep_for)
    assert last_exc is not None
    raise last_exc
