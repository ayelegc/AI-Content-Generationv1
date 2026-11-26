# Failures & Workarounds

* **Missing API Keys / Offline Execution:** When `GEMINI_API_KEY`, `CLOUDFLARE_API_TOKEN`, `WAN22_ENDPOINT_URL`, or `ACESTEP_ENDPOINT_URL` are unset or unreachable, stages fall back cleanly to deterministic local media generation so `make film` still completes end-to-end.
* **GPU Queue / Quota Constraints on Video Models:** Wan 2.2 image-to-video can face queue delays or memory limits; `shots_stage.py` supports targeted `use_video: false` shots and FFmpeg motion fallback so no shot blocks assembly.
* **Subtitles / Text Inside Generated Images:** Image models can garble text; `style_block` explicitly requests no text/watermarks and subtitles/end-card text are rendered programmatically in FFmpeg.
