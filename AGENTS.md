# Video Rush

Video Rush owns production code, stories, skills and edit rules. `gunman-rush` is an external **read-only** source. Never edit, import inside, checkout, reset, commit or push that source repo. Run old game versions only in `build/recordings/` archives. User instructions override these local defaults.

For natural language video requests, invoke the four local skills in sequence. The Codex host does research/creative direction; the Python CLI performs deterministic synthesis/rendering. An unknown topic producing a director brief is not a finished video. Continue authoring its JSON specs yourself, then run produce; do not ask the phone-only user to edit JSON.

- `.agents/skills/history-researcher/SKILL.md`
- `.agents/skills/video-director/SKILL.md`
- `.agents/skills/footage-producer/SKILL.md`
- `.agents/skills/video-producer/SKILL.md`

Use full SHA + repository-relative asset path + blob/hash. Distinguish original recording, later historical reconstruction, positioned screenshot, preview, concept art and explanatory diagram. Same-seed claims require evidence of equal seed/recipe/version. Never synthesize gameplay or fabricate voice, execution, user feedback or independent review. Preserve technical/experience/art/rights statuses separately.

Keep media, API dumps and logs in ignored `build/`; commit authored specs, curated story index, rights notes and concise verification summaries. On failures preserve state/logs, fix the real cause, resume cached stages. No upload to Bilibili. The user explicitly authorized direct GitHub Prerelease delivery for all subsequent episodes (2026-10-21). Use local rendering -> validation -> commit/push -> prerelease; do not use Actions/Artifact as the normal delivery route. Do not create a stable Release or overwrite existing published media. See docs/editorial-style.md for the entertainment-first pacing, original memes and restrained self-deprecating humor.

Run `pytest` and real end-to-end production for pipeline changes. `python -m video_rush validate <episode dir>` is technical verification; phone review remains pending. Avoid claiming an unexecuted workflow works remotely. Do not spawn other agents unless the user explicitly requests delegation.

Every prerelease must include final.mp4, cover.png, standalone bilibili.md with title and description, and a complete delivery ZIP; show submission copy in release notes. Missing mandatory files blocks publication.

User exception (2026-10-21): GitHub Release uploads remained unauthorized; the user now explicitly requested Actions download for the current episode. Use deliver-existing.yml and tools/deliver_actions.py to preserve the existing video/BGM bytes as an Artifact. This exception authorizes Actions delivery; do not ask for Release credentials before proceeding.
