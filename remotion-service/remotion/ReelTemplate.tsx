import React from "react";
import { AbsoluteFill, OffthreadVideo } from "remotion";
import { TextOverlay } from "./TextOverlay.js";
import { SAFE_ZONE_TOP, SAFE_ZONE_HEIGHT } from "./constants.js";
import type { ReelInput } from "./schemas.js";

export const POSITION_MAP = {
  top: "flex-start",
  center: "center",
  bottom: "flex-end",
} as const;

export const ReelTemplate: React.FC<ReelInput> = ({
  sourceVideoLocalPath,
  hookText,
  bodyText,
  animationStyle,
  textDirection,
  brandConfig,
}) => {
  const justifyContent = POSITION_MAP[brandConfig?.textPosition ?? "top"];

  return (
    <AbsoluteFill>
      {/* Video layer: OffthreadVideo for source, or solid black fallback for previews */}
      {sourceVideoLocalPath ? (
        <OffthreadVideo
          src={sourceVideoLocalPath}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        <AbsoluteFill style={{ backgroundColor: "#000" }} />
      )}

      {/* Text overlay layer: positioned within the safe zone */}
      <AbsoluteFill
        style={{
          top: SAFE_ZONE_TOP,
          height: SAFE_ZONE_HEIGHT,
          position: "absolute",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent,
          padding: "40px 60px",
        }}
      >
        <TextOverlay
          hookText={hookText}
          bodyText={bodyText}
          animationStyle={animationStyle}
          textDirection={textDirection}
          primaryColor={brandConfig?.primaryColor}
          secondaryColor={brandConfig?.secondaryColor}
          fontFamily={brandConfig?.fontFamily}
          hookFontSize={brandConfig?.hookFontSize}
          bodyFontSize={brandConfig?.bodyFontSize}
          hookFontWeight={brandConfig?.hookFontWeight}
          overlayColor={brandConfig?.overlayColor}
          overlayOpacity={brandConfig?.overlayOpacity}
          borderRadius={brandConfig?.borderRadius}
          textAlign={brandConfig?.textAlign}
          animationSpeedMs={brandConfig?.animationSpeedMs}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
