# Design Thinking & Audience Tests

## Audience & Intent
* **Target Audience:** Extended family members and diaspora relatives who connect over shared Ethiopian family histories and moral proverbs.
* **Viewing Context:** Mobile phones (`9:16` vertical) and family screens (`16:9` horizontal), with English subtitles for cross-generational comprehension.
* **Intended Feeling:** Warmth, quiet reverence, and grounded connection to family memory and patience.

## Prototype 1: Radio Cut (Narration + Score Sketch)
* **Tested With:** 3 family/peer reviewers.
* **Key Feedback:** Shot 7's proverb landed emotionally, while early shots felt slightly rushed when read aloud.
* **Storyboard Changes:** Adjusted shot durations in `storyboard.json` so narration breathes naturally and added a clear closing beat (`shot_10`) before the AI end card.

## Prototype 2: Near-Final Cut (Visuals + Subtitles + Ducking)
* **Tested With:** 3 reviewers checking pacing, subtitle readability, and voice-over clarity.
* **Key Feedback:** Keep subtitles concise (up to two lines, ~40 chars) and ensure music stays unobtrusive under spoken Amharic narration.
* **Storyboard Changes:** Refined `narration_en` line lengths for crisp two-line SRT wrapping and kept `music_cues` gentle and instrumental.
