import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { getFontFamily, DEFAULT_FONT_FAMILY } from "./fonts.js";

type TextOverlayProps = {
  hookText: string;
  bodyText: string;
  animationStyle: "fade" | "slide";
  textDirection: "rtl" | "ltr";
  // Brand config — all optional with defaults matching current hardcoded values
  primaryColor?: string;
  secondaryColor?: string;
  fontFamily?: string;       // Font name (e.g. "Rubik"), resolved via getFontFamily
  hookFontSize?: number;
  bodyFontSize?: number;
  hookFontWeight?: number;
  overlayColor?: string;
  overlayOpacity?: number;
  borderRadius?: number;
  textAlign?: "center" | "right" | "left";
  animationSpeedMs?: number;
};

/**
 * Convert a hex color (#RGB or #RRGGBB) to an rgba() string.
 * Exported for unit testing.
 */
export function hexToRgba(hex: string, opacity: number): string {
  let h = hex.replace(/^#/, "");
  // Expand 3-char hex to 6-char
  if (h.length === 3) {
    h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
  }
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

/**
 * Returns the overlay box style (background + borderRadius).
 * Exported for unit testing.
 */
export function getOverlayBoxStyle(opts?: {
  overlayColor?: string;
  overlayOpacity?: number;
  borderRadius?: number;
}): React.CSSProperties {
  return {
    backgroundColor: hexToRgba(opts?.overlayColor ?? "#000000", opts?.overlayOpacity ?? 0.55),
    borderRadius: opts?.borderRadius ?? 16,
  };
}

/**
 * Returns the base text container style for the given text direction.
 * Exported for unit testing (HEBR-01 RTL style assertions).
 *
 * @param direction - Text direction ("rtl" | "ltr")
 * @param brandOverrides - Optional brand config overrides for font, alignment, and color
 */
export function getTextContainerStyle(
  direction: "rtl" | "ltr",
  brandOverrides?: { fontFamily?: string; textAlign?: string; primaryColor?: string }
): React.CSSProperties {
  return {
    direction,
    unicodeBidi: "embed",
    textAlign: (brandOverrides?.textAlign ?? "center") as React.CSSProperties["textAlign"],
    fontFamily: brandOverrides?.fontFamily ? getFontFamily(brandOverrides.fontFamily) : DEFAULT_FONT_FAMILY,
    color: brandOverrides?.primaryColor ?? "#FFFFFF",
  };
}

export const TextOverlay: React.FC<TextOverlayProps> = ({
  hookText,
  bodyText,
  animationStyle,
  textDirection,
  primaryColor,
  secondaryColor,
  fontFamily: fontFamilyProp,
  hookFontSize,
  bodyFontSize,
  hookFontWeight,
  overlayColor,
  overlayOpacity,
  borderRadius,
  textAlign,
  animationSpeedMs,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Convert animationSpeedMs to frames (default 500ms = 15 frames at 30fps)
  const fadeFrames = Math.round(((animationSpeedMs ?? 500) / 1000) * fps);

  // Fade animation: 0 -> 1 over fadeFrames, hold at 1, then 1 -> 0 over fadeFrames
  const opacity = interpolate(
    frame,
    [0, fadeFrames, durationInFrames - fadeFrames, durationInFrames],
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
    // Exit: slide back down in the last fadeFrames
    const exitSlide = interpolate(
      frame,
      [durationInFrames - fadeFrames, durationInFrames],
      [0, 80],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
    translateY = slideProgress + exitSlide;
  }

  const containerStyle = getTextContainerStyle(textDirection, {
    fontFamily: fontFamilyProp,
    textAlign,
    primaryColor,
  });

  // Transparent overlay — text stands on its own with stroke + shadow
  const overlayBoxStyle: React.CSSProperties = {
    background: "transparent",
    padding: "24px 32px",
    opacity,
    transform: animationStyle === "slide" ? `translateY(${translateY}px)` : undefined,
  };

  const textStrokeStyle: React.CSSProperties = {
    WebkitTextStroke: "2px #000000",
    paintOrder: "stroke fill",
    textShadow: "2px 2px 4px rgba(0,0,0,0.8)",
  };

  const hookStyle: React.CSSProperties = {
    ...containerStyle,
    ...textStrokeStyle,
    fontSize: hookFontSize ?? 52,
    fontWeight: hookFontWeight ?? 700,
    color: "#FFFFFF",
    marginBottom: 16,
  };

  const bodyStyle: React.CSSProperties = {
    ...containerStyle,
    ...textStrokeStyle,
    fontSize: hookFontSize ?? 52,
    fontWeight: hookFontWeight ?? 700,
    color: "#FFFFFF",
  };

  return (
    <div style={overlayBoxStyle}>
      <div style={hookStyle}>{hookText}</div>
      <div style={bodyStyle}>{bodyText}</div>
    </div>
  );
};
