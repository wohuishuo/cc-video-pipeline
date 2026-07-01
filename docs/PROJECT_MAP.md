# cc视频剪辑 项目地图

这是一个视频创作流水线仓库，不是传统软件项目。现在按“能出片”分层看：

## 入口文件

- `CLAUDE.md`：项目总规则，接手时先读。
- `TOOLS.md`：工具速查，想做某个动作时先查这里。
- `.claude/skills/`：当前生效的创作 skill。
- `reference/`：参考视频拆解和 SOP。
- `projects/`：具体视频项目和实验产物。
- `tools/`：可复用脚本、转录、TTS、Remotion 动画。

## 当前最有用的链路

### 小Lin风格知识/读书视频

详见 `docs/workflows/xiaolin-style-video.md`。

核心链路：

1. `ref-analyze`：拆参考视频，沉淀结构。
2. `content-plan`：选题和标题。
3. `script-pyramid`：结论先行写稿。
4. `storyboard`：把每段口播强制配视觉支撑。
5. Remotion / B-roll / 信息图：做画面密度。
6. `local-tts-dub` 或真人录音：配音。
7. `edit-ffmpeg`：字幕、横竖屏、粗剪。
8. `thumbnail`：封面。
9. `review-data`：复盘数据。

### 纳西妲本地配音

- Qwen3-TTS 稳定生产版：`tools/tts-mvp/`
- so-vits 变声试听：`tools/tts-mvp/nahida_sovits.ps1`
- 说明：`nahida/README.md`

注意：so-vits 是“源音频 -> 纳西妲声线”的变声，不是直接 TTS。

## 不要提交的大东西

- 模型权重：`*.pth` / `*.pt` / `tools/tts-mvp/models/`
- 生成音频/视频：`*.wav` / `*.mp4`
- 外部 clone：`projects/so-vits-svc/`
- 剪映/排查临时目录：`projects/_jianying_data/`、`projects/_cos_triage/`

## 最小可跑检查

```powershell
.\tools\setup.ps1
.\.claude\skills\local-tts-dub\scripts\check.ps1
```

如果要做新片，先建：

```text
projects/<slug>/
  brief.md
  titles.md
  script.md
  storyboard.md
  assets/
  audio/
  exports/
  review.md
```
