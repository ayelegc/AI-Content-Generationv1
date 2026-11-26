# Costs, Latency & Quota Notes

* **Zero-Cost Stack:** Designed for free tiers and open/local tools (`GEMINI_API_KEY`, Cloudflare Workers AI free allowance, Kaggle/Colab GPU quotas, and FFmpeg).
* **Telemetry:** Every stage execution appends latency (`latency_sec`), seed, parameters, cache status, and estimated cost (`cost_usd_est`) to `runs.jsonl`.
