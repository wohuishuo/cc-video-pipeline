# Remotion 模板与 skill 调研 v0.1

目标：把当前视频从“2 个画面家族反复换字”扩展为“小Lin式知识视频模板库”。这里的模板不是照搬别人的视觉，而是把 GitHub/Remotion 社区里可复用的动效语法翻译成本片可剪辑、可核验的镜头类型。

## GitHub / 官方来源

1. RVE Remotion templates
   - 地址：https://github.com/reactvideoeditor/remotion-templates
   - 可用点：81 个现成 Remotion 模板，覆盖文字、图表、背景、转场、Logo、媒体等类别。
   - 对本片的用法：不复制外观，借它的组件拆法：一个模板 = 一个 React 组件 + props + frame-driven animation。

2. Remotion 官方 Agent Skills
   - 地址：https://www.remotion.dev/docs/ai/skills
   - 安装命令：`npx skills add remotion-dev/skills`
   - 可用点：官方给 AI agent 的 Remotion 项目实践，适合补“怎么组织 Remotion 项目、怎么写组件、怎么渲染检查”。

3. remotion-dev/skills
   - 地址：https://github.com/remotion-dev/skills
   - 可用点：官方 skills 源仓库。后续可以把其中 Remotion best practices 拉到本项目 `.agents/skills/`，变成长期能力。

4. iart-ai/motion-skills
   - 地址：https://github.com/iart-ai/motion-skills
   - 可用点：50+ motion graphics skills，覆盖 kinetic typography、data-viz、explainers、TikTok/Reels、WebGL、Manim。
   - 对本片的用法：优先借 kinetic typography、data-viz、explainer 三类，不借营销广告味的模板。

5. ali-abassi/remotion-templates
   - 地址：https://github.com/ali-abassi/remotion-templates
   - 可用点：面向 AI coding agent 的 Remotion 模板索引和 SKILL.md，上手成本低。

## 本片需要的 32 个镜头模板

### A. 主持人机位类

1. `PresenterFull`：主持人中景 + 下字幕。
2. `PresenterLeftEvidenceRight`：主持人在左，右侧证据卡浮入。
3. `PresenterRightChartLeft`：主持人在右，左侧图表/流程。
4. `PresenterCirclePip`：全屏素材，左下主持人圆窗。
5. `PresenterPausePunch`：主持人静停 0.8-1.2 秒，只保留一句字幕。

### B. 证据拼贴类

6. `EvidenceDeskScatter`：桌面上散落合同/截图/付款页。
7. `ScreenshotWall`：收益截图/反馈截图铺满，然后压数据框。
8. `ContractZoom`：大字承诺后推入合同小字。
9. `PhoneScroll`：手机聊天/直播页纵向滚动。
10. `ReceiptStack`：账单、发票、分期记录一张张叠上来。
11. `WebsiteTeardown`：销售页分区框选：标题、案例、付款按钮、免责声明。
12. `DocumentStamp`：合同或材料上盖“未展示/需确认/条件”。

### C. 结构解释类

13. `FlowTimeline`：鸡蛋→登记→加群→讲座→检测→套餐。
14. `CashflowTracks`：AI课/加盟/供应链三条收费轨道。
15. `RiskTransferBalance`：左侧卖方已收，右侧买方留下。
16. `BoundaryLadder`：正常生意→信息不对称→违法营销→刑事诈骗。
17. `NetworkGraph`：人、群、合同、付款、平台之间连线。
18. `FunnelActions`：点击→停留→留资→加群→付款。
19. `CostWaterfall`：营业额逐项扣到净利润。
20. `ConditionMaze`：退款条件变成关卡路径。

### D. 数据与表格类

21. `MetricFourBoxes`：总人数/达标人数/中位数/净结果。
22. `MedianVsBestCase`：最好案例与中位数并排。
23. `HiddenCostTable`：当前价格/必须费用/升级费用/退出成本。
24. `BeforeAfterLedger`：付款前看到的价格 vs 付款后实际账单。
25. `ProbabilityStrip`：案例数量放在总人数分母里。

### E. 转场与节奏类

26. `HardCutQuestion`：黑场 8-12 帧 + 大问题。
27. `WhipPanDocuments`：资料横扫切到下一组证据。
28. `ZoomIntoClause`：从承诺文案推到合同条款。
29. `MapPinToDesk`：从真实场景/行业图标落到桌面材料。
30. `NumberPunch`：关键数字大字砸入，再缩成表格。
31. `SubtitleOnlyBeat`：只保留一行字幕和背景声，做停顿。
32. `ChapterReset`：章节号 + 一句结论 + 3 张材料预告。

## 当前 Remotion 已实现 / 部分实现

- `PresenterCirclePip`
- `EvidenceDeskScatter`
- `FlowTimeline`
- `ScreenshotWall`
- `CashflowTracks`
- `ContractZoom`
- `BoundaryLadder`
- `ChecklistBoard`
- `TableScene`
- `CompareScene`

## 下一步

1. 安装/移植官方 Remotion skill，沉淀到 `.agents/skills/remotion-video/`。
2. 把上面 32 个模板拆成 `templates/` 组件目录。
3. 每个模板出一张静帧验收图，文件名格式：`preview-template-<template>.png`。
4. 反读心验收：模板描述只写画面元素、时长、切换方式，不写“观众会觉得”。
