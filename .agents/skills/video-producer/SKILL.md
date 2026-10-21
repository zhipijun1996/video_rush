---
name: video-producer
description: Produce, resume, render and validate narrated 1080p Mandarin videos from evidence-backed specs with FFmpeg, replaceable TTS, subtitles and phone delivery artifacts.
---

Read AGENTS.md and README. Announce first use. Run doctor, then `python -m video_rush produce --spec episodes/NAME.json --source GAME_PATH`. Default is 1920x1080, 16:9, 30fps, H.264/yuv420p + AAC/48k MP4, Chinese narration, 180–300 seconds. The ten stage states and input/output hashes permit retries; preserve failure logs, never fabricate completion or replace speech with silence. An unchanged valid cached output is reused.

Edge first: use inherited HTTPS proxy explicitly for aiohttp WebSockets; bounded timeout; preserve synthesis failure. Piper is a replacement via --tts piper --piper-model PATH, with reviewed model .json/license. Never silently download an unlicensed voice. Decode generated audio, measure waveform and duration. Nonzero waveform is not independent listening/ASR proof. Edge sentence boundary timings are real synthesis metadata; within-sentence phrase subdivisions and Piper fallback timing are estimates. At tempo changes scale timing together with audio.

Compose deterministic shots in FFmpeg: real normal-speed clip windows, still pan/zoom, aspect-preserving split comparisons, readable source labels and Chinese ASS captions. No fake gameplay loops. Normalise narration; optional --music requires --music-license and uses low gain/sidechain ducking. For ep001 use narration only; original game's raw mix is not copied into final audio. Make cover from the actual source images, clearly distinguish concept versus real game evidence. Do not use image synthesis to suggest an implemented feature.

Technical validation: entire-file decode, codecs, dimensions/FPS/duration, real TTS receipt and non-silent waveform, subtitle bounds, clipping, long black/freeze detection, declared still exemptions, source hashes and delivery manifest. Technical failure blocks Delivery. Content structural checks do not certify truth or taste. Produce phone-review.md for hook, matching, readability, repeated shots, factual limits, voice/listening and user acceptance; mark human/independent review unverified.

Deliver final.mp4, cover.png, script.md, storyboard.json, subtitles.ass, bilibili.md, sources.json, report.json plus state/logs. Media remains ignored by Git. For mobile delivery use the manually dispatched GitHub workflow/artifact if actually run; report exact URL/run state. No Bilibili upload. An unexecuted YAML file is not cloud success. Do not block local production waiting on deployment permissions or authentication; finish and report exact remaining steps.
