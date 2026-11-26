# Architecture

## Contract & Validation
All pipeline stages read `storyboard.json` validated against `schema/storyboard.schema.json`. Changing one shot updates only that shot's input hash, avoiding full-film regeneration.

## Stages
1. **Script (`pipeline/script_stage.py`)**: Validates the storyboard and emits a structured summary.
2. **Keyframes (`pipeline/keyframes_stage.py`)**: Generates a character reference image and per-shot keyframes conditioned on character attributes and `style_block` via Cloudflare Workers AI (`FLUX.1 schnell` / `FLUX.2 klein`) with deterministic local fallback if offline.
3. **Moving Shots (`pipeline/shots_stage.py`)**: Generates motion clips via Wan 2.2 TI2V-5B endpoint when configured or smooth FFmpeg `zoompan` Ken Burns motion clips.
4. **Music (`pipeline/music_stage.py`)**: Generates an instrumental underscore via ACE-Step 1.5 endpoint when configured or a deterministic gentle acoustic score WAV.
5. **Narration (`pipeline/narration_stage.py`)**: Synthesizes per-shot Amharic (`am-ET`) narration via Gemini TTS (`GEMINI_API_KEY`) with deterministic cadence fallback.
6. **Assembly (`pipeline/assemble_stage.py`)**: Builds English SRT subtitles, formats `16:9` and `9:16` timelines, applies sidechain music ducking (`sidechaincompress`) and `-14 LUFS` normalization (`loudnorm`), appends the AI disclosure end card, and exports MP4s.

## Retries, Caching & Logging
* `retry_call` applies exponential backoff across transient network/API errors.
* `compute_cache_key` hashes stage name and relevant inputs into `outputs/.cache`.
* `log_run` appends structured JSON records to `runs.jsonl`.
