import {
  AbsoluteFill,
  Audio,
  Easing,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const FPS = 30;
const BG = "#15120f";
const CARD = "#f4efe4";
const FG = "#f3efe7";
const INK = "#191714";
const MUTED = "#b8ad9d";
const RED = "#d94a3a";
const GOLD = "#d6a742";
const BLUE = "#4f8cc9";
const GREEN = "#4f8f6a";
const SANS = '"Microsoft YaHei","SimHei","Inter","Segoe UI",sans-serif';

type SceneKind = "title" | "grid" | "boundary" | "flow" | "compare" | "table" | "question";

type Scene = {
  id: number;
  start: number;
  end: number;
  chapter: string;
  kind: SceneKind;
  title: string;
  subtitle?: string;
  items: string[];
  accent?: string;
};

const scenes: Scene[] = [
  { id: 1, start: 0, end: 8, chapter: "OPEN", kind: "title", title: "你刷到过这种东西吗？", items: ["9.9 课", "1 元鸡蛋", "低价加盟", "高薪兼职"], accent: BLUE },
  { id: 2, start: 8, end: 22, chapter: "OPEN", kind: "grid", title: "四个入口", items: ["9.9 体验课", "1 元鸡蛋", "加盟名额", "月入过万"], accent: GOLD },
  { id: 3, start: 22, end: 45, chapter: "OPEN", kind: "grid", title: "材料完整，不等于信息完整", items: ["直播", "老师", "合同", "成功案例", "付款链接"], accent: BLUE },
  { id: 4, start: 45, end: 80, chapter: "MAIN QUESTION", kind: "title", title: "如果我失败了，\n它已经赚了什么？", items: ["学费", "加盟费", "设备原料", "软件续费"], accent: RED },
  { id: 5, start: 80, end: 90, chapter: "TITLE", kind: "title", title: "你失败，他也赚", subtitle: "信息差生意的现金流路径", items: ["入口", "案例", "收费", "绑定", "退出"], accent: GOLD },
  { id: 6, start: 90, end: 125, chapter: "01 边界", kind: "boundary", title: "不是所有高毛利都是诈骗", items: ["正常生意", "信息不对称", "违法营销", "刑事诈骗"], accent: BLUE },
  { id: 7, start: 125, end: 170, chapter: "01 边界", kind: "compare", title: "产品存在 ≠ 信息完整", items: ["课上了", "群建了", "合同签了", "设备寄了", "关键费用在后面"], accent: RED },
  { id: 8, start: 170, end: 215, chapter: "02 筛选入口", kind: "flow", title: "免费和低价是入口", items: ["免费直播", "9.9 体验", "加微信", "进群", "正价课", "高阶陪跑"], accent: BLUE },
  { id: 9, start: 215, end: 250, chapter: "02 筛选入口", kind: "grid", title: "筛选的是动作", items: ["点击", "停留", "留资", "加群", "付款", "听完"], accent: GREEN },
  { id: 10, start: 250, end: 310, chapter: "03 案例概率", kind: "question", title: "成功案例不是概率", items: ["总人数？", "中位数？", "净利润？", "失败者？"], accent: BLUE },
  { id: 11, start: 310, end: 335, chapter: "03 案例概率", kind: "table", title: "截图不是财报", items: ["30000", "- 广告费", "- 工具费", "- 抽成", "- 退款", "= 净结果：未展示"], accent: RED },
  { id: 12, start: 335, end: 410, chapter: "02 筛选入口", kind: "flow", title: "鸡蛋是门票", items: ["鸡蛋", "登记", "加群", "讲座", "检测", "产品套餐"], accent: GOLD },
  { id: 13, start: 410, end: 455, chapter: "02 筛选入口", kind: "flow", title: "一次交易 → 长期触达", items: ["问候", "活动", "群直播", "检测报告", "复购提醒", "专人跟进"], accent: GREEN },
  { id: 14, start: 455, end: 490, chapter: "KEY 01", kind: "question", title: "免费入口后面，接着收什么？", items: ["留下什么信息？", "进入什么群？", "后面付什么？"], accent: BLUE },
  { id: 15, start: 490, end: 535, chapter: "04 结果承诺", kind: "grid", title: "卖产品，也卖结果标签", items: ["AI 红利", "被动收入", "城市合伙人", "不再打工", "孩子未来", "传承智慧"], accent: GOLD },
  { id: 16, start: 535, end: 585, chapter: "04 结果承诺", kind: "compare", title: "结果承诺背后的条件", items: ["零基础 / 接单", "客户来源？", "交付标准？", "工具成本？", "退款条件？"], accent: BLUE },
  { id: 17, start: 585, end: 635, chapter: "04 结果承诺", kind: "table", title: "加盟费只是账单一行", items: ["加盟费", "设备", "装修", "原料", "房租", "人工", "平台抽成", "广告投放"], accent: RED },
  { id: 18, start: 635, end: 750, chapter: "KEY 02", kind: "question", title: "结果承诺背后，必须投入什么？", items: ["客户来源", "交付标准", "工具成本", "平台价格", "退款条件"], accent: BLUE },
  { id: 19, start: 750, end: 815, chapter: "05 案例概率", kind: "grid", title: "案例不等于概率", items: ["收益截图", "排队视频", "上岸名单", "反馈截图", "晒单"], accent: GOLD },
  { id: 20, start: 815, end: 890, chapter: "05 案例概率", kind: "question", title: "案例旁边必须补数字", items: ["总人数？", "达标人数？", "中位数？", "净结果？"], accent: BLUE },
  { id: 21, start: 890, end: 945, chapter: "05 案例概率", kind: "table", title: "月入三万拆口径", items: ["30000", "- 广告费", "- 工具费", "- 平台抽成", "- 退款", "- 税费", "= 未展示"], accent: RED },
  { id: 22, start: 945, end: 1020, chapter: "05 案例概率", kind: "table", title: "营业额不是利润", items: ["营业额", "- 房租", "- 人工", "- 食材", "- 平台抽成", "- 损耗", "= 净利润"], accent: RED },
  { id: 23, start: 1020, end: 1090, chapter: "06 收费链", kind: "flow", title: "第一笔钱 ≠ 完整成本", items: ["免费体验", "基础课", "高阶课", "陪跑营", "工具", "API", "设备", "续费维护"], accent: GOLD },
  { id: 24, start: 1090, end: 1150, chapter: "06 收费链", kind: "compare", title: "谁收钱？收几次？", items: ["AI：课程 / 工具 / API", "加盟：设备 / 装修 / 原料", "供应链：软件 / 物流 / 抽成"], accent: BLUE },
  { id: 25, start: 1150, end: 1200, chapter: "06 收费链", kind: "flow", title: "招聘入口 → 培训消费", items: ["招聘", "面试", "能力不足", "培训合同", "分期账单", "推荐就业"], accent: RED },
  { id: 26, start: 1200, end: 1320, chapter: "KEY 04", kind: "table", title: "把所有费用列成表", items: ["当前价格", "必须费用", "升级费用", "退出成本", "谁收钱"], accent: BLUE },
  { id: 27, start: 1320, end: 1370, chapter: "07 风险转移", kind: "title", title: "卖方赚不赚钱，\n是否依赖你最终成功？", items: ["抽成 / 分佣", "学费 / 设备 / 续费"], accent: GOLD },
  { id: 28, start: 1370, end: 1425, chapter: "07 风险转移", kind: "compare", title: "失败结果 / 已收费用", items: ["没学会 → 课程费", "没接单 → 工具费", "店倒闭 → 设备原料", "没就业 → 培训分期", "没通过 → 条件链"], accent: RED },
  { id: 29, start: 1425, end: 1475, chapter: "07 风险转移", kind: "flow", title: "控制越少，退出越难", items: ["货源", "物流", "广告账户", "订单系统", "素材/API", "提现规则"], accent: GREEN },
  { id: 30, start: 1475, end: 1525, chapter: "07 风险转移", kind: "table", title: "展示品 / 到手品 / 解释口径", items: ["直播间展示", "下单页面", "到手实物", "售后解释", "补差价", "退款记录"], accent: RED },
  { id: 31, start: 1525, end: 1590, chapter: "07 风险转移", kind: "compare", title: "卖方拿走 / 买方留下", items: ["学费 / 加盟费 / 设备费", "贷款 / 库存 / 房租", "平台规则 / 时间成本 / 退款流程"], accent: GOLD },
  { id: 32, start: 1590, end: 1620, chapter: "08 五问", kind: "title", title: "付款前问 5 个问题", items: ["中位数", "失败者", "后续费用", "合同", "失败时已赚"], accent: BLUE },
  { id: 33, start: 1620, end: 1645, chapter: "08 五问", kind: "question", title: "不算最好案例，中位数是多少？", items: ["全部人", "中位数", "扣掉成本"], accent: BLUE },
  { id: 34, start: 1645, end: 1670, chapter: "08 五问", kind: "question", title: "失败者占多少？主要怎么失败？", items: ["学习", "流量", "客户", "工具", "平台", "退款"], accent: RED },
  { id: 35, start: 1670, end: 1695, chapter: "08 五问", kind: "question", title: "除了当前价格，后面还要付什么？", items: ["工具", "设备", "原料", "月费", "抽成", "服务费"], accent: GOLD },
  { id: 36, start: 1695, end: 1725, chapter: "08 五问", kind: "question", title: "交付清单能不能逐项确认？", items: ["展示画面", "型号规格", "数量重量", "售后口径"], accent: BLUE },
  { id: 37, start: 1725, end: 1765, chapter: "08 五问", kind: "question", title: "我失败时，它已经赚了什么？", items: ["学费", "加盟费", "设备原料", "软件", "广告", "续费"], accent: RED },
  { id: 38, start: 1765, end: 1800, chapter: "END", kind: "flow", title: "把销售页翻译成账面", items: ["机会 → 账单", "案例 → 概率", "扶持 → 控制接口", "展示 → 交付清单"], accent: GOLD },
];

const fadeIn = (frame: number, from = 0, len = 12) =>
  interpolate(frame, [from, from + len], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

const splitTitle = (title: string) => title.split("\n");

const Progress: React.FC<{ totalFrames: number }> = ({ totalFrames }) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: 7, background: "rgba(255,255,255,0.06)" }}>
      <div style={{ height: "100%", width: `${Math.min(100, (frame / totalFrames) * 100)}%`, background: `linear-gradient(90deg, ${BLUE}, ${GOLD}, ${RED})` }} />
    </div>
  );
};

