import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { fontFamily } from "./fonts.js";
import { FADE_IN_FRAMES, FADE_OUT_FRAMES } from "./constants.js";

type TextOverlayProps = {
  hookText: string;
  bodyText: string;
  animationStyle: "fade" | "slide";
  textDirection: "rtl" | "ltr";
};

/**
 * Returns the base text container style for the given text direction.
 * Exported for unit testing (HEBR-01 RTL style assertions).
 */
export function getTextContainerStyle(direction: "rtl" | "ltr"): React.CSSProperties {
  return {
    direction,
    unicodeBidi: "embed",
    textAlign: "center",
    fontFamily,
    color: "#FFFFFF",
  };
}

export const TextOverlay: React.FC<TextOverlayProps> = ({
  hookText,
  bodyText,
  animationStyle,
  textDirection,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Fade animation: 0 -> 1 over FADE_IN_FRAMES, hold at 1, then 1 -> 0 over FADE_OUT_FRAMES
  const opacity = interpolate(
    frame,
    [0, FADE_IN_FRAMES, durationInFrames - FADE_OUT_FRAMES, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Slide entrance: translateY from +80px to 0 using spring
  let translateY = 0;
  if (animationStyle === "slide") {
    const slideProgress = spring({
      frame,
      fps,
      from: 80,
      to: 0,
      config: { damping: 14, stiffness: 120, mass: 1 },
    });
    // Exit: slide back down in the last FADE_OUT_FRAMES
    const exitSlide = interpolate(
      frame,
      [durationInFrames - FADE_OUT_FRAMES, durationInFrames],
      [0, 80],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
    translateY = slideProgress + exitSlide;
  }

  const containerStyle = getTextContainerStyle(textDirection);

  const overlayBoxStyle: React.CSSProperties = {
    backgroundColor: "rgba(0, 0, 0, 0.55)",
    borderRadius: 16,
    padding: "24px 32px",
    opacity,
    transform: animationStyle === "slide" ? `translateY(${translateY}px)` : undefined,
  };

  const hookStyle: React.CSSProperties = {
    ...containerStyle,
    fontSize: 52,
    fontWeight: 700,
    marginBottom: 16,
  };

  const bodyStyle: React.CSSProperties = {
    ...containerStyle,
    fontSize: 36,
    fontWeight: 400,
  };

  return (
    <div style={overlayBoxStyle}>
      <div style={hookStyle}>{hookText}</div>
      <div style={bodyStyle}>{bodyText}</div>
    </div>
  );
};
