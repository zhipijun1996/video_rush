# 拍拍波：用户完整分镜 v1 重剪

新主片与 ep008-r2 分开保存。唯一剧情依据为 [用户分镜原文](../episodes/briefs/ep008-r3-user-storyboard-v1.md)，SHA256 `085002b9cbf3918e226500b640ca141cbaebdeca676aa365ab478eaafb6ab8d5`。36个父镜头、47句中文对白，实际时间线111.6秒；日语短引用、片尾笑声另列音轨。

```sh
python -m tools.prepare_wave_story --spec episodes/ep008-r3-film.json --source build/sources/wave-game --project build/recordings/wave-film-c6f1326c824a
# 在项目目录安装 playwright 的 Chromium 与 ffmpeg，或设置 VR_CHROMIUM_PATH
python -m tools.capture_wave_film
python -m tools.make_paipai_film --stage structure  # 可选：先检查R/G和对白结构
python -m tools.make_paipai_film
```

输入为 wave-game `c6f1326c824a4b5c8489b0918285d9063f9d1db6` 的只读快照。原仓库不修改。21轮连续对局自5血、0气开始，原规则逐轮独立结算比对；对方固定选招在输入窗口之前封存。不是实时联网双人，也没有为了剧情中途注入血量/能量。A反弹B中波、最终五气光线击破反弹的方向及结果必须通过断言。

另录390×844触屏浏览器，首页、点击开局、真实选防御与WebAudio一并记录。桌面与手机录屏都用首尾色标校准视频/音频时钟，漂移超界直接失败。现有素材和新录制有SHA，缓存损坏不能当成功复用。

火柴人使用关节动作、表情、速度线、定格反应、手势/声桥和童年重影。AN短引用与实机G是可替换独立图层；招式碰撞、血条变化和胜负必须回到实机。中文对白为真实Edge TTS，逐句裁切首尾空白，使用实际合成边界生成字幕。视频片段无音轨，统一连续浮点音轨合成，避免每段AAC填充造成累计漂移。最终保留 `-reinit_filter 0`，防混合片段色彩元数据变化导致滤镜重新初始化吞帧。

主片 `build/episodes/ep008-r3/final.mp4`；`short-tail.mp4`仅省略7-03重影，不覆盖主片。还输出完整确认稿、实际逐镜CSV、结构化编辑工程、脚本、ASS/SRT、封面、投稿资料、逐条来源/音轨许可状态、探测报告和手机审核清单。

自动验收覆盖全片/短片解码、1080p/30fps/H.264/AAC、真实配音波形、字幕边界、削波、黑屏/静帧、36父镜头存活和对局不变量。它不认证好笑、自然、审美合格或版权许可。动漫引用及游戏自带的作品录音均保留未确认授权状态；当前只用于私下审核，未投稿B站/Toy。Runner成功并下载核验后，才记录Actions交付成功。