const Header: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => (
  <div style={{
    position: "absolute",
    top: vertical ? 74 : 48,
    left: vertical ? 56 : 72,
    right: vertical ? 56 : 72,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontFamily: SANS,
    color: MUTED,
    fontSize: vertical ? 24 : 22,
    letterSpacing: 2,
  }}>
    <span style={{ color: scene.accent ?? BLUE, fontWeight: 800 }}>{scene.chapter}</span>
    <span>{String(scene.id).padStart(2, "0")} / {scenes.length}</span>
  </div>
);

const BackdropTexture: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const frame = useCurrentFrame();
  const drift = Math.sin(frame / 55) * (vertical ? 18 : 26);
  const slowDrift = Math.sin(frame / 90) * (vertical ? 10 : 16);
  const gridShift = `${frame % 44}px ${Math.round((frame * 0.35) % 44)}px`;
  const fallbackLabels = ["登记表", "合同条款", "付款页", "收益截图", "群公告", "分期账单"];
  const labels = [...scene.items, ...fallbackLabels].slice(0, 6);
  return (
    <AbsoluteFill style={{
      background: `
        linear-gradient(115deg, rgba(9,8,7,0.88), rgba(24,20,15,0.92)),
        radial-gradient(circle at 25% 18%, ${(scene.accent ?? BLUE)}44, transparent 26%),
        radial-gradient(circle at 82% 76%, rgba(214,167,66,0.2), transparent 30%),
        #17130f`,
      overflow: "hidden",
    }}>
      {labels.map((label, i) => {
        const w = vertical ? 310 : 420;
        const h = vertical ? 210 : 260;
        const left = vertical ? (i % 2) * 470 - 80 : 110 + (i % 3) * 560;
        const top = vertical ? 150 + i * 230 : 120 + Math.floor(i / 3) * 420;
        return (
          <div key={label} style={{
            position: "absolute",
            left,
            top: top + drift * (i % 2 ? -1 : 1),
            width: w,
            height: h,
            transform: `rotate(${[-8, 5, -3, 7, -5, 4][i]}deg)`,
            background: i % 2 ? "#1d252b" : "#e7ddc9",
            border: "1px solid rgba(255,255,255,0.16)",
            boxShadow: "0 28px 80px rgba(0,0,0,0.42)",
            opacity: 0.22,
            borderRadius: 6,
            padding: 24,
            fontFamily: SANS,
            color: i % 2 ? "#dfe9f2" : "#2b241d",
            fontSize: vertical ? 28 : 30,
            fontWeight: 900,
            scale: 1 + Math.sin((frame + i * 19) / 120) * 0.01,
          }}>
            {label}
            <div style={{ marginTop: 22, height: 9, width: "76%", background: "currentColor", opacity: 0.22 }} />
            <div style={{ marginTop: 15, height: 9, width: "54%", background: "currentColor", opacity: 0.18 }} />
            <div style={{ position: "absolute", right: 22, bottom: 22, width: 82, height: 42, border: `4px solid ${scene.accent ?? BLUE}`, opacity: 0.32 }} />
          </div>
        );
      })}
      <div style={{
        position: "absolute",
        inset: 0,
        backgroundImage: "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
        backgroundSize: "44px 44px",
        backgroundPosition: gridShift,
        opacity: 0.22,
      }} />
      <div style={{
        position: "absolute",
        left: vertical ? -120 : -220,
        top: vertical ? 220 : 120,
        width: vertical ? 380 : 620,
        height: vertical ? 5 : 6,
        background: `linear-gradient(90deg, transparent, ${(scene.accent ?? BLUE)}88, transparent)`,
        opacity: 0.28,
        translate: `${slowDrift * 6}px ${drift * 3}px`,
        rotate: "-18deg",
        boxShadow: `0 0 34px ${(scene.accent ?? BLUE)}66`,
      }} />
    </AbsoluteFill>
  );
};

const LowerCaption: React.FC<{ text: string; vertical?: boolean }> = ({ text, vertical }) => (
  <div style={{
    position: "absolute",
    left: vertical ? 48 : 300,
    right: vertical ? 48 : 300,
    bottom: vertical ? 62 : 54,
    minHeight: vertical ? 70 : 58,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "rgba(0,0,0,0.48)",
    borderTop: "1px solid rgba(255,255,255,0.18)",
    borderBottom: "1px solid rgba(255,255,255,0.12)",
    fontFamily: SANS,
    fontSize: vertical ? 34 : 34,
    lineHeight: 1.25,
    color: "#fff",
    fontWeight: 850,
    textShadow: "0 2px 8px rgba(0,0,0,0.9)",
    padding: "10px 26px",
  }}>
    {text.replace("\n", " ")}
  </div>
);

const PresenterWindow: React.FC<{ compact?: boolean; vertical?: boolean; side?: "left" | "right" }> = ({ compact, vertical, side = "left" }) => {
  const size = vertical ? 154 : 148;
  if (compact) {
    return (
      <div style={{
        position: "absolute",
        left: vertical ? 46 : 68,
        bottom: vertical ? 48 : 44,
        width: size,
        height: size,
        borderRadius: "50%",
        overflow: "hidden",
        border: "5px solid rgba(255,255,255,0.88)",
        boxShadow: "0 18px 50px rgba(0,0,0,0.55)",
        background: "#2d241c",
      }}>
        <PresenterFigure compact />
      </div>
    );
  }
  return (
    <div style={{
      position: "absolute",
      [side]: vertical ? 58 : 96,
      bottom: vertical ? 162 : 112,
      width: vertical ? 330 : 390,
      height: vertical ? 480 : 520,
      borderRadius: 14,
      overflow: "hidden",
      border: "1px solid rgba(255,255,255,0.2)",
      boxShadow: "0 30px 100px rgba(0,0,0,0.48)",
      background: "#2d241c",
    }}>
      <PresenterFigure />
    </div>
  );
};

