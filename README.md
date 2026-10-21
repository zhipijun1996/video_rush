# Video Rush

可追溯的 AI 游戏开发视频生产系统。独立于游戏仓库，游戏源码只读。首期已经在 Codex Cloud **实际生产**；技术数据和云端运行状态见 [实施记录](docs/implementation.md)。默认 1920×1080 / 30fps / H.264 + AAC，中文AI配音，手机兼容 MP4。

## 当前下载方式（用户最新指示）

当前ep002已实际通过GitHub Actions生产并上传，随后下载核对hash与整片解码：[下载成片、封面与标题简介ZIP](https://github.com/zhipijun1996/video_rush/actions/runs/39594660575/artifacts/12343311814)，约30MB，2026-11-04过期。Release上传401，自托管Runner管理403，现成文件直传Actions存储也被云端代理拒绝；因此使用GitHub托管Runner重新生产，不冒称复用了同一MP4。

指定BGM由原上传曲目转为前145秒、单声道Opus 20kbps压缩副本，通过有界workflow_dispatch输入分块传输，Runner验SHA后用于轻背景配乐。临时音频块生产成功后删除，否则1天过期；媒体不提交Git，不使用第三方文件托管。原曲/压缩副本SHA都记在sources.json。后续同类入口：

```bash
python tools/dispatch_actions.py build/music/the_kindred_hearth-actions.ogg
```

每块最多48KB，最多16块；超限明确失败，不无限派发。`receive-music.yml`只接收音轨块，`produce.yml`执行全部十阶段、技术验收并上传下载包。必须确认实际运行成功与成品hash；派发不等于交付。

## 手机使用

以后成片直接交付 **GitHub预发布**，不再把Actions/Artifact作为常规入口。打开[Releases](https://github.com/zhipijun1996/video_rush/releases)，选相应的Prerelease：直接下载 `final.mp4`（成片）、`cover.png`（封面）、`bilibili.md`（推荐标题、备选标题和可复制简介），或完整资料ZIP。说明页同步展示标题和简介。预发布资产没有Artifact的14天自动过期限制；未向B站上传。

在Codex中说“用Video Rush制作一期关于……的视频”即可。当前宿主按四个Skills研究、创作、在本地渲染验收，提交代码后上传预发布。手机用户无需剪辑、写JSON或操作Actions。已有分镜可以一条CLI完成；未知主题会先形成director-brief，Codex应继续编写与执行，不能把brief交给用户当成片。

默认风格已改为轻快、紧凑、有个人感：适度反转和自嘲、原创梗图、少量音效与轻BGM（用户指定音轨优先，人声期间自动压低，首尾淡入淡出）。简单介绍约2分钟，其余默认3–5分钟；不凑时长。详见[编辑风格](docs/editorial-style.md)。

旧首期Actions成片仍有[历史运行记录](https://github.com/zhipijun1996/video_rush/actions/runs/39580103766)，只是上一轮的执行证据。后续不依赖该入口。

## 本地启动

系统依赖：Python ≥3.11、Git、FFmpeg/ffprobe（含 libx264/libass）、Noto CJK字体。历史扫描另需 `gh`，公开仓库可降级匿名API。游戏录制另需对应 Godot、Mesa及Xvfb；**已有真实素材的合成不需要Godot**。

```bash
python -m pip install -e '.[test]'
python -m video_rush doctor
python -m video_rush produce --source /workspace/gunman-rush \
  --topic '介绍一下我为什么想用AI圆做游戏的梦'
pytest -q
```

默认会在生产后上传GitHub预发布，需要`gh`已授权且分镜/代码已提交推送、工作树干净。调试先加`--local-only`；本地验收后用`python -m video_rush deliver build/episodes/ep002`交付。已编写首期美术复盘和本期初心介绍两套方案。`--source` 指向游戏本地检出；若不存在，CLI会克隆到该位置。不会在游戏工作区导入或运行Godot。不要把 `--source` 指向 Video Rush 本身。

```bash
# 全历史扫描；不refresh时冻结已有Git引用和PR详情缓存
python -m video_rush research --source /workspace/gunman-rush
# 明确更新远端历史（只fetch，不改游戏源码/当前检出）
python -m video_rush research --source /workspace/gunman-rush --refresh
# 已编写一期：完整生产与失败恢复使用同一条命令，完成后直接预发布
python -m video_rush produce --spec episodes/ep002.json --source /workspace/gunman-rush
# 只调试/验收，不先上传
python -m video_rush produce --spec episodes/ep002.json --local-only
# 提交推送后，将验收文件交付到GitHub预发布
python -m video_rush deliver build/episodes/ep002
# 修订成片使用新tag，避免覆盖已有版本
python -m video_rush deliver build/episodes/ep002 --tag ep002-v2
# 提交给当前Codex宿主的创作选择器
python -m video_rush produce --pr 90
python -m video_rush produce --story S090
python -m video_rush produce --commits SHA1..SHA2
python -m video_rush produce --since 2026-10-17 --until 2026-10-19
# 独立重验成片；非零退出代表失败
python -m video_rush validate build/episodes/ep001
```

`--topic/--pr/--story/--commits/--since/--until` 选择研究任务；`--spec` 是最终编排入口，提供时以该分镜为准，不会静默改写分镜内容。下一期的自然语言入口由 Codex + Skills 实现，确定性CLI不伪装LLM。

## 选题先看这里

已将原27条开发事件收敛为[四条主线、两条踩坑备选](docs/video-shortlist.md)：核心机制与武器、动作反馈与手感、风铃平原、Harness/Skills，以及移动钩索故障和双钩路线被反冲替代。`research/pitches.json`包含每集的开头、冲突、真实来源和需补镜头。原stories.json保留作事件证据库，不逐PR排期。

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
| `video_rush/publish.py` | 验收/hash守门、预发布上传与服务端digest复核 |
| `video_rush/graphics.py` | 原创表情梗图、简短合成底乐与音效 |
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

本期上传曲目由 `music_asset` 固定文件路径和SHA；媒体不提交Git。换环境重现时需恢复同一用户音轨，否则明确失败，不静默换曲。

Piper代码路径已实现，未在本轮下载模型或冒称其声音已经验证。模型许可需随具体模型审查。Edge属于免费可访问服务，不是离线开源引擎或可保证可用的服务。首期不用第三方BGM，不保留游戏音轨，避免不必要的音乐许可混用。

素材授权依据为用户本人项目制作请求。Underworld是Asouris的自定义宽松声明，**不是CC0**；Noto CJK为SIL OFL。AI素材的原始供应商商业条款未独立披露，不臆造“全部可商用”。见 `research/rights.json` 和成品 `sources.json`。

## 真实性与验收

来源Manifest区分AI母版、合屏预览、技术样板、历史原片、定位截图及之后重新录制。存档提交SHA与原片运行源SHA分别保存。不同阶段对照不自动等于同种子实验。游戏源本轮未改。

技术通过只证明：文件可解码、1080p/30fps/H.264/AAC、时长范围、有真实TTS音频、字幕不越界、无明显削波/长黑屏/意外长静帧，来源文件hash匹配。波形非零不等于独立语音识别通过。内容只做结构检查；完整事实独审、手机试听、审美与最终用户认可都不能自动代签。`phone-review.md` 保持待审核。

## 预发布交付与资源

默认 `produce` 在成功生产后直接创建GitHub Prerelease；`--local-only`允许先检查和修改。`deliver`会核对技术验收、内容结构检查、MP4及全部交付文件的hash，要求生产代码/分镜已提交推送。人类审核待完成可以交付预发布，不冒称审美通过。

每期先创建草稿，附MP4、PNG封面、独立投稿资料bilibili.md（推荐/备选标题及可复制简介）和含脚本/字幕/来源/报告的ZIP，并核对GitHub返回的大小和SHA256；全部成功后才转成公开Prerelease。已有正式Release绝不覆盖；已有预发布若内容不同，使用新修订tag。调用或上传失败保留 `prerelease.failure.json`，不会声称已上传。

活动Actions工作流已移到 `docs/archive/produce-actions.yml`，保留旧证据；不再作为后续常规执行/下载入口。既有工作流的成功记录见 [上一轮实施记录](docs/implementation.md)。

真实配音、素材、渲染和预发布上传都可能失败；状态和日志用于恢复。新主题创作仍由当前Codex宿主完成，没有暗藏的模型服务或凭据。

当前ep002的本地成片与指定BGM均已验收；本轮执行环境的Release附件上传返回401，尚未完成远端媒体交付，草稿不算可下载成片。修复上传授权后可用同一deliver命令续传，无需重新生产。详见docs/ep002.md。

## ep003：反冲跳跃与六条武器分支

用户已改为 Actions 下载交付。当前使用 `.github/workflows/produce.yml`，不是上文归档的旧流程。先在本地完成制作、验收并推送代码，再运行：

```bash
python -m video_rush produce --spec episodes/ep003.json --source /workspace/gunman-rush --local-only
python tools/dispatch_actions.py build/music/the_kindred_hearth-actions.ogg --spec episodes/ep003.json --episode ep003
```

本集会在只读源提交 `7be8c340372d1e20db6685cbd6a559191821eb0e` 的隔离副本中，调用正式 App、原输入 Router 和 Motor 录制普通枪及六条 Lv2 分支。Godot 必须匹配源仓库的工具链版本和下载 SHA；云端自动安装，无图形环境使用 Xvfb/Mesa。录制脚本只指定开局装备和操作，不修改原物理、美术、生命或空中资源。原片、运行轨迹及回执保存在被 Git 忽略的 `build/recordings/`；成片目录的 `recording-evidence/` 和 Actions ZIP 带轨迹/回执/日志。

“只跳/加枪”“激光持续/提前松手”来自同一源版本、Seed 与出生点。其余武器是分开录制的指定装备演示，不代表自然解锁或全流程完成。声音包含实际中文 TTS、对应片段原游戏音效和用户提供 BGM 的低音量压缩副本；与口播自动混音。视频编码、轨迹验证及完整解码通过，也仍需手机完整试听和观感审核。
