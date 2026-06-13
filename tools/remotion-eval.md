# Remotion 评估笔记

评估日期：2026-06-12

## 是什么

[Remotion](https://remotion.dev) 是一个用 **React 组件编程生成视频** 的框架。每帧 = 一个 React 组件渲染的网页画面。支持 SVG、Canvas、WebGL、CSS 动画、Three.js。

## 安装体验

- 脚手架：`npx create-video@latest`
- Windows 11 node 24 + npm 11 完全兼容
- 注意：npm 缓存路径不能包含中文用户名（老旧 npm 的 bug），设置 `$env:npm_config_cache` 绕开
- ffmpeg 8.1.1 已装，Remotion 不会重复下载

## 适合做什么（对 cc 视频三类内容的匹配度）

| 场景 | 适合度 | 说明 |
|---|---|---|
| **科普视频的图示/动画** | ⭐⭐⭐⭐⭐ | 数据可视化、流程图、公式标注、时间轴动画 —— 程序员写 React 比 AE 拉关键帧快 10 倍 |
| **科普视频的字幕特效** | ⭐⭐⭐⭐ | 逐字高亮、关键词弹出、代码高亮（Code Hike 模板）|
| **Vlog 的标题卡/转场** | ⭐⭐⭐ | 可以做，但 ffmpeg 的 drawtext 更轻量；Remotion 适合复杂动效 |
| **Cos 跳舞视频** | ⭐ | 实时画面 + 特效叠加不适合纯代码渲染；用 ffmpeg 滤镜更合适 |
| **封面图生成** | ⭐⭐⭐⭐ | SVG/HTML 模板渲染，比 Photoshop 模板更可编程、可批量 |
| **稿子→演示画面** | ⭐⭐⭐⭐ | 把 script.md 渲染成带字幕的 16:9 演示（类似 garden-skills 的 web-video-presentation）|

## 性能（Intel Arc 140T）

- 渲染：纯 CPU（无浏览器 GPU 合成），255H 的 16 核够用
- QSV 加速：Remotion 调用系统 ffmpeg 做编码，QSV 可用（设置 `REMOTION_GPU=1`）
- 实测：1080p 30s 动画约 30-60s 渲染（取决于复杂度）
- 瓶颈在 Chromium 帧渲染而非编码，所以 QSV 收益有限

## 模板生态

从 20+ 官方模板看，最相关的几个：
- **Hello World** — 入门动画
- **Audiogram** — 播客文字+波形可视化
- **Music Visualization** — 音乐可视化
- **Code Hike** — 代码高亮动画（程序员教编程/技术科普神器）
- **Prompt to Video** — AI 生成故事+图片+配音
- **React Three Fiber** — 3D 动画（科普可用）

## 后续集成建议

### 短期（这次就可做）
1. 在 `tools/remotion-hello/` 跑通 hello world，验证渲染链路
2. 做一个 `tools/remotion-templates/title-card/` 模板：读 `script.md` 生成开场标题动画

### 中期（科普视频启动时）
3. 做 `科普图示模板`：数据对比条、时间轴、流程图（React 组件化，复用）
4. 与 script-pyramid 联动：稿子里的"论点1/论据"自动拉 Remotion 模板渲染成动画片段
5. 与 storyboard 联动：分镜表直接驱动 Remotion 渲染管线

### 不做
- 实拍视频的剪辑/特效——那是 ffmpeg 和剪辑软件的活
- 实时预览——Remotion Studio 可以看预览，但不是 NLE 时间轴

## 结论

- **适合安装**，脚手架体验流畅
- **科普视频的动画方案的明确首选**（程序员友好、React 技能复用、模板丰富）
- **不是替代 ffmpeg/必剪**，而是补充"代码生成动画"这一环
- **短期投入**: 跑通 hello world + 做 1 个标题卡模板。**中期**: 科普图示组件库
