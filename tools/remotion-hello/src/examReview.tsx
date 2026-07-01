import {
  AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig,
  interpolate, Easing,
} from "remotion";

const FPS = 30;

const INK = "#0b0d12";
const CARD = "#13161d";
const INDIGO = "#7C6CF0";
const AMBER = "#F2B84B";
const FG = "#EDEFF4";
const MUTE = "#7A8094";

const SERIF = '"Georgia","Times New Roman","STKaiti",serif';
const SANS = '"Microsoft YaHei","Inter","Segoe UI",sans-serif';

type TableT = { header: string[]; rows: string[][] } | null;
type Seg = { lang: "en" | "zh"; text: string; start: number; end: number };
type Entry = {
  id: string; title_en: string; title_zh: string;
  question_en: string; answer: string; conclusion: string; table: TableT;
  start: number; end: number; segments: Seg[];
};
type Timings = { part_no: number; part_title: string; total: number; entries: Entry[] };

const fadeIn = (frame: number, from = 0, len = 10) =>
  interpolate(frame, [from, from + len], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const Header: React.FC<{ partNo: number; partTitle: string; idx: number; count: number }> = ({ partNo, partTitle, idx, count }) => (
  <div style={{
    position: "absolute", top: 44, left: 64, right: 64, display: "flex",
    justifyContent: "space-between", alignItems: "center", fontFamily: SANS,
  }}>
    <span style={{ color: INDIGO, fontWeight: 700, fontSize: 22, letterSpacing: 3 }}>
      PART {partNo} <span style={{ color: MUTE, fontWeight: 400 }}>· {partTitle}</span>
    </span>
    <span style={{ color: MUTE, fontSize: 20, letterSpacing: 2 }}>
      {String(idx + 1).padStart(2, "0")} / {String(count).padStart(2, "0")}
    </span>
  </div>
);

const ProgressBar: React.FC<{ pct: number }> = ({ pct }) => (
  <div style={{ position: "absolute", top: 0, left: 0, height: 6, width: "100%", background: "rgba(255,255,255,0.06)" }}>
    <div style={{ height: "100%", width: `${pct * 100}%`, background: `linear-gradient(90deg, ${INDIGO}, ${AMBER})` }} />
  </div>
);

const MiniTable: React.FC<{ table: TableT; appear: number }> = ({ table, appear }) => {
  if (!table) return null;
  return (
    <div style={{
      marginTop: 28, borderRadius: 14, overflow: "hidden", border: `1px solid rgba(255,255,255,0.08)`,
      opacity: fadeIn(appear, 0, 12), transform: `translateY(${(1 - fadeIn(appear, 0, 12)) * 14}px)`,
    }}>
      <div style={{ display: "flex", background: "rgba(124,108,240,0.16)" }}>
        {table.header.map((h, i) => (
          <div key={i} style={{
            flex: 1, padding: "12px 18px", fontFamily: SANS, fontWeight: 700,
            fontSize: 20, color: INDIGO,
          }}>{h}</div>
        ))}
      </div>
      {table.rows.map((row, ri) => (
        <div key={ri} style={{
          display: "flex", background: ri % 2 === 0 ? "rgba(255,255,255,0.02)" : "transparent",
          borderTop: "1px solid rgba(255,255,255,0.06)",
        }}>
          {row.map((c, ci) => (
            <div key={ci} style={{
              flex: 1, padding: "10px 18px", fontFamily: SANS, fontSize: 19,
              color: ci === 0 ? FG : MUTE, fontWeight: ci === 0 ? 700 : 400,
            }}>{c}</div>
          ))}
        </div>
      ))}
    </div>
  );
};

const EntryCard: React.FC<{ entry: Entry }> = ({ entry }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zhSeg = entry.segments.find((s) => s.lang === "zh");
  const enSeg = entry.segments.find((s) => s.lang === "en");
  const zhFrame = zhSeg ? Math.round((zhSeg.start - entry.start) * fps) : 0;
  const showZh = !enSeg || frame >= zhFrame;
  const kickerOp = fadeIn(frame, 0, 8);
  const enOp = enSeg ? fadeIn(frame, 4, 12) * (showZh ? interpolate(frame, [zhFrame, zhFrame + 10], [1, 0.35], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1) : 0;
  const enScale = showZh ? interpolate(frame, [zhFrame, zhFrame + 14], [1, 0.82], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }) : 1;
  const zhOp = zhSeg ? fadeIn(frame, zhFrame, 12) : 0;
  const zhY = zhSeg ? interpolate(frame, [zhFrame, zhFrame + 14], [40, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }) : 0;

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: 1500, display: "flex", flexDirection: "column" }}>
        <div style={{
          opacity: kickerOp, fontFamily: SANS, color: AMBER, fontSize: 24, fontWeight: 700,
          letterSpacing: 3, marginBottom: 18, textTransform: "uppercase",
        }}>
          {entry.id} {entry.title_zh ? `· ${entry.title_zh}` : ""}
        </div>

        {enSeg && (
          <div style={{
            opacity: enOp, transform: `scale(${enScale})`, transformOrigin: "left top",
            display: "flex", gap: 22,
          }}>
            <span style={{ fontFamily: SERIF, fontSize: 64, color: INDIGO, lineHeight: 1, opacity: 0.5 }}>&ldquo;</span>
            <span style={{
              fontFamily: SERIF, fontStyle: "italic", fontSize: 40, color: FG, lineHeight: 1.42,
            }}>{entry.question_en}</span>
          </div>
        )}

        {zhSeg && (
          <div style={{
            opacity: zhOp, transform: `translateY(${zhY}px)`, marginTop: enSeg ? 36 : 0,
            background: CARD, border: `1px solid rgba(124,108,240,0.25)`, borderRadius: 18,
            padding: "32px 40px", boxShadow: "0 24px 60px rgba(0,0,0,0.45)",
          }}>
            {entry.answer && (
              <div style={{
                display: "inline-block", fontFamily: SANS, fontSize: 20, fontWeight: 700,
                color: INK, background: AMBER, borderRadius: 8, padding: "4px 14px", marginBottom: 16,
              }}>✓ {entry.answer}</div>
            )}
            {entry.conclusion && (
              <div style={{ fontFamily: SANS, fontSize: 32, color: FG, lineHeight: 1.55, fontWeight: 600 }}>
                {entry.conclusion}
              </div>
            )}
            <MiniTable table={entry.table} appear={frame - zhFrame - 4} />
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

export const ExamReview: React.FC<{ timings: Timings }> = ({ timings }) => {
  const frame = useCurrentFrame();
  const totalFrames = Math.ceil(timings.total * FPS) + 30;
  const idxNow = Math.max(0, timings.entries.findIndex((e) => frame / FPS < e.end));

  return (
    <AbsoluteFill style={{ background: INK }}>
      <ProgressBar pct={Math.min(1, frame / totalFrames)} />
      <Header partNo={timings.part_no} partTitle={timings.part_title} idx={idxNow < 0 ? timings.entries.length - 1 : idxNow} count={timings.entries.length} />
      {timings.entries.map((e) => {
        const from = Math.round(e.start * FPS);
        const dur = Math.round((e.end - e.start) * FPS) + 10;
        return (
          <Sequence key={e.id} from={from} durationInFrames={dur}>
            <EntryCard entry={e} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
