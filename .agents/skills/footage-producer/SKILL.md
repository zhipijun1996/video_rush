---
name: footage-producer
description: Discover, verify, collect or reconstruct truthful game footage from exact commits, reusing existing Godot recording and input drivers. Use for ShotSpec-to-media work and graphical-environment failures.
---

Read AGENTS.md. Announce first use. Investigate the source's `visual_director.py`, movie/input drivers, seeds, manifests, Web builds, Git media and CI artifacts before inventing tools. Read the actual script's arguments and limits. Never change the game source repo. `video_rush.footage.collect` extracts committed blobs; `record` creates a reduced disposable git archive under build/recordings and runs existing drivers.

ShotSpec is the `shots[]` entry in the episode JSON: source IDs, view type, offsets, required narration duration and source claims. AssetSpec needs id, repository-relative path, full commit, PR, kind, runtime_commit if different, license and truth. Archive commit and runtime producer commit are not interchangeable. Verify surrounding README/trace receipts and hashes. Original historical video stays original; a new old-version run is historical_reconstruction, explicitly labeled. Positioned captures prove appearance at a location, not traversal.

For recording: resolve full SHA; pin the project's engine URL/SHA; check version; run import in the archive. Investigate headless validation (no rendered visual proof), Mesa llvmpipe/software rendering, Xvfb, Godot MovieMaker and existing recorded artifacts. Use bounded timeouts, preserve stdout/stderr and failure receipts. Seeds and actual input route must be documented. Validate movie dimensions/FPS/decode and trace actions/health/epoch. Driver exit zero alone is not route completion, device performance or visual quality. A respawn invalidates uninterrupted-route claims.

Use existing modules for movement/jump/recoil/grapple; do not fake frames, move the player by transform and claim natural traversal, or synthesize a feature that does not exist. Historical before/after may have incompatible seeds; label differing stages. When rebuilding fails, preserve the error and use genuine saved screenshots/records with explanatory motion. Never silently replace with generic AI game footage.

Export exact SHA/blob/SHA256/URL and provenance to sources.json. Verify available source licenses. Reuse project-owned assets authorized by the user; identify third-party licenses and unknown AI-provider terms accurately. No unlicensed external game/Bilibili clips. Capture system/environment evidence separately from artistic claims.
