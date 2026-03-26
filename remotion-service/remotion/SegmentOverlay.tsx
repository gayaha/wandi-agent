import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { getTextContainerStyle, getOverlayBoxStyle } from "./TextOverlay.js";
import type { BrandConfig } from "./schemas.js";

/**
 * Resolve role-based text styling from brand config.
 *
 * - hook: primaryColor + hookFontSize + hookFontWeight
 * - body: secondaryColor + bodyFontSize + weight 400 (always)
 * - cta:  primaryColor + bodyFontSize + weight 700 (always bold)
 *
 * Exported for unit testing without React rendering context.
 */
export function resolveRoleStyle(
  role: "hook" | "body" | "cta",
  brand?: BrandConfig
): { color: string; fontSize: number; fontWeight: number } {
  // All roles use the same size and weight for uniform look
  const fontSize = brand?.hookFontSize ?? 52;
  const fontWeight = brand?.hookFontWeight ?? 700;
  const color = "#FFFFFF";

  switch (role) {
    case "hook":
      return { color, fontSize, fontWeight };
    case "body":
      return { color, fontSize, fontWeight };
    case "cta":
      return { color, fontSize, fontWeight };
  }
}

type SegmentOverlayProps = {
  text: string;
  role: "hook" | "body" | "cta";
  animationStyle: "fade" | "slide";
  textDirection: "rtl" | "ltr";
  brandConfig?: BrandConfig;
};

/**
 * SegmentOverlay — renders a single timed text segment with role-based styling
 * and independent fade/slide animation.
 *
 * This component is always mounted inside a Remotion <Sequence>, so
 * useCurrentFrame() returns 0 at the start of the segment and
 * useVideoConfig().durationInFrames equals the segment duration.
 *
 * Unlike TextOverlay (which renders both hookText + bodyText), SegmentOverlay
 * renders a SINGLE text block. The role determines styling, not content structure.
 */
export const SegmentOverlay: React.FC<SegmentOverlayProps> = ({
  text,
  role,
  animationStyle,
  textDirection,
  brandConfig,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Convert animationSpeedMs to frames (default 500ms = 15 frames at 30fps)
  const fadeFrames = Math.round(((brandConfig?.animationSpeedMs ?? 500) / 1000) * fps);

  // Fade animation: 0 -> 1 over fadeFrames, hold at 1, then 1 -> 0 over fadeFrames
  const opacity = interpolate(
    frame,
    [0, fadeFrames, durationInFrames - fadeFrames, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Slide animation: same spring + exit interpolation pattern as TextOverlay
  let translateY = 0;
  if (animationStyle === "slide") {
    const slideProgress = spring({
      frame,
      fps,
      from: 80,
      to: 0,
      config: { damping: 14, stiffness: 120, mass: 1 },
    });
    // Exit: slide back down in the last fadeFrames
    const exitSlide = interpolate(
      frame,
      [durationInFrames - fadeFrames, durationInFrames],
      [0, 80],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
    translateY = slideProgress + exitSlide;
  }

  // Resolve role-based styling
  const roleStyle = resolveRoleStyle(role, brandConfig);

  // Build text container style using shared helper from TextOverlay
  const textContainerStyle = getTextContainerStyle(textDirection, {
    fontFamily: brandConfig?.fontFamily,
    textAlign: brandConfig?.textAlign,
    primaryColor: roleStyle.color,
  });

  // Transparent overlay — text stands on its own with stroke + shadow
  const overlayBoxStyle: React.CSSProperties = {
    background: "transparent",
    padding: "24px 32px",
    opacity,
    transform: animationStyle === "slide" ? `translateY(${translateY}px)` : undefined,
  };

  const textStyle: React.CSSProperties = {
    ...textContainerStyle,
    fontSize: roleStyle.fontSize,
    fontWeight: roleStyle.fontWeight,
    WebkitTextStroke: "2px #000000",
    paintOrder: "stroke fill",
    textShadow: "2px 2px 4px rgba(0,0,0,0.8)",
  };

  return (
    <div style={overlayBoxStyle}>
      <div style={textStyle}>{text}</div>
    </div>
  );
};
