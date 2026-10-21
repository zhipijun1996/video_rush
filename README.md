# Video Rush

可追溯的 AI 游戏开发视频生产系统。独立于游戏仓库，游戏源码只读。首期已经在 Codex Cloud **实际生产**；技术数据和云端运行状态见 [实施记录](docs/implementation.md)。默认 1920×1080 / 30fps / H.264 + AAC，中文AI配音，手机兼容 MP4。

## 手机使用

首期：[直接下载成片Artifact](https://github.com/zhipijun1996/video_rush/actions/runs/39580103766/artifacts/12336770405) · [成功运行记录](https://github.com/zhipijun1996/video_rush/actions/runs/39580103766)（初始实现提交；完整补充许可见当前仓库rights.json）。

1. 在 Codex 中说：**“用 Video Rush 制作一期关于……的视频”**，或指定 PR / 日期 / 故事 ID。Codex 按四个 Skills 研究和编写分镜，再运行生产命令。无需用户剪辑或改 JSON。
2. 首期及已经提交的分镜可直接在 GitHub → **Actions → Produce Video Rush episode → Run workflow** 启动。完成后打开该次运行 → **Artifacts → video-rush-ep001**，下载 ZIP，解压 `final.mp4`、`cover.png`。移动浏览器看不到入口时切换桌面版网页；登录同一 GitHub 账号。
3. 看完 `phone-review.md` 的清单后，通过 B站手机端手动上传。系统不自动发布。Artifact 保留14天，过期可重跑；不是永久视频托管。

**边界：** 无已编写分镜的新主题会生成 `director-brief.json`，退出码3，等待当前 Codex 宿主继续创作。Python/Actions 没有隐藏的模型凭据，不能凭空创作所有新主题。不要把这个创作交接状态当成完成。手机用户把主题交给 Codex 即可，Codex 应继续处理，而不是让用户手工编写 JSON。

## 本地启动

系统依赖：Python ≥3.11、Git、FFmpeg/ffprobe（含 libx264/libass）、Noto CJK字体。历史扫描另需 `gh`，公开仓库可降级匿名API。游戏录制另需对应 Godot、Mesa及Xvfb；**已有真实素材的合成不需要Godot**。

```bash
python -m pip install -e '.[test]'
python -m video_rush doctor
python -m video_rush produce --source /workspace/gunman-rush \
  --topic 'AI生成的概念图为什么无法直接变成好看的游戏'
pytest -q
```

默认使用已编写的首期方案。`--source` 指向游戏本地检出；若不存在，CLI会克隆到该位置。不会在游戏工作区导入或运行Godot。不要把 `--source` 指向 Video Rush 本身。

```bash
# 全历史扫描；不refresh时冻结已有Git引用和PR详情缓存
python -m video_rush research --source /workspace/gunman-rush
# 明确更新远端历史（只fetch，不改游戏源码/当前检出）
python -m video_rush research --source /workspace/gunman-rush --refresh
# 已编写新一期：完整生产与失败恢复使用同一条命令
python -m video_rush produce --spec episodes/ep002.json --source /workspace/gunman-rush
# 提交给当前Codex宿主的创作选择器
python -m video_rush produce --pr 90
python -m video_rush produce --story S090
python -m video_rush produce --commits SHA1..SHA2
python -m video_rush produce --since 2026-10-17 --until 2026-10-19
# 独立重验成片；非零退出代表失败
python -m video_rush validate build/episodes/ep001
```

`--topic/--pr/--story/--commits/--since/--until` 选择研究任务；`--spec` 是最终编排入口，提供时以该分镜为准，不会静默改写分镜内容。下一期的自然语言入口由 Codex + Skills 实现，确定性CLI不伪装LLM。

## 四个 Skills 与代码

| 部件 | 职责 |
| --- | --- |
| [.agents/skills/history-researcher](.agents/skills/history-researcher/SKILL.md) | main/分支/PR/失败链研究和结构化故事库 |
| [.agents/skills/video-director](.agents/skills/video-director/SKILL.md) | 自然中文故事、分镜、证据与观点边界 |
| [.agents/skills/footage-producer](.agents/skills/footage-producer/SKILL.md) | 真素材提取、旧源码重建、复用原录制驱动 |
| [.agents/skills/video-producer](.agents/skills/video-producer/SKILL.md) | TTS、时间轴、FFmpeg、封面、验收与交付 |
| `video_rush/history.py` | 全引用Git索引；分页PR文件/讨论；3000文件上限披露 |
| `video_rush/footage.py` | Git blob提取/损坏缓存修复，隔离archive录制 |
| `video_rush/narration.py` | Edge/Piper、代理、真实波形校验、边界时间 |
| `video_rush/render.py` | 视频窗口、静图运镜、分屏、比较图重排、ASS、封面 |
| `video_rush/pipeline.py` | 十阶段状态、输入/输出SHA缓存、重试、配乐压低 |
| `video_rush/quality.py` | 全片解码、格式/音量/字幕/黑屏/静帧/来源验收 |
| `research/` | 27个候选故事、543提交主扫描与3提交补充、扫描范围、权利记录；非媒体 |
| `episodes/` | 可复用的脚本与AssetSpec，完整SHA，不提交素材 |
| `tests/` | 失败恢复、篡改缓存、只读素材、字幕和缺镜头负例 |

## 十阶段产物和缓存

Research → Story → Script → Shot Planning → Footage Collection → Narration → Timeline Composition → Rendering → Quality Validation → Delivery。

`state.json` 记录每阶段 running/complete/failed、错误、输入hash和输出hash。有效文件且输入不变则跳过；中途失败原命令重跑。每段配音、每个镜头另有缓存，内容或SHA变化才重新生成。更换渲染实现会使镜头缓存失效。不要编辑缓存的素材充当源证据；损坏的blob会从Git修复。

每期目录 `build/episodes/ep001/`：`final.mp4`、`cover.png`、`script.md`、`storyboard.json`、`subtitles.ass`、`bilibili.md`、`sources.json`、`report.json`；另有 `phone-review.md`、`delivery.json`、`state.json`、素材/配音缓存和日志。所有媒体及API原始转储均被Git忽略。

## 配音、音轨和版权

Edge为首选。aiohttp WebSocket显式使用继承的 `HTTPS_PROXY`；默认直连可能在云端失败。每次合成有超时与失败JSON，不会生成静音占位。首期用Xiaoxiao，先生成真实音频，再按1.18倍保音高调整节奏；字幕时间同步缩放。Edge句子边界来自实际TTS，句内短字幕按字符比例细分，不能称为逐字强制对齐。

```bash
# Edge不可用时先准备具有明确许可的中文Piper模型和同名 .onnx.json
python -m video_rush produce --spec episodes/ep001.json \
  --tts piper --piper-model /path/to/licensed-zh-model.onnx
# 可选配乐必须声明许可，自动低音量并随口播压低
python -m video_rush produce --spec episodes/ep001.json \
  --music /path/to/music.wav --music-license 'CC0; author; source URL'
```

Piper代码路径已实现，未在本轮下载模型或冒称其声音已经验证。模型许可需随具体模型审查。Edge属于免费可访问服务，不是离线开源引擎或可保证可用的服务。首期不用第三方BGM，不保留游戏音轨，避免不必要的音乐许可混用。

素材授权依据为用户本人项目制作请求。Underworld是Asouris的自定义宽松声明，**不是CC0**；Noto CJK为SIL OFL。AI素材的原始供应商商业条款未独立披露，不臆造“全部可商用”。见 `research/rights.json` 和成品 `sources.json`。

## 真实性与验收

来源Manifest区分AI母版、合屏预览、技术样板、历史原片、定位截图及之后重新录制。存档提交SHA与原片运行源SHA分别保存。不同阶段对照不自动等于同种子实验。游戏源本轮未改。

技术通过只证明：文件可解码、1080p/30fps/H.264/AAC、时长范围、有真实TTS音频、字幕不越界、无明显削波/长黑屏/意外长静帧，来源文件hash匹配。波形非零不等于独立语音识别通过。内容只做结构检查；完整事实独审、手机试听、审美与最终用户认可都不能自动代签。`phone-review.md` 保持待审核。

## Actions与资源

手动workflow按AssetSpec的完整SHA执行浅层、延迟blob拉取，不下载8GB全历史。历史研究在Codex/本地完成；Actions复现固定分镜和素材。50分钟上限，14天Artifact保留，失败也上传现有报告/日志。需要Actions允许运行且仓库公开可读取素材；私有来源另需配置授权，默认只读GITHUB_TOKEN不能假定跨私库可用。

实际云端执行状态与精确链接见 [实施记录](docs/implementation.md)。未运行的workflow不作为成功证据。工具/缓存/TTS服务可能失败，失败会阻止交付并留下可恢复状态。