const PresenterFigure: React.FC<{ compact?: boolean }> = ({ compact }) => (
  <AbsoluteFill style={{
    background: "linear-gradient(180deg, #4b3a2b, #1e1915)",
    overflow: "hidden",
  }}>
    {[0, 1, 2, 3].map((i) => (
      <div key={i} style={{
        position: "absolute",
        left: `${8 + i * 23}%`,
        top: compact ? "8%" : "6%",
        width: compact ? 18 : 44,
        height: compact ? 58 : 170,
        background: i % 2 ? "#72583b" : "#c9a56d",
        opacity: 0.55,
      }} />
    ))}
    {!compact && (
      <>
        <div style={{
          position: "absolute",
          left: "8%",
          right: "8%",
          top: "12%",
          height: 5,
          background: "rgba(255,255,255,0.2)",
        }} />
        <div style={{
          position: "absolute",
          left: "9%",
          bottom: "8%",
          width: "82%",
          height: "16%",
          borderRadius: "10px 10px 0 0",
          background: "linear-gradient(180deg, #5a4634, #2a211b)",
          boxShadow: "0 -14px 35px rgba(0,0,0,0.28)",
        }} />
        <div style={{
          position: "absolute",
          right: "18%",
          bottom: "21%",
          width: 22,
          height: 96,
          borderRadius: 14,
          background: "#111",
          boxShadow: "0 0 0 6px rgba(255,255,255,0.08)",
        }} />
      </>
    )}
    <div style={{
      position: "absolute",
      left: "50%",
      top: compact ? "28%" : "25%",
      width: compact ? 44 : 120,
      height: compact ? 44 : 120,
      borderRadius: "50%",
      background: "#e0b48d",
      transform: "translateX(-50%)",
      boxShadow: "0 8px 28px rgba(0,0,0,0.34)",
    }} />
    <div style={{
      position: "absolute",
      left: "50%",
      top: compact ? "55%" : "48%",
      width: compact ? 82 : 250,
      height: compact ? 80 : 250,
      borderRadius: compact ? "42px 42px 0 0" : "110px 110px 0 0",
      background: "linear-gradient(180deg, #f1eee8, #7b756b)",
      transform: "translateX(-50%)",
    }} />
  </AbsoluteFill>
);

const cardKinds = ["网页", "合同", "票据", "手机", "表格", "照片"];

const FloatingEvidenceCard: React.FC<{ text: string; index: number; color: string; vertical?: boolean; dense?: boolean }> = ({ text, index, color, vertical, dense }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame: frame - 5 - index * 4, fps, from: 0.92, to: 1, config: { damping: 18, stiffness: 130 } });
  const op = fadeIn(frame, 4 + index * 4, 9);
  const kind = cardKinds[index % cardKinds.length];
  const isDark = index % 3 === 0;
  return (
    <div style={{
      opacity: op,
      transform: `rotate(${[-4, 3, -2, 5, -3, 2][index % 6]}deg) scale(${scale})`,
      width: vertical ? (dense ? 300 : 360) : (dense ? 315 : 390),
      height: vertical ? (dense ? 205 : 250) : (dense ? 205 : 245),
      background: isDark ? "#20262b" : CARD,
      color: isDark ? "#f2f6fa" : INK,
      borderRadius: kind === "手机" ? 22 : 8,
      border: `1px solid ${isDark ? "rgba(255,255,255,0.22)" : "rgba(20,16,12,0.16)"}`,
      boxShadow: "0 24px 58px rgba(0,0,0,0.36)",
      padding: vertical ? 22 : 24,
      fontFamily: SANS,
      position: "relative",
      overflow: "hidden",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color, fontWeight: 950, fontSize: vertical ? 21 : 20 }}>
        <span>{kind}</span>
        <span>{String(index + 1).padStart(2, "0")}</span>
      </div>
      <div style={{ marginTop: 20, fontSize: vertical ? 30 : 30, lineHeight: 1.15, fontWeight: 950 }}>{text}</div>
      <div style={{ position: "absolute", left: 24, right: 24, bottom: 24 }}>
        <div style={{ height: 8, width: "82%", background: "currentColor", opacity: 0.16, marginBottom: 11 }} />
        <div style={{ height: 8, width: "58%", background: "currentColor", opacity: 0.12 }} />
      </div>
      {(kind === "合同" || text.includes("退") || text.includes("合同")) && (
        <div style={{ position: "absolute", right: 22, bottom: 22, width: 112, height: 50, border: `5px solid ${RED}`, opacity: 0.9 }} />
      )}
      {kind === "表格" && [0, 1, 2].map((row) => (
        <div key={row} style={{ position: "absolute", left: 24, right: 24, top: 118 + row * 27, height: 1, background: "currentColor", opacity: 0.16 }} />
      ))}
    </div>
  );
};

const SceneTitle: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const frame = useCurrentFrame();
  const color = scene.accent ?? BLUE;
  return (
    <div style={{ opacity: fadeIn(frame, 0, 12), marginBottom: vertical ? 18 : 28 }}>
      {splitTitle(scene.title).map((line) => (
        <div key={line} style={{
          fontFamily: SANS,
          fontSize: vertical ? 54 : 68,
          lineHeight: 1.08,
          fontWeight: 900,
          color: FG,
          textAlign: vertical ? "left" : "center",
          textShadow: `0 4px 0 rgba(0,0,0,0.34), 0 0 44px ${color}55`,
          whiteSpace: "nowrap",
        }}>
          {line}
        </div>
      ))}
      {scene.subtitle && (
        <div style={{
          marginTop: 18,
          fontFamily: SANS,
          fontSize: vertical ? 31 : 34,
          color: "#eadfce",
          textAlign: vertical ? "left" : "center",
          fontWeight: 600,
        }}>
          {scene.subtitle}
        </div>
      )}
    </div>
  );
};

const NetworkLines: React.FC<{ count: number; color: string; vertical?: boolean }> = ({ count, color, vertical }) => (
  <svg style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.88 }}>
    {Array.from({ length: Math.max(1, Math.min(5, count - 1)) }).map((_, i) => {
      const x1 = vertical ? 210 : 500 + i * 210;
      const y1 = vertical ? 390 + i * 210 : 520 + (i % 2) * 120;
      const x2 = vertical ? 740 : 720 + i * 220;
      const y2 = vertical ? 470 + i * 195 : 470 + ((i + 1) % 2) * 130;
      return (
        <g key={i}>
          <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={5} strokeDasharray="12 10" />
          <circle cx={x2} cy={y2} r={8} fill={color} />
        </g>
      );
    })}
  </svg>
);

const FlowTimeline: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const color = scene.accent ?? BLUE;
  const items = scene.items.slice(0, vertical ? 6 : 8);
  return (
    <div style={{
      position: "relative",
      width: vertical ? 900 : 1360,
      height: vertical ? 830 : 520,
      fontFamily: SANS,
    }}>
      <div style={{
        position: "absolute",
        left: vertical ? 430 : 70,
        right: vertical ? undefined : 70,
        top: vertical ? 50 : 250,
        bottom: vertical ? 70 : undefined,
        width: vertical ? 8 : undefined,
        height: vertical ? undefined : 8,
        background: `linear-gradient(${vertical ? "180deg" : "90deg"}, ${color}, rgba(255,255,255,0.28))`,
        boxShadow: `0 0 26px ${color}77`,
      }} />
      {items.map((item, i) => {
        const x = vertical ? (i % 2 === 0 ? 40 : 500) : 30 + i * (1280 / Math.max(1, items.length - 1));
        const y = vertical ? 55 + i * 120 : (i % 2 === 0 ? 42 : 292);
        return (
          <div key={item} style={{ position: "absolute", left: x, top: y }}>
            <FloatingEvidenceCard text={item} index={i} color={color} vertical={vertical} dense />
          </div>
        );
      })}
    </div>
  );
};

const ScreenshotWall: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const color = scene.accent ?? BLUE;
  const cards = [...scene.items, "未展示人数", "退款记录", "投放成本", "平台抽成"].slice(0, vertical ? 8 : 10);
  return (
    <div style={{
      position: "relative",
      width: vertical ? 900 : 1360,
      height: vertical ? 830 : 520,
      fontFamily: SANS,
    }}>
      {cards.map((item, i) => (
        <div key={`${item}-${i}`} style={{
          position: "absolute",
          left: vertical ? 55 + (i % 2) * 405 : 20 + (i % 5) * 255,
          top: vertical ? 20 + Math.floor(i / 2) * 188 : 20 + Math.floor(i / 5) * 210,
          width: vertical ? 350 : 225,
          height: vertical ? 160 : 178,
          background: i % 3 === 0 ? "#1f262c" : "#eee7d8",
          color: i % 3 === 0 ? "#f7fbff" : INK,
          borderRadius: 6,
          border: "1px solid rgba(255,255,255,0.18)",
          boxShadow: "0 20px 56px rgba(0,0,0,0.36)",
          padding: 18,
          transform: `rotate(${[-3, 2, -1, 3, -2][i % 5]}deg)`,
        }}>
          <div style={{ color, fontSize: 18, fontWeight: 950 }}>截图 {String(i + 1).padStart(2, "0")}</div>
          <div style={{ marginTop: 18, fontSize: vertical ? 28 : 24, fontWeight: 950 }}>{item}</div>
          <div style={{ position: "absolute", left: 18, right: 18, bottom: 18, height: 8, background: "currentColor", opacity: 0.18 }} />
        </div>
      ))}
      <div style={{
        position: "absolute",
        right: vertical ? 60 : 38,
        bottom: vertical ? 34 : 18,
        width: vertical ? 380 : 410,
        background: "rgba(12,13,14,0.86)",
        border: `2px solid ${color}`,
        boxShadow: `0 0 34px ${color}55`,
        padding: "26px 30px",
        color: FG,
        fontSize: vertical ? 31 : 30,
        fontWeight: 950,
      }}>
        必须补：总人数 / 中位数 / 净结果
      </div>
    </div>
  );
};

