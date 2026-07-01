# Remotion 制作运行说明

目标：当前 Remotion 版本是 30 分钟资料卡骨架视频，用来验证节奏、卡片、章节和横竖屏排版。它不是最终成片，后续要逐步替换重构页面、B-roll、合同截图和配音。

## Composition

入口文件：

```text
tools/remotion-hello/src/root.tsx
```

新增组件：

```text
tools/remotion-hello/src/informationGap.tsx
```

可用 composition：

```text
information-gap
information-gap-vertical
```

规格：

| Composition | 尺寸 | 时长 | 帧率 |
|---|---:|---:|---:|
| `information-gap` | 1920x1080 | 1800 秒 | 30 |
| `information-gap-vertical` | 1080x1920 | 1800 秒 | 30 |

## 已验证命令

在目录：

```powershell
cd C:\Users\艾莉\Videos\cc视频剪辑\tools\remotion-hello
```

列出 compositions：

```powershell
npx remotion compositions src/root.tsx
```

已确认输出包含：

```text
information-gap             30      1920x1080      54000
information-gap-vertical    30      1080x1920      54000
```

导出静帧：

```powershell
npx remotion still src/root.tsx information-gap ..\..\projects\information-gap-business\preview-000045.png --frame=45
npx remotion still src/root.tsx information-gap ..\..\projects\information-gap-business\preview-000900.png --frame=900
npx remotion still src/root.tsx information-gap-vertical ..\..\projects\information-gap-business\preview-vertical-000900.png --frame=900
```

已生成：

```text
projects/information-gap-business/preview-000045.png
projects/information-gap-business/preview-000900.png
projects/information-gap-business/preview-vertical-000900.png
```

## 预览 Studio

```powershell
npx remotion studio src/root.tsx
```

打开后选择：

```text
information-gap
```

或：

```text
information-gap-vertical
```

## 当前骨架说明

当前 `informationGap.tsx` 内置 38 个场景，对应 `storyboard.md` 的 38 个镜组。

每个场景包含：

```text
start / end
chapter
kind
title
items
accent
```

场景类型：

```text
title
grid
boundary
flow
compare
table
question
```

后续可以把内置 `scenes` 数组迁移成 JSON：

```text
projects/information-gap-business/remotion-scenes.json
```

再由组件 import，方便非代码编辑。

## 下一步替换计划

### 1. 替换开场四入口

当前：文字卡。

目标：

- 9.9 AI 课重构页面。
- 1 元鸡蛋登记页。
- 餐饮加盟招商页。
- 招聘 App 高薪兼职页。

对应素材清单：

```text
asset-shot-list.md R01-R04
```

### 2. 替换费用链

当前：文字流程卡。

目标：

- 横屏长链路动画。
- 竖屏三段滚动链路。
- 每项下面标注“谁收钱”。

对应卡片：

```text
visual-cards.md F01
```

### 3. 替换合同小字

当前：表格卡。

目标：

- 大字“不过全退”先出现。
- 镜头推近。
- 小字逐条红框高亮。

对应卡片：

```text
visual-cards.md G04
```

### 4. 加入口播音频

待做：

- 根据 `script.md` 录音或 TTS。
- 生成台词级 timing。
- 用真实 timing 替换现在按 storyboard 估算的 `start/end`。

建议输出：

```text
projects/information-gap-business/narration.wav
projects/information-gap-business/timings.json
```

### 5. 加字幕

待做：

- 从 `script.md` 切分字幕。
- 与配音 timing 对齐。
- Remotion 底部字幕使用 1-2 行，避免遮挡资料卡。

## 反读心验收

每次改 `informationGap.tsx` 或场景数据后，扫以下词：

```powershell
rg -n "观众|让人|觉得|感觉|相信|心动|高级|焦虑|恐惧|心理|身份|错觉|安全感|情绪|秘密" tools\remotion-hello\src\informationGap.tsx projects\information-gap-business
```

允许出现在规则说明里，不允许出现在画面文案里。

## 当前风险

- 目前只是卡片骨架，缺少真实 B-roll 和重构页面。
- 30 分钟全渲染会很慢，开发时先用 `still` 和短段落 render。
- 真实配音完成后，场景时间必须重新对齐。
- 横屏可读性已通过静帧检查；竖屏可读，但后续加入更多文字时要继续看安全区。
