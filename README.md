<<<<<<< HEAD
# AI-Content-Generationv1
=======
# Heritage Short Pipeline (`make film`)

A reproducible, multi-model AI short-film pipeline built around a single validated contract (`storyboard.json` + `schema/storyboard.schema.json`).

## Quick Start (One Command)

```bash
cp .env.example .env
make film
```

To regenerate only a modified shot, edit its prompt, duration, seed, or narration in `storyboard.json` and run `make film` again—input-hash caching (`outputs/.cache`) skips unchanged artifacts and logs every call to `runs.jsonl`.

## Repository Layout

* `storyboard.json` — Contract defining 10 shots (~72s total), Amharic narration (`am-ET`), English subtitles, camera/motion prompts, and score cues.
* `schema/storyboard.schema.json` — JSON Schema validated before any stage runs.
* `pipeline/` — Stage scripts (`script_stage.py`, `keyframes_stage.py`, `shots_stage.py`, `music_stage.py`, `narration_stage.py`, `assemble_stage.py`), shared caching/retry/logging utilities (`common.py`), and CLI entrypoint (`run_pipeline.py`).
* `runs.jsonl` — Append-only execution log recording model, parameters, seed, latency, estimated cost, and cache hits.
* `outputs/` — Stage artifacts, SRT subtitles, and dual-aspect exports (`16:9` and `9:16`) with sidechain ducking, `-14 LUFS` target normalization, and an explicit AI end card.
* `DESIGN.md`, `ARCHITECTURE.md`, `EXPERIMENTS.md`, `FAILURES.md`, `COSTS.md`, `ETHICS.md` — Engineering and design documentation.
>>>>>>> fa4f1bd (Initial project commit)
