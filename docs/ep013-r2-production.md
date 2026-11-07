# ep12 第二版：类银河恶魔城，启动！

本次是叙事重剪，原版 ep013 保留。新规格为 `episodes/ep013-r2.json`，独立输出目录为 `ep013-r2`。不修改主游戏仓库，不进行 B 站投稿。

用户要求减少具体细节，多讲思路，并明确还不知道能不能做好。新版移除口播中的房间数量、编号、逐项路线和能力顺序；围绕转向类银的动机、新能力与回访、选择与探索、成长积累、张弛和可选高难挑战展开。工城留下一个空间相连的短例子。保留真实规划图和素材拼装预览，增加通用的回访思路动态图。结尾原话为“不知道能不能做好，先往下试试”。

主标题：类银河恶魔城，启动！我想做个值得回头的世界。公开期号仍为 ep12；制作编号 ep013-r2 不改变期号。封面同步使用“类银河恶魔城 / 启动！”。投稿简介不含 Git 网站，保留活动话题和素材署名。

沿用已核验的 PR141 评论 6711181818 两份附件，未把 ZIP 规划说成正式实机或已完成世界：

- `godot-room-art-cloud.zip`：SHA256 `3d9d8a591a5a5672dbf81fd8feb487eed919d3897ee9ab02fa1c9559ebabc048`。
- `world-graybox-kit-v07-light-1.zip`：SHA256 `c4e6f7692bd3341aadf972f8c766a533fe39cea925c50694ad76ccfa32fdc395`。
- PR 研究快照 head `0e742706c59e3409b23c4536ba74f89af6a2146b`，原始逐文件核验记录见 `docs/ep013-check.json`。

18 段中文配音，原用户配乐，目标 3–5 分钟。新的本地时间轴为 224.2 秒；远端成片时长与哈希以下载验证记录为准。对白修改后重新生成真实 TTS，未复用旧字幕时间。自动技术检查与用户审美审核分开记录；完整手机试听仍待用户审核。

复现：

```bash
python tools/author_ep013_r2.py
python -m video_rush produce --source /path/to/read-only/gunman-rush \
  --spec episodes/ep013-r2.json --output build/episodes/ep013-r2 --local-only
```

远端沿用用户明确选择的 Actions 下载路线。先完成独立新版，再交付包含成片、封面、标题简介、字幕与来源的 Artifact，不覆盖旧版。