const CashflowTracks: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const color = scene.accent ?? BLUE;
  const tracks = ["AI 课", "加盟", "供应链"];
  const chunks = tracks.map((track, i) => ({
    track,
    nodes: scene.items.filter((_, idx) => idx % 3 === i).slice(0, 4),
  }));
  return (
    <div style={{ width: vertical ? 900 : 1360, height: vertical ? 820 : 510, fontFamily: SANS }}>
      {chunks.map((track, ti) => (
        <div key={track.track} style={{
          position: "relative",
          height: vertical ? 245 : 142,
          marginBottom: vertical ? 22 : 22,
          borderLeft: `8px solid ${[BLUE, GOLD, RED][ti]}`,
          background: ti % 2 ? "rgba(244,239,228,0.92)" : "rgba(29,36,42,0.92)",
          color: ti % 2 ? INK : FG,
          boxShadow: "0 22px 58px rgba(0,0,0,0.34)",
          padding: vertical ? "22px 26px" : "18px 28px",
        }}>
          <div style={{ fontSize: vertical ? 31 : 27, color: [BLUE, GOLD, RED][ti], fontWeight: 950, marginBottom: 16 }}>{track.track}</div>
          <div style={{ display: "flex", gap: vertical ? 14 : 18, flexWrap: "wrap", alignItems: "center" }}>
            {(track.nodes.length ? track.nodes : scene.items.slice(ti, ti + 3)).map((node, i) => (
              <div key={`${node}-${i}`} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{
                  minWidth: vertical ? 160 : 170,
                  padding: vertical ? "13px 16px" : "12px 18px",
                  background: ti % 2 ? "rgba(0,0,0,0.06)" : "rgba(255,255,255,0.08)",
                  border: "1px solid rgba(255,255,255,0.18)",
                  borderRadius: 6,
                  fontSize: vertical ? 26 : 25,
                  fontWeight: 900,
                }}>{node}</div>
                {i < track.nodes.length - 1 && <div style={{ color, fontSize: 28, fontWeight: 950 }}>→</div>}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

const FulfillmentMismatch: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const color = scene.accent ?? RED;
  const cols = [
    { title: "直播间拍到", items: ["样品特写", "主播演示", "下单口令"], bg: "#1f262c", fg: FG },
    { title: "页面写到", items: ["套餐图", "规格表", "售后入口"], bg: "#efe7d6", fg: INK },
    { title: "实际收到", items: ["批次不同", "赠品变更", "补差价"], bg: "#2b201e", fg: FG },
  ];
  return (
    <div style={{
      position: "relative",
      width: vertical ? 900 : 1360,
      height: vertical ? 820 : 520,
      fontFamily: SANS,
      display: "grid",
      gridTemplateColumns: vertical ? "1fr" : "repeat(3, 1fr)",
      gap: vertical ? 18 : 22,
    }}>
      {cols.map((col, ci) => (
        <div key={col.title} style={{
          position: "relative",
          background: col.bg,
          color: col.fg,
          borderRadius: 8,
          boxShadow: "0 28px 90px rgba(0,0,0,0.44)",
          border: `1px solid ${ci === 2 ? color : "rgba(255,255,255,0.18)"}`,
          overflow: "hidden",
          padding: vertical ? 32 : 34,
          minHeight: vertical ? 240 : 520,
        }}>
          <div style={{ fontSize: vertical ? 33 : 34, fontWeight: 950, color: ci === 2 ? color : ci === 1 ? INK : BLUE, marginBottom: 28 }}>
            {col.title}
          </div>
          {col.items.map((item, i) => (
            <div key={item} style={{
              height: vertical ? 48 : 64,
              marginBottom: 12,
              borderBottom: "1px solid rgba(255,255,255,0.18)",
              fontSize: vertical ? 30 : 30,
              fontWeight: 900,
              display: "flex",
              alignItems: "center",
            }}>{item}</div>
          ))}
          <div style={{
            position: "absolute",
            left: 28,
            right: 28,
            bottom: 28,
            height: vertical ? 78 : 108,
            border: ci === 2 ? `6px solid ${color}` : "1px solid rgba(255,255,255,0.14)",
            background: ci === 0 ? "rgba(255,255,255,0.08)" : ci === 1 ? "rgba(0,0,0,0.06)" : "rgba(217,74,58,0.12)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: vertical ? 26 : 27,
            fontWeight: 950,
          }}>
            {ci === 0 ? "镜头里的一份" : ci === 1 ? "页面上的一份" : "到手后的一份"}
          </div>
        </div>
      ))}
      <div style={{
        position: "absolute",
        left: vertical ? 30 : 350,
        right: vertical ? 30 : 350,
        bottom: vertical ? -88 : -72,
        padding: "18px 26px",
        background: "#171717",
        color: "#fff",
        fontSize: vertical ? 28 : 28,
        fontWeight: 950,
        textAlign: "center",
        boxShadow: "0 18px 50px rgba(0,0,0,0.45)",
      }}>三处材料无法逐项对齐</div>
    </div>
  );
};

const ContractZoom: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const color = scene.accent ?? RED;
  const items = scene.items.slice(0, 6);
  return (
    <div style={{
      position: "relative",
      width: vertical ? 900 : 1360,
      height: vertical ? 820 : 520,
      background: "#efe7d6",
      color: INK,
      borderRadius: 8,
      boxShadow: "0 28px 90px rgba(0,0,0,0.44)",
      fontFamily: SANS,
      overflow: "hidden",
      padding: vertical ? 44 : 52,
    }}>
      <div style={{ fontSize: vertical ? 44 : 46, fontWeight: 950, marginBottom: 30 }}>页面承诺 / 可核验清单</div>
      {items.map((item, i) => (
        <div key={item} style={{
          position: "relative",
          height: vertical ? 92 : 58,
          marginBottom: vertical ? 15 : 12,
          borderBottom: "1px solid rgba(30,24,18,0.18)",
          fontSize: vertical ? 31 : 27,
          fontWeight: 850,
          display: "flex",
          alignItems: "center",
        }}>
          <span>{item}</span>
          {(i === 0 || i === 3 || item.includes("规格") || item.includes("口径")) && (
            <div style={{
              position: "absolute",
              left: vertical ? 0 : 430,
              right: vertical ? 0 : 40,
              top: 7,
              bottom: 7,
              border: `5px solid ${color}`,
              boxShadow: `0 0 20px ${color}44`,
            }} />
          )}
        </div>
      ))}
      <div style={{
        position: "absolute",
        right: vertical ? 42 : 54,
        bottom: vertical ? 42 : 44,
        padding: "18px 26px",
        background: "#171717",
        color: "#fff",
        fontSize: vertical ? 30 : 28,
        fontWeight: 950,
      }}>页面怎么说，到手怎么核</div>
    </div>
  );
};

const BoundaryLadder: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const color = scene.accent ?? BLUE;
  return (
    <div style={{ width: vertical ? 900 : 1280, height: vertical ? 820 : 500, fontFamily: SANS }}>
      {scene.items.map((item, i) => (
        <div key={item} style={{
          marginLeft: vertical ? 0 : i * 90,
          marginTop: vertical ? 26 : i === 0 ? 0 : -12,
          width: vertical ? 850 : 840,
          height: vertical ? 150 : 96,
          background: i < 2 ? "rgba(244,239,228,0.94)" : "rgba(31,36,41,0.96)",
          color: i < 2 ? INK : FG,
          borderLeft: `10px solid ${[GREEN, BLUE, GOLD, RED][i] ?? color}`,
          boxShadow: "0 20px 56px rgba(0,0,0,0.34)",
          display: "flex",
          alignItems: "center",
          padding: "0 34px",
          fontSize: vertical ? 34 : 34,
          fontWeight: 950,
        }}>
          <span style={{ color: [GREEN, BLUE, GOLD, RED][i] ?? color, marginRight: 24 }}>{String(i + 1).padStart(2, "0")}</span>
          {item}
        </div>
      ))}
    </div>
  );
};

const ChecklistBoard: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const color = scene.accent ?? BLUE;
  return (
    <div style={{
      width: vertical ? 900 : 1260,
      minHeight: vertical ? 620 : 430,
      display: "grid",
      gridTemplateColumns: vertical ? "1fr" : "repeat(2, 1fr)",
      gap: 18,
      fontFamily: SANS,
    }}>
      {scene.items.map((item, i) => (
        <div key={item} style={{
          background: i % 2 ? "rgba(31,36,42,0.95)" : "rgba(244,239,228,0.95)",
          color: i % 2 ? FG : INK,
          borderRadius: 8,
          border: `1px solid ${color}66`,
          boxShadow: "0 18px 50px rgba(0,0,0,0.32)",
          padding: vertical ? "26px 30px" : "22px 28px",
          fontSize: vertical ? 32 : 30,
          fontWeight: 900,
          display: "flex",
          alignItems: "center",
          gap: 18,
        }}>
          <span style={{
            width: 40,
            height: 40,
            borderRadius: "50%",
            background: color,
            color: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 22,
          }}>{i + 1}</span>
          {item}
        </div>
      ))}
    </div>
  );
};

const EvidenceCollage: React.FC<{ scene: Scene; vertical?: boolean; withPresenter?: boolean }> = ({ scene, vertical, withPresenter }) => {
  const color = scene.accent ?? BLUE;
  const items = scene.items.slice(0, vertical ? 5 : 6);
  return (
    <div style={{
      position: "relative",
      width: vertical ? 920 : 1420,
      height: vertical ? 900 : 620,
      marginTop: vertical ? 26 : 20,
    }}>
      <NetworkLines count={items.length} color={color} vertical={vertical} />
      {items.map((item, i) => {
        const positions = vertical
          ? [
              [80, 10], [500, 105], [120, 325], [520, 500], [170, 650],
            ]
          : [
              [20, 44], [455, 12], [890, 66], [180, 330], [630, 360], [1050, 318],
            ];
        const [left, top] = positions[i] ?? [80 + i * 90, 90 + i * 70];
        return (
          <div key={`${item}-${i}`} style={{ position: "absolute", left, top }}>
            <FloatingEvidenceCard text={item} index={i} color={color} vertical={vertical} dense={scene.kind === "flow"} />
          </div>
        );
      })}
      {withPresenter && (
        <div style={{ position: "absolute", right: vertical ? 44 : 30, bottom: vertical ? 10 : 14, width: vertical ? 240 : 270, height: vertical ? 240 : 270 }}>
          <PresenterWindow compact vertical={vertical} />
        </div>
      )}
    </div>
  );
};

type OpeningBeatKind = "concept" | "phone" | "form" | "contract" | "chat" | "network" | "materials" | "question";

type OpeningBeat = {
  kind: OpeningBeatKind;
  seconds: number;
  title: string;
  kicker: string;
  items: string[];
  accent: string;
};

const openingBeatPlans: Record<number, OpeningBeat[]> = {
  1: [
    { kind: "concept", seconds: 2.35, title: "你刷到过这种东西吗？", kicker: "OPEN 01", items: ["9.9 体验课", "1 元鸡蛋", "低价加盟", "高薪兼职"], accent: BLUE },
    { kind: "phone", seconds: 2.25, title: "9.9 只是入口", kicker: "直播间 / 体验课", items: ["限时 9.9", "评论区留 1", "进群领资料"], accent: GOLD },
    { kind: "form", seconds: 2.2, title: "低价换登记", kicker: "社区活动 / 表单", items: ["姓名", "电话", "住址", "社群"], accent: GREEN },
    { kind: "question", seconds: 1.2, title: "它先拿到什么？", kicker: "问题先放这里", items: ["点击", "留资", "加群"], accent: RED },
  ],
  2: [
    { kind: "contract", seconds: 2.4, title: "低价加盟", kicker: "合同桌面", items: ["加盟费", "设备", "原料", "装修"], accent: GOLD },
    { kind: "chat", seconds: 2.35, title: "高薪兼职", kicker: "招聘页 / 聊天框", items: ["面试", "能力不足", "培训合同", "分期"], accent: RED },
    { kind: "network", seconds: 3.1, title: "四个入口，动作一样", kicker: "点击到付款", items: ["点击", "停留", "留资", "加群", "付款", "续费"], accent: BLUE },
    { kind: "phone", seconds: 2.35, title: "第一笔钱不完整", kicker: "页面只显示当前价", items: ["体验价", "基础课", "工具费"], accent: GREEN },
    { kind: "question", seconds: 1.4, title: "后面接什么？", kicker: "先看现金流", items: ["谁收钱", "收几次", "退出要什么"], accent: GOLD },
  ],
  3: [
    { kind: "materials", seconds: 3.0, title: "材料可以很完整", kicker: "直播 / 老师 / 合同 / 案例", items: ["直播", "老师", "合同", "成功案例", "付款链接"], accent: BLUE },
    { kind: "network", seconds: 3.0, title: "但关键数字没出现", kicker: "案例不是概率", items: ["总人数", "中位数", "失败者", "净利润"], accent: RED },
    { kind: "contract", seconds: 2.8, title: "合同写的是责任", kicker: "承诺旁边看条件", items: ["退款条件", "交付清单", "续费维护", "违约条款"], accent: GOLD },
    { kind: "form", seconds: 2.45, title: "页面写到，不等于到手对齐", kicker: "展示 / 下单 / 到手", items: ["样品特写", "套餐图", "批次不同"], accent: GREEN },
    { kind: "question", seconds: 3.1, title: "如果我失败了，\n它已经赚了什么？", kicker: "主问题", items: ["学费", "设备", "原料", "软件"], accent: RED },
  ],
};

const OpeningLabel: React.FC<{ children: string; color: string; small?: boolean }> = ({ children, color, small }) => (
  <div style={{
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    height: small ? 42 : 52,
    padding: small ? "0 16px" : "0 22px",
    background: "rgba(255,255,255,0.08)",
    border: `1px solid ${color}88`,
    color: small ? "#efe8da" : color,
    fontFamily: SANS,
    fontSize: small ? 21 : 27,
    fontWeight: 950,
    boxShadow: `0 0 28px ${color}22`,
  }}>
    {children}
  </div>
);

const OpeningTitle: React.FC<{ beat: OpeningBeat; vertical?: boolean; align?: "left" | "center" }> = ({ beat, vertical, align = "left" }) => (
  <div style={{ fontFamily: SANS, color: FG, textAlign: align }}>
    <div style={{
      color: beat.accent,
      fontSize: vertical ? 22 : 22,
      fontWeight: 950,
      letterSpacing: 2,
      marginBottom: vertical ? 16 : 18,
    }}>{beat.kicker}</div>
    {beat.title.split("\n").map((line) => (
      <div key={line} style={{
        fontSize: vertical ? 64 : 76,
        lineHeight: 1.04,
        fontWeight: 950,
        textShadow: `0 5px 0 rgba(0,0,0,0.36), 0 0 44px ${beat.accent}44`,
        whiteSpace: vertical ? "normal" : "nowrap",
      }}>{line}</div>
    ))}
  </div>
);

const OpeningPhone: React.FC<{ beat: OpeningBeat; frame: number; vertical?: boolean }> = ({ beat, frame, vertical }) => {
  const y = Math.sin(frame / 28) * 10;
  return (
    <div style={{
      position: "absolute",
      left: vertical ? 88 : 180,
      top: vertical ? 265 : 172,
      width: vertical ? 455 : 420,
      height: vertical ? 710 : 650,
      borderRadius: 40,
      background: "#101418",
      border: "10px solid #252b31",
      boxShadow: "0 40px 120px rgba(0,0,0,0.58)",
      padding: 28,
      translate: `0 ${y}px`,
      fontFamily: SANS,
      color: FG,
    }}>
      <div style={{ height: 44, borderRadius: 20, background: "#07090b", margin: "0 auto 28px", width: "42%" }} />
      <div style={{ background: "#efe7d6", color: INK, borderRadius: 12, padding: 22, height: vertical ? 515 : 455 }}>
        <div style={{ color: beat.accent, fontSize: 24, fontWeight: 950 }}>LIVE</div>
        <div style={{ marginTop: 22, fontSize: vertical ? 48 : 46, fontWeight: 950, lineHeight: 1.05 }}>{beat.items[0]}</div>
        <div style={{ marginTop: 22, height: 92, background: "#1f262d", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 32, fontWeight: 950 }}>
          {beat.items[1] ?? "进群"}
        </div>
        {(beat.items.slice(2).length ? beat.items.slice(2) : ["领取资料", "付款链接"]).map((item, i) => (
          <div key={item} style={{
            marginTop: 18,
            height: 48,
            display: "flex",
            alignItems: "center",
            borderBottom: "1px solid rgba(25,20,16,0.18)",
            fontSize: 25,
            fontWeight: 850,
            opacity: fadeIn(frame, 8 + i * 5, 8),
          }}>{item}</div>
        ))}
      </div>
    </div>
  );
};

const OpeningForm: React.FC<{ beat: OpeningBeat; frame: number; vertical?: boolean }> = ({ beat, frame, vertical }) => {
  const scan = interpolate(frame % 80, [0, 80], [0, vertical ? 545 : 420]);
  return (
    <div style={{
      position: "absolute",
      left: vertical ? 72 : 148,
      top: vertical ? 310 : 170,
      width: vertical ? 720 : 845,
      height: vertical ? 620 : 510,
      background: CARD,
      color: INK,
      border: `1px solid ${beat.accent}88`,
      boxShadow: "0 36px 110px rgba(0,0,0,0.46)",
      fontFamily: SANS,
      padding: vertical ? 36 : 42,
      rotate: "-2deg",
    }}>
      <div style={{ color: beat.accent, fontSize: 24, fontWeight: 950, marginBottom: 26 }}>{beat.kicker}</div>
      <div style={{ fontSize: vertical ? 48 : 52, fontWeight: 950, marginBottom: 28 }}>{beat.title}</div>
      {beat.items.map((item, i) => (
        <div key={item} style={{
          height: vertical ? 75 : 63,
          display: "grid",
          gridTemplateColumns: "150px 1fr",
          alignItems: "center",
          borderTop: "1px solid rgba(25,20,16,0.16)",
          fontSize: vertical ? 30 : 28,
          fontWeight: 850,
        }}>
          <span style={{ color: MUTED }}>{String(i + 1).padStart(2, "0")}</span>
          <span>{item}</span>
        </div>
      ))}
      <div style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: scan,
        height: 4,
        background: beat.accent,
        opacity: 0.55,
        boxShadow: `0 0 30px ${beat.accent}`,
      }} />
    </div>
  );
};

