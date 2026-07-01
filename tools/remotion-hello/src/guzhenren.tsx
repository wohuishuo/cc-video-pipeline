import {
  AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig,
  interpolate, spring, Easing,
} from "remotion";

const FPS = 30;
// 配音时间轴(秒)，与 narration 对齐
const LINES = [
  { s: 0.0, e: 4.2, t: "几十万读者，追着一个反派，看了快十年。" },
  { s: 4.6, e: 9.9, t: "他自私、冷血，为了变强什么都做得出来——他叫方源。" },
  { s: 10.2, e: 17.0, t: "《蛊真人》一句话：网文里恶人主角的天花板，让你忍不住替一个坏人叫好。" },
  { s: 17.4, e: 24.2, t: "蛊师把天地万物炼成蛊虫，养在体内，换取力量。" },
  { s: 24.6, e: 29.6, t: "而方源，带着五百年的记忆，重生回了一切的起点。" },
];

const RED = "#C8302B";
const JADE = "#3FB68B";
const GOLD = "#C9A24B";
const INK = "#0a0a0c";
const SERIF = '"KaiTi","STKaiti","Microsoft YaHei",serif';
const SANS = '"Microsoft YaHei","SimHei",sans-serif';

// ── 漂浮孢子粒子背景 ──
const Spores: React.FC = () => {
  const frame = useCurrentFrame();
  const dots = Array.from({ length: 42 }, (_, i) => {
    const seed = i * 97.13;
    const x = (Math.sin(seed) * 0.5 + 0.5) * 1920;
    const baseY = (Math.cos(seed * 1.7) * 0.5 + 0.5) * 1080;
    const y = (baseY - frame * (0.3 + (i % 5) * 0.15)) % 1080;
    const yy = y < 0 ? y + 1080 : y;
    const r = 1 + (i % 4);
    const op = 0.06 + 0.12 * (Math.sin(frame * 0.03 + seed) * 0.5 + 0.5);
    return (
      <circle key={i} cx={x} cy={yy} r={r} fill={JADE} opacity={op} />
    );
  });
  return (
    <svg width={1920} height={1080} style={{ position: "absolute" }}>
      {dots}
    </svg>
  );
};

const Vignette: React.FC = () => (
  <AbsoluteFill style={{
    background: `radial-gradient(ellipse 70% 60% at 50% 45%, rgba(40,30,20,0.35), ${INK} 75%)`,
  }} />
);

// 同步字幕（下三分之一）
const Captions: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const cur = LINES.find((l) => t >= l.s && t <= l.e + 0.3);
  if (!cur) return null;
  const local = t - cur.s;
  const op = interpolate(local, [0, 0.25], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", bottom: 70, width: "100%", textAlign: "center",
      opacity: op,
    }}>
      <span style={{
        fontFamily: SANS, fontSize: 38, color: "#fff", fontWeight: 600,
        background: "rgba(0,0,0,0.45)", padding: "8px 22px", borderRadius: 8,
        textShadow: "0 2px 8px rgba(0,0,0,0.8)", letterSpacing: 1,
      }}>{cur.t}</span>
    </div>
  );
};

// 印章盖章效果
const Seal: React.FC<{ char: string; delay: number; x: number; y: number }> = ({ char, delay, x, y }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { mass: 0.6, damping: 9, stiffness: 180 }, from: 0, to: 1 });
  const op = interpolate(frame - delay, [0, 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", left: x, top: y, transform: `scale(${1.4 - 0.4 * s}) rotate(-6deg)`,
      opacity: op,
    }}>
      <div style={{
        fontFamily: SERIF, fontSize: 70, color: "#fff", fontWeight: 700,
        background: RED, width: 110, height: 110, display: "flex",
        alignItems: "center", justifyContent: "center", borderRadius: 10,
        border: "4px solid rgba(255,255,255,0.85)", boxShadow: "0 0 30px rgba(200,48,43,0.6)",
      }}>{char}</div>
    </div>
  );
};

const Big: React.FC<{ children: React.ReactNode; size: number; color?: string; delay?: number; font?: string; glow?: string }> =
  ({ children, size, color = "#fff", delay = 0, font = SANS, glow }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();
    const s = spring({ frame: frame - delay, fps, config: { damping: 12, mass: 0.8 }, from: 0, to: 1 });
    const op = interpolate(frame - delay, [0, 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    return (
      <div style={{
        fontFamily: font, fontSize: size, color, fontWeight: 800, lineHeight: 1.15,
        transform: `translateY(${(1 - s) * 40}px) scale(${0.9 + 0.1 * s})`, opacity: op,
        textShadow: glow ? `0 0 40px ${glow}` : "0 4px 16px rgba(0,0,0,0.7)", textAlign: "center",
      }}>{children}</div>
    );
  };

// ── 场景 ──
const S1: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 10 }}>
    <Big size={46} color="#aaa" delay={0}>几十万读者，追着一个</Big>
    <Big size={170} color={RED} delay={12} font={SERIF} glow="rgba(200,48,43,0.6)">反 派</Big>
    <Big size={56} color={GOLD} delay={28}>看了快十年</Big>
  </AbsoluteFill>
);

