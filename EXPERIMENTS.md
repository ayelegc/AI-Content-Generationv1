# Experiments Log

| # | Hypothesis | Change | Result | Decision |
|---|---|---|---|---|
| 1 | Fixed character description + style block reduces visual drift across shots | Prepended `character_reference.description` and `style_block` to every shot keyframe prompt | More uniform lighting and attire across shots | Keep fixed style & character block |
| 2 | Per-shot narration files simplify re-takes | Generated one `.wav` per `shot_id` instead of a single monolithic audio track | Editing one line no longer invalidates unrelated shots | Keep per-shot narration files |
| 3 | Sidechain ducking preserves voice clarity over score | Used `sidechaincompress` (`threshold=0.02`, `ratio=6`, `attack=300`, `release=1500`) | Narration remained clear while underscore stayed present in pauses | Keep sidechain ducking parameters |
| 4 | Short captions (<=40 chars/line, max 2 lines) improve mobile legibility | Wrapped English SRT lines at 40 characters up to 2 lines | Cleaner framing on `9:16` vertical exports | Keep 40-char / 2-line cap |
| 5 | Deterministic seed per shot enables fair prompt comparisons | Assigned explicit `seed` per shot in `storyboard.json` | Re-runs with unchanged inputs hit cache deterministically | Keep explicit seeds in contract |