const OpeningContract: React.FC<{ beat: OpeningBeat; frame: number; vertical?: boolean }> = ({ beat, frame, vertical }) => {
  const zoom = interpolate(frame, [0, 22], [0.96, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return (
    <div style={{
      position: "absolute",
      left: vertical ? 58 : 138,
      top: vertical ? 260 : 132,
      width: vertical ? 840 : 1050,
      height: vertical ? 690 : 600,
      scale: zoom,
      fontFamily: SANS,
    }}>
      {[0, 1, 2].map((i) => (
        <div key={i} style={{
          position: "absolute",
          left: vertical ? 30 + i * 42 : 40 + i * 185,
          top: vertical ? 56 + i * 58 : 38 + i * 42,
          width: vertical ? 610 : 635,
          height: vertical ? 480 : 475,
          background: i === 1 ? "#efe7d6" : "#f8f2e6",
          color: INK,
          boxShadow: "0 34px 100px rgba(0,0,0,0.42)",
          border: "1px solid rgba(35,28,20,0.18)",
          rotate: `${[-6, 1, 7][i]}deg`,
          padding: 34,
          opacity: i === 0 ? 0.74 : 1,
        }}>
          <div style={{ color: beat.accent, fontSize: 23, fontWeight: 950 }}>{i === 2 ? "费用清单" : beat.kicker}</div>
          <div style={{ marginTop: 20, fontSize: 42, lineHeight: 1.05, fontWeight: 950 }}>{i === 2 ? beat.title : "合作协议"}</div>
          {beat.items.slice(0, 4).map((item, row) => (
            <div key={item} style={{ marginTop: 22, height: 34, borderBottom: "1px solid rgba(25,20,16,0.18)", fontSize: 24, fontWeight: 850 }}>
              {item}
            </div>
          ))}
          {i === 2 && (
            <div style={{
              position: "absolute",
              right: 34,
              bottom: 34,
              width: 160,
              height: 82,
              border: `8px solid ${RED}`,
              color: RED,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 26,
              fontWeight: 950,
              rotate: "-8deg",
            }}>另计</div>
          )}
        </div>
      ))}
    </div>
  );
};

const OpeningChat: React.FC<{ beat: OpeningBeat; frame: number; vertical?: boolean }> = ({ beat, frame, vertical }) => {
  const items = beat.items.length ? beat.items : ["面试", "培训合同", "分期"];
  return (
    <div style={{
      position: "absolute",
      inset: vertical ? "260px 62px 150px" : "140px 150px 120px",
      display: "grid",
      gridTemplateColumns: vertical ? "1fr" : "0.95fr 1.05fr",
      gap: 38,
      fontFamily: SANS,
      color: FG,
    }}>
      <div style={{ background: "#11161b", border: "1px solid rgba(255,255,255,0.16)", boxShadow: "0 36px 100px rgba(0,0,0,0.48)", padding: 34 }}>
        <div style={{ color: beat.accent, fontSize: 24, fontWeight: 950, marginBottom: 28 }}>{beat.kicker}</div>
        {items.map((item, i) => (
          <div key={item} style={{
            marginLeft: i % 2 ? 90 : 0,
            marginBottom: 22,
            padding: "18px 24px",
            maxWidth: vertical ? 610 : 520,
            background: i % 2 ? "#efe7d6" : "#26313a",
            color: i % 2 ? INK : FG,
            fontSize: vertical ? 31 : 31,
            fontWeight: 900,
            opacity: fadeIn(frame, 5 + i * 6, 8),
          }}>{item}</div>
        ))}
      </div>
      <div style={{ position: "relative", background: CARD, color: INK, boxShadow: "0 36px 100px rgba(0,0,0,0.48)", padding: 42 }}>
        <div style={{ fontSize: vertical ? 54 : 64, lineHeight: 1.05, fontWeight: 950 }}>{beat.title}</div>
        {["月入过万", "推荐就业", "零基础可做"].map((item, i) => (
          <div key={item} style={{
            marginTop: i === 0 ? 34 : 18,
            width: i === 1 ? "72%" : "88%",
            height: 52,
            borderBottom: "1px solid rgba(25,20,16,0.18)",
            display: "flex",
            alignItems: "center",
            color: i === 0 ? RED : INK,
            fontSize: 30,
            fontWeight: 900,
            opacity: fadeIn(frame, 8 + i * 5, 8),
          }}>{item}</div>
        ))}
        <div style={{ position: "absolute", left: 42, right: 42, bottom: 44, height: 112, border: `6px solid ${RED}`, display: "flex", alignItems: "center", justifyContent: "center", color: RED, fontSize: 32, fontWeight: 950 }}>
          培训合同 / 分期账单
        </div>
      </div>
    </div>
  );
};

const OpeningNetwork: React.FC<{ beat: OpeningBeat; frame: number; vertical?: boolean }> = ({ beat, frame, vertical }) => {
  const centerX = vertical ? 540 : 960;
  const centerY = vertical ? 620 : 520;
  const positions = vertical
    ? [[170, 340], [690, 330], [140, 760], [710, 795], [320, 935], [540, 220]]
    : [[330, 260], [770, 190], [1270, 270], [430, 740], [920, 790], [1360, 650]];
  return (
    <div style={{ position: "absolute", inset: 0, fontFamily: SANS }}>
      <svg style={{ position: "absolute", inset: 0, opacity: 0.92 }}>
        {positions.slice(0, beat.items.length).map(([x, y], i) => (
          <line key={i} x1={x} y1={y} x2={centerX} y2={centerY} stroke={beat.accent} strokeWidth={5} strokeDasharray="16 12" opacity={fadeIn(frame, 5 + i * 3, 8)} />
        ))}
      </svg>
      <div style={{
        position: "absolute",
        left: centerX - (vertical ? 165 : 190),
        top: centerY - (vertical ? 72 : 86),
        width: vertical ? 330 : 380,
        height: vertical ? 144 : 172,
        background: "#0d1116",
        color: FG,
        border: `3px solid ${beat.accent}`,
        boxShadow: `0 0 56px ${beat.accent}66, 0 30px 90px rgba(0,0,0,0.5)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        fontSize: vertical ? 42 : 48,
        lineHeight: 1.05,
        fontWeight: 950,
      }}>{beat.title}</div>
      {beat.items.map((item, i) => {
        const [x, y] = positions[i] ?? positions[0];
        return (
          <div key={item} style={{
            position: "absolute",
            left: x - (vertical ? 105 : 120),
            top: y - 36,
            minWidth: vertical ? 210 : 240,
            minHeight: 72,
            padding: "0 22px",
            background: i % 2 ? CARD : "#202a32",
            color: i % 2 ? INK : FG,
            border: `1px solid ${beat.accent}66`,
            boxShadow: "0 22px 62px rgba(0,0,0,0.42)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: vertical ? 28 : 29,
            fontWeight: 950,
            opacity: fadeIn(frame, 5 + i * 4, 8),
          }}>{item}</div>
        );
      })}
    </div>
  );
};

const OpeningMaterials: React.FC<{ beat: OpeningBeat; frame: number; vertical?: boolean }> = ({ beat, frame, vertical }) => (
  <div style={{
    position: "absolute",
    inset: vertical ? "230px 64px 135px" : "135px 120px 110px",
    display: "grid",
    gridTemplateColumns: vertical ? "1fr" : "0.9fr 1.1fr",
    gap: 42,
    alignItems: "center",
    fontFamily: SANS,
  }}>
    <OpeningTitle beat={beat} vertical={vertical} />
    <div style={{ position: "relative", height: vertical ? 620 : 620 }}>
      {beat.items.map((item, i) => (
        <div key={item} style={{
          position: "absolute",
          left: vertical ? 95 + (i % 2) * 270 : [20, 300, 590, 185, 470][i],
          top: vertical ? 30 + Math.floor(i / 2) * 190 : [35, 0, 52, 305, 342][i],
          width: vertical ? 250 : 300,
          height: vertical ? 165 : 195,
          background: i % 2 ? CARD : "#202a32",
          color: i % 2 ? INK : FG,
          border: `1px solid ${beat.accent}66`,
          boxShadow: "0 30px 80px rgba(0,0,0,0.42)",
          padding: 24,
          rotate: `${[-5, 3, -2, 5, -4][i]}deg`,
          opacity: fadeIn(frame, 6 + i * 4, 8),
        }}>
          <div style={{ color: beat.accent, fontSize: 21, fontWeight: 950 }}>材料 {String(i + 1).padStart(2, "0")}</div>
          <div style={{ marginTop: 24, fontSize: vertical ? 32 : 34, fontWeight: 950 }}>{item}</div>
        </div>
      ))}
    </div>
  </div>
);

const OpeningQuestion: React.FC<{ beat: OpeningBeat; frame: number; vertical?: boolean }> = ({ beat, frame, vertical }) => {
  const pulse = 1 + Math.sin(frame / 18) * 0.012;
  return (
    <div style={{
      position: "absolute",
      inset: 0,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: SANS,
      color: FG,
      textAlign: "center",
      padding: vertical ? "0 70px" : "0 190px",
      background: "radial-gradient(circle at 50% 50%, rgba(217,74,58,0.2), transparent 48%)",
    }}>
      <OpeningLabel color={beat.accent}>{beat.kicker}</OpeningLabel>
      <div style={{
        marginTop: 34,
        fontSize: vertical ? 76 : 92,
        lineHeight: 1.05,
        fontWeight: 950,
        textShadow: `0 5px 0 rgba(0,0,0,0.44), 0 0 70px ${beat.accent}66`,
        scale: pulse,
      }}>
        {beat.title.split("\n").map((line) => <div key={line}>{line}</div>)}
      </div>
      <div style={{ marginTop: 42, display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center" }}>
        {beat.items.map((item) => <OpeningLabel key={item} color={beat.accent} small>{item}</OpeningLabel>)}
      </div>
    </div>
  );
};

const OpeningConcept: React.FC<{ beat: OpeningBeat; frame: number; vertical?: boolean }> = ({ beat, frame, vertical }) => {
  const positions = vertical
    ? [[110, 330], [650, 330], [95, 800], [655, 800]]
    : [[250, 260], [1330, 255], [345, 760], [1270, 760]];
  return (
    <div style={{ position: "absolute", inset: 0, fontFamily: SANS }}>
      <div style={{
        position: "absolute",
        left: vertical ? 86 : 260,
        right: vertical ? 86 : 260,
        top: vertical ? 465 : 325,
        textAlign: "center",
      }}>
        <OpeningTitle beat={beat} vertical={vertical} align="center" />
        <div style={{
          margin: "34px auto 0",
          width: vertical ? 520 : 720,
          height: 8,
          background: `linear-gradient(90deg, transparent, ${beat.accent}, ${GOLD}, transparent)`,
          boxShadow: `0 0 26px ${beat.accent}66`,
        }} />
      </div>
      {beat.items.map((item, i) => {
        const [left, top] = positions[i] ?? positions[0];
        return (
          <div key={item} style={{
            position: "absolute",
            left,
            top: top + Math.sin((frame + i * 20) / 30) * 8,
            width: vertical ? 260 : 310,
            height: vertical ? 96 : 112,
            background: i % 2 ? CARD : "#202a32",
            color: i % 2 ? INK : FG,
            border: `2px solid ${beat.accent}77`,
            boxShadow: "0 28px 80px rgba(0,0,0,0.44)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: vertical ? 30 : 34,
            fontWeight: 950,
            opacity: fadeIn(frame, 6 + i * 4, 8),
          }}>{item}</div>
        );
      })}
    </div>
  );
};

const OpeningVisual: React.FC<{ beat: OpeningBeat; frame: number; vertical?: boolean }> = ({ beat, frame, vertical }) => {
  if (beat.kind === "phone") return <OpeningPhone beat={beat} frame={frame} vertical={vertical} />;
  if (beat.kind === "form") return <OpeningForm beat={beat} frame={frame} vertical={vertical} />;
  if (beat.kind === "contract") return <OpeningContract beat={beat} frame={frame} vertical={vertical} />;
  if (beat.kind === "chat") return <OpeningChat beat={beat} frame={frame} vertical={vertical} />;
  if (beat.kind === "network") return <OpeningNetwork beat={beat} frame={frame} vertical={vertical} />;
  if (beat.kind === "materials") return <OpeningMaterials beat={beat} frame={frame} vertical={vertical} />;
  if (beat.kind === "question") return <OpeningQuestion beat={beat} frame={frame} vertical={vertical} />;
  return <OpeningConcept beat={beat} frame={frame} vertical={vertical} />;
};

const OpeningBeatScene: React.FC<{ scene: Scene; vertical?: boolean; showLowerCaption?: boolean }> = ({ scene, vertical, showLowerCaption }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const beats = openingBeatPlans[scene.id] ?? openingBeatPlans[1];
  const seconds = frame / fps;
  let cursor = 0;
  let beat = beats[beats.length - 1];
  let beatStart = 0;
  for (const candidate of beats) {
    if (seconds < cursor + candidate.seconds) {
      beat = candidate;
      beatStart = cursor;
      break;
    }
    cursor += candidate.seconds;
    beatStart = cursor;
  }
  const beatFrame = frame - Math.round(beatStart * fps);
  const cutFlash = interpolate(beatFrame, [0, 5], [0.22, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <BackdropTexture scene={{ ...scene, title: beat.title, items: beat.items, accent: beat.accent }} vertical={vertical} />
      <div style={{
        position: "absolute",
        top: vertical ? 70 : 45,
        left: vertical ? 56 : 72,
        right: vertical ? 56 : 72,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontFamily: SANS,
        fontSize: vertical ? 23 : 22,
        fontWeight: 950,
        letterSpacing: 2,
        color: MUTED,
      }}>
        <span style={{ color: beat.accent }}>{scene.chapter}</span>
        <span>{String(scene.id).padStart(2, "0")} / OPEN</span>
      </div>
      <OpeningVisual beat={beat} frame={beatFrame} vertical={vertical} />
      {(beat.kind === "concept" || beat.kind === "network" || beat.kind === "materials") && <PresenterWindow compact vertical={vertical} />}
      <div style={{
        position: "absolute",
        inset: 0,
        background: beat.accent,
        opacity: cutFlash,
        pointerEvents: "none",
      }} />
      <div style={{
        position: "absolute",
        left: vertical ? 58 : 74,
        bottom: vertical ? 54 : 48,
        width: vertical ? 280 : 380,
        height: 5,
        background: `linear-gradient(90deg, ${beat.accent}, transparent)`,
        opacity: 0.85,
      }} />
      {showLowerCaption && <LowerCaption text={scene.subtitle ?? scene.title} vertical={vertical} />}
    </AbsoluteFill>
  );
};

const CompareScene: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const frame = useCurrentFrame();
  const mid = Math.ceil(scene.items.length / 2);
  const left = scene.items.slice(0, mid);
  const right = scene.items.slice(mid);
  const color = scene.accent ?? BLUE;
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: vertical ? "1fr" : "1fr 1fr",
      gap: 26,
      width: vertical ? 820 : 1360,
    }}>
      {[left, right].map((list, idx) => (
        <div key={idx} style={{
          background: idx === 0 ? "rgba(244,239,228,0.96)" : "rgba(30,36,42,0.96)",
          border: `1px solid ${idx === 0 ? BLUE : color}55`,
          borderRadius: 8,
          padding: vertical ? 28 : 34,
          minHeight: vertical ? 260 : 320,
          boxShadow: "0 24px 70px rgba(0,0,0,0.34)",
        }}>
          <div style={{ fontFamily: SANS, color: idx === 0 ? BLUE : color, fontSize: vertical ? 26 : 24, fontWeight: 900, marginBottom: 22 }}>
            {idx === 0 ? "买方看到 / 当前动作" : "后续条件 / 卖方收入"}
          </div>
          {list.map((item, i) => (
            <div key={item} style={{
              fontFamily: SANS,
              fontSize: vertical ? 31 : 34,
              color: idx === 0 ? INK : FG,
              fontWeight: 800,
              marginTop: 14,
              opacity: fadeIn(frame, 8 + (idx * mid + i) * 5, 10),
            }}>
              {item}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

const TableScene: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  const frame = useCurrentFrame();
  const color = scene.accent ?? BLUE;
  return (
    <div style={{ width: vertical ? 840 : 1320, background: "rgba(244,239,228,0.96)", border: `1px solid ${color}66`, borderRadius: 8, overflow: "hidden", boxShadow: "0 28px 80px rgba(0,0,0,0.4)" }}>
      {scene.items.map((item, i) => (
        <div key={`${item}-${i}`} style={{
          display: "flex",
          alignItems: "center",
          minHeight: vertical ? 72 : 66,
          padding: vertical ? "0 28px" : "0 34px",
          borderTop: i === 0 ? "none" : "1px solid rgba(35,28,22,0.16)",
          background: i % 2 === 0 ? "rgba(25,23,20,0.045)" : "transparent",
          opacity: fadeIn(frame, 8 + i * 4, 8),
        }}>
          <span style={{ fontFamily: SANS, fontSize: vertical ? 30 : 32, color: item.includes("-") || item.includes("未展示") ? RED : INK, fontWeight: 850 }}>
            {item}
          </span>
        </div>
      ))}
    </div>
  );
};

const SceneBody: React.FC<{ scene: Scene; vertical?: boolean }> = ({ scene, vertical }) => {
  if (scene.id === 6) return <BoundaryLadder scene={scene} vertical={vertical} />;
  if (scene.id === 10 || scene.id === 19 || scene.id === 20) return <ScreenshotWall scene={scene} vertical={vertical} />;
  if ([23, 24, 26, 28, 31].includes(scene.id)) return <CashflowTracks scene={scene} vertical={vertical} />;
  if (scene.id === 30) return <FulfillmentMismatch scene={scene} vertical={vertical} />;
  if (scene.id === 36) return <ContractZoom scene={scene} vertical={vertical} />;
  if (scene.kind === "flow") return <FlowTimeline scene={scene} vertical={vertical} />;
  if (scene.kind === "question") return <ChecklistBoard scene={scene} vertical={vertical} />;
  if (scene.kind === "compare") return <CompareScene scene={scene} vertical={vertical} />;
  if (scene.kind === "table") return <TableScene scene={scene} vertical={vertical} />;
  return <EvidenceCollage scene={scene} vertical={vertical} withPresenter={scene.kind === "title" || scene.kind === "grid"} />;
};

const DossierScene: React.FC<{ scene: Scene; vertical?: boolean; showLowerCaption?: boolean }> = ({ scene, vertical, showLowerCaption }) => {
  const color = scene.accent ?? BLUE;
  const presenterSide = scene.kind === "compare" || scene.kind === "table" ? "left" : "right";
  const needsLargePresenter = scene.kind === "compare" || scene.kind === "table";
  return (
    <AbsoluteFill>
      <BackdropTexture scene={scene} vertical={vertical} />
      <Header scene={scene} vertical={vertical} />
      {!needsLargePresenter && <PresenterWindow compact vertical={vertical} />}
      {needsLargePresenter && <PresenterWindow side={presenterSide} vertical={vertical} />}
      <div style={{
        position: "absolute",
        top: vertical ? 145 : 116,
        left: vertical ? 58 : needsLargePresenter ? 560 : 120,
        right: vertical ? 58 : 110,
      }}>
        <SceneTitle scene={scene} vertical={vertical} />
      </div>
      <div style={{
        position: "absolute",
        left: vertical ? 54 : needsLargePresenter ? 540 : 250,
        right: vertical ? 54 : 90,
        top: vertical ? 330 : needsLargePresenter ? 340 : 310,
        display: "flex",
        justifyContent: "center",
      }}>
        <SceneBody scene={scene} vertical={vertical} />
      </div>
      <div style={{
        position: "absolute",
        left: vertical ? 58 : 88,
        top: vertical ? 104 : 88,
        width: vertical ? 92 : 118,
        height: 5,
        background: color,
        boxShadow: `0 0 24px ${color}`,
      }} />
      {showLowerCaption && <LowerCaption text={scene.subtitle ?? scene.title} vertical={vertical} />}
    </AbsoluteFill>
  );
};

const TitleCollageScene: React.FC<{ scene: Scene; vertical?: boolean; showLowerCaption?: boolean }> = ({ scene, vertical, showLowerCaption }) => {
  const frame = useCurrentFrame();
  const y = interpolate(frame, [0, 18], [28, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill style={{ transform: `translateY(${y}px)` }}>
      <BackdropTexture scene={scene} vertical={vertical} />
      <Header scene={scene} vertical={vertical} />
      <div style={{
        position: "absolute",
        inset: vertical ? "180px 54px 180px" : "155px 110px 135px",
        display: "grid",
        gridTemplateColumns: vertical ? "1fr" : "1fr 1.2fr",
        gap: vertical ? 22 : 48,
        alignItems: "center",
      }}>
        <EvidenceCollage scene={scene} vertical={vertical} />
        <div style={{
          order: vertical ? -1 : 0,
          background: "linear-gradient(180deg, rgba(15,13,11,0.65), rgba(15,13,11,0.18))",
          borderLeft: `8px solid ${scene.accent ?? BLUE}`,
          padding: vertical ? "28px 0 26px 28px" : "36px 0 36px 42px",
        }}>
          <SceneTitle scene={scene} vertical={vertical} />
        </div>
      </div>
      <PresenterWindow compact vertical={vertical} />
      {showLowerCaption && <LowerCaption text={scene.subtitle ?? scene.title} vertical={vertical} />}
    </AbsoluteFill>
  );
};

const SceneCard: React.FC<{ scene: Scene; vertical?: boolean; showLowerCaption?: boolean }> = ({ scene, vertical, showLowerCaption }) => {
  if (scene.id <= 3) {
    return <OpeningBeatScene scene={scene} vertical={vertical} showLowerCaption={showLowerCaption} />;
  }
  if (scene.kind === "title" || scene.id <= 5) {
    return <TitleCollageScene scene={scene} vertical={vertical} showLowerCaption={showLowerCaption} />;
  }
  return <DossierScene scene={scene} vertical={vertical} showLowerCaption={showLowerCaption} />;
};

export const informationGapBaseSeconds = 1800;
export const informationGapNarrationSeconds = 1380.098;

export const InformationGap: React.FC<{ vertical?: boolean; timelineSeconds?: number; withAudio?: boolean; showLowerCaption?: boolean }> = ({
  vertical = false,
  timelineSeconds = informationGapBaseSeconds,
  withAudio = false,
  showLowerCaption = false,
}) => {
  const totalFrames = Math.ceil(timelineSeconds * FPS);
  const sceneScale = timelineSeconds / informationGapBaseSeconds;
  return (
    <AbsoluteFill style={{ background: BG }}>
      <Progress totalFrames={totalFrames} />
      {withAudio && <Audio src={staticFile("audio/information-gap-nahida-sovits-mix.wav")} />}
      {scenes.map((scene) => (
        <Sequence
          key={scene.id}
          from={Math.round(scene.start * sceneScale * FPS)}
          durationInFrames={Math.round((scene.end - scene.start) * sceneScale * FPS) + 8}
        >
          <SceneCard scene={scene} vertical={vertical} showLowerCaption={showLowerCaption} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

export const informationGapDurationFrames = informationGapBaseSeconds * FPS;
export const informationGapNarrationDurationFrames = Math.ceil(informationGapNarrationSeconds * FPS);
