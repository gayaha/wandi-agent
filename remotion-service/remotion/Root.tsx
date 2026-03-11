import { Composition } from "remotion";
import { AbsoluteFill } from "remotion";
import { ReelInputSchema } from "./schemas.js";
import type { ReelInput } from "./schemas.js";

const ReelTemplatePlaceholder: React.FC<ReelInput> = ({ hookText, bodyText }) => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        color: "#fff",
        fontFamily: "sans-serif",
      }}
    >
      <div style={{ fontSize: 48, fontWeight: 700, marginBottom: 24 }}>
        {hookText || "ReelTemplate placeholder"}
      </div>
      <div style={{ fontSize: 32, fontWeight: 400 }}>
        {bodyText || "Body text placeholder"}
      </div>
    </AbsoluteFill>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ReelTemplate"
      component={ReelTemplatePlaceholder}
      durationInFrames={90 * 30}
      fps={30}
      width={1080}
      height={1920}
      schema={ReelInputSchema}
      defaultProps={{
        sourceVideoUrl: "https://example.com/sample.mp4",
        hookText: "שלום עולם",
        bodyText: "גוף הטקסט כאן",
        textDirection: "rtl" as const,
        animationStyle: "fade" as const,
        durationInSeconds: 15,
      }}
    />
  );
};
