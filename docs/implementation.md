# 本轮实施与真实验证

2026-10-21，Video Rush空仓库从零实现。游戏仓库始终只读，最终 `git status --porcelain` 应为空。本仓库未提交任何视频、音频、Godot、模型或API原始大转储。

## 研究范围

完整非浅层克隆；543个可达提交、108个远端引用（含origin/HEAD别名；107个具体远端head）、91个PR（#11–#101）。时间2026-10-09T08:11:33Z至2026-10-21T08:01:53Z。main为 `7be8c340372d1e20db6685cbd6a559191821eb0e`；首期冻结的森林开发head为 `6dba342dcf557c89957e31b7faec489574d46abd`。

全部Git提交元数据、各远端tip文档/媒体目录、PR正文、API文件patch及讨论/评审已归档到 `build/research/`。GitHub文件API有3000项上限；#67/#69/#71及#92存在达到上限或报告数量异常的情况，脚本以本地Git完整变更路径补充，不声称API已返回超上限完整patch。27个精选故事进一步读取具体PR、精确base/head diff、相关报告和原始媒体。不是对543提交每一行代码做了独立内容审计。另在本仓库build内补取已删分支PR52与进行中PR101后继bbf5b24d，额外3个提交，合计546个不同可达提交；读取旧流程文档与后继current_state，森林/平原艺术仍未完成。首期不把后继内容重新绑定到旧素材。见[故事表](stories.md)、`research/stories.json`、`research/scope.json`。

## 首期实际生产

《我用 AI 做独立游戏，为什么概念图很好看，实机却总是差很多？》

本地 `build/episodes/ep001/final.mp4` 已实际生成，约4分47秒、1920×1080/30fps、H.264/yuv420p + AAC/48k，中文Edge合成解说与ASS烧录字幕。26段分镜，使用已核实的母版、合屏、实际截图、历史原片，原运行源与归档SHA分别登记。封面来自本项目母版及失败候选的真实截图。无其他游戏/B站素材、无第三方BGM、无静音冒充配音。五风格纵向比较图裁切重排为横屏，操作记录在分镜presentation，原图保持不变。

每段TTS先实际合成、测波形并归一化；最终以1.18倍保音高节奏播放，句子边界同步缩放。句内短字幕用字符比例估计，不冒称逐字强制对齐。

实际运行入口：

```bash
python -m video_rush produce --topic 'AI生成的概念图为什么无法直接变成好看的游戏'
```

全部十阶段实际跑过。技术验收通过；最终SHA、精确时长/体积与每项检查以该目录 `report.json`、`delivery.json` 为准。关键帧和封面已实际查看；没有完整人类试听、手机真机播放或独立内容终审，`human_review_required` 不改签PASS。

## 实际录制

下载锁定Godot4.7.2 Standard，完整SHA256 `cadd3204e728a35d3f13adb7fd0d7902636b79f6b95c40c265eb73b6c35329e4` 与游戏 `config/toolchain.json` 相同。Xvfb无法通过当前apt索引安装，改从Debian官方包解到本仓库build/tools，虚拟显示真实启动。采用Mesa llvmpipe，软件渲染，不声称设备帧率。

独立git archive副本，未在游戏工作树导入。main `7be8c340…`，固定Seed `level-design-v2-baseline/08`，复用 `tools/capture_underworld_formal.gd --motion`，Godot MovieMaker得到496帧/60fps、8.267秒原AVI，转成可解码MP4。480条运动观察、完整manifest hash、输入/健康/epoch保存在 `build/recordings/main-7be8-motion/`。有重生（epoch 3→4），只证明采集链路与局部运动，不宣称完整路线通过。该试录片作为额外产物，首期主体使用历史原片和截图。

## 故障、修复与未验证

- Edge默认直连失败（连接拒绝/无路由），保留 `build/probes/edge.log`；显式使用环境HTTPS代理后实际生成6.984秒测试语音，再生成完整26段配音。
- GitHub App/CLI一度401；连接器对#94/#101大diff提取失败。改用公开API和完整本地Git，最终91个PR详情都已归档，不伪装原失败为成功。
- apt缺Xvfb可用索引；官方Debian包本地解压后软件显示可用。
- ASR是额外抽样检查；最初ASR解码受PyAV/faster-whisper接口不兼容失败，保存 `build/probes/asr.failure.json`。随后改用FFmpeg PCM数组绕开PyAV接口，Whisper-base已成功识别前60秒中文口播；存在同音词/专有名词误识，只证明抽样可理解，不扩成全片逐句听审。原型模型附属preprocessor文件下载404也单独保留。
- Piper可替换后端已实现，本轮未下载中文声模、未实际合成；Edge失败会明确停在Narration，不能把Piper未运行说成自动兜底成功。
- 通用新主题需要当前Codex宿主按Skills编写分镜；Actions只复现已提交分镜，没有隐藏的LLM服务。未知主题保存brief并退出3。
- 首期使用编辑性切镜、静图缓慢运镜与分屏。自动电影级审美、完整音效设计、逐字对齐和任意动作自动驾驶仍有限，不宣称已经实现。

## 自动验收与测试

4项有实际负例的pytest通过：阶段失败恢复和输入/输出缓存；源repo只读且损坏blob修复；字幕边界及文本守恒；短源片拒绝伪造循环补足。全片FFmpeg严格解码，ffprobe格式/时长，有声波形、削波比例、字幕不越界、黑屏/静帧、源SHA均实测。内容仅结构检查，不代签真实独立事实审查、人类审美或用户认可。

## 云端交付

已实现 `.github/workflows/produce.yml` 手动入口，按完整SHA浅拉/延迟blob，节省完整8GB历史；成片和日志上传Artifact14天。实际远端run39580103766已SUCCESS，初始实现提交219768075e038ec882f0ff0621001ad18d97e697；依赖、pytest、按精确SHA取素材、全部十阶段生产与验收、Artifact上传均实际完成。成片Artifact12336770405，约84.3MB，保留14天。[运行与下载](https://github.com/zhipijun1996/video_rush/actions/runs/39580103766/artifacts/12336770405)。本轮后继提交补充扫描、ASR和授权记录，电影分镜未改变；初次成功Artifact中的元数据对应初始提交，不冒称已包含后来补充。完整云端验收与下载复核见cloud-run.json。

## 下一轮优先事项

1. 为新主题增加可配置的模型导演后端与事实审查接口，使Actions也能在明确授权凭据下完成创作；保留宿主Skills模式。
2. 强化镜头选择：依据轨迹找真正动作窗口、自动避开重生/菜单，扩展历史版本同Seed同布局对比；不为漂亮指标伪造可比性。
3. 加入全片中文ASR对齐和手机可读性抽检，提高口播节奏、字幕和视觉变化；最终审美/试听仍交给手机用户。

GitHub Artifact通过CLI直下时Azure blob返回403，改用已连接GitHub下载工具获取文件引用后复核；不能把CLI失败写为成功。公共运行页是稳定手机入口，临时签名URL不写入仓库。