const S2: React.FC = () => {
  const frame = useCurrentFrame();
  const slideL = interpolate(frame, [0, 18], [-300, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const slideR = interpolate(frame, [0, 18], [300, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
      <div style={{ display: "flex", gap: 60, marginBottom: 30 }}>
        <span style={{ fontFamily: SERIF, fontSize: 90, color: "#fff", transform: `translateX(${slideL}px)`, fontWeight: 800 }}>自私</span>
        <span style={{ fontFamily: SERIF, fontSize: 90, color: JADE, transform: `translateX(${slideR}px)`, fontWeight: 800 }}>冷血</span>
      </div>
      <Big size={56} color="#ddd" delay={40}>为了变强，什么都做得出来</Big>
      <div style={{ marginTop: 24 }}><Big size={120} color={RED} delay={62} font={SERIF} glow="rgba(200,48,43,0.7)">他叫 方源</Big></div>
    </AbsoluteFill>
  );
};

const S3: React.FC = () => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
    <Seal char="蛊" delay={6} x={760} y={170} />
    <div style={{ height: 160 }} />
    <Big size={210} color="#fff" delay={20} font={SERIF} glow="rgba(201,162,75,0.5)">蛊 真 人</Big>
    <div style={{ marginTop: 40 }}>
      <Big size={62} color={GOLD} delay={48}>恶人主角 · 天花板</Big>
    </div>
  </AbsoluteFill>
);

const S4: React.FC = () => {
  const items = ["蛊师", "炼蛊虫", "养于体内", "换取力量"];
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
      <Big size={240} color={JADE} delay={0} font={SERIF} glow="rgba(63,182,139,0.5)">蛊</Big>
      <div style={{ display: "flex", gap: 28, marginTop: 50 }}>
        {items.map((it, i) => {
          const frame = useCurrentFrame();
          const op = interpolate(frame, [20 + i * 14, 30 + i * 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const y = interpolate(frame, [20 + i * 14, 30 + i * 14], [20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <span key={i} style={{
              fontFamily: SANS, fontSize: 48, color: "#fff", fontWeight: 700,
              padding: "12px 26px", border: `2px solid ${JADE}`, borderRadius: 10,
              opacity: op, transform: `translateY(${y}px)`,
            }}>{it}</span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const S5: React.FC = () => {
  const frame = useCurrentFrame();
  const rot = interpolate(frame, [0, 60], [0, -340], { easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
      <svg width={260} height={260} style={{ position: "absolute", top: 120, opacity: 0.5 }}>
        <g transform={`rotate(${rot} 130 130)`}>
          <path d="M130 30 A100 100 0 1 1 60 60" fill="none" stroke={GOLD} strokeWidth={6} />
          <polygon points="60,40 60,80 95,60" fill={GOLD} />
        </g>
      </svg>
      <div style={{ height: 120 }} />
      <Big size={150} color={GOLD} delay={4} font={SERIF} glow="rgba(201,162,75,0.6)">五百年记忆</Big>
      <Big size={90} color="#fff" delay={26} font={SERIF}>重生 · 回到起点</Big>
      <div style={{ marginTop: 30 }}><Big size={40} color="#888" delay={50}>—— 一切，才刚刚开始</Big></div>
    </AbsoluteFill>
  );
};

export const GuZhenRen: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Vignette />
      <Spores />
      <Sequence from={0} durationInFrames={138}><S1 /></Sequence>
      <Sequence from={138} durationInFrames={168}><S2 /></Sequence>
      <Sequence from={306} durationInFrames={216}><S3 /></Sequence>
      <Sequence from={522} durationInFrames={216}><S4 /></Sequence>
      <Sequence from={738} durationInFrames={162}><S5 /></Sequence>
      <Captions />
      <div style={{ position: "absolute", top: 36, right: 48, fontFamily: SERIF, fontSize: 30, color: "rgba(255,255,255,0.5)", letterSpacing: 2 }}>蛊真人 · 网文拆解</div>
    </AbsoluteFill>
  );
};
