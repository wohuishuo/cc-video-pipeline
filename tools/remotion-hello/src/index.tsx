import { useCurrentFrame, useVideoConfig, spring } from "remotion";

export const HelloWorld: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, from: 0, to: 1, config: { mass: 1, damping: 10 } });

  return (
    <div style={{
      flex: 1,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
      fontFamily: "system-ui, sans-serif",
      width: "100%",
      height: "100%",
    }}>
      <h1 style={{
        fontSize: 80,
        color: "#fff",
        transform: `scale(${scale})`,
        textAlign: "center",
        fontWeight: 800,
        textShadow: "0 0 40px rgba(99,102,241,0.5)",
      }}>
        Hello Remotion!
      </h1>
    </div>
  );
};
