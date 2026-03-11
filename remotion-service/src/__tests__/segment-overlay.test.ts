import { describe, it, expect } from "vitest";
import { resolveRoleStyle } from "../../remotion/SegmentOverlay.js";

// Default brand values from BrandConfigSchema:
// primaryColor: "#FFFFFF", secondaryColor: "#FFFFFF"
// hookFontSize: 52, bodyFontSize: 36, hookFontWeight: 700

describe("resolveRoleStyle", () => {
  // ── Default brand (no brandConfig passed) ───────────────────────────────

  it("hook with no brand returns primaryColor #FFFFFF, hookFontSize 52, hookFontWeight 700", () => {
    const style = resolveRoleStyle("hook");
    expect(style.color).toBe("#FFFFFF");
    expect(style.fontSize).toBe(52);
    expect(style.fontWeight).toBe(700);
  });

  it("body with no brand returns secondaryColor #FFFFFF, bodyFontSize 36, fontWeight 400", () => {
    const style = resolveRoleStyle("body");
    expect(style.color).toBe("#FFFFFF");
    expect(style.fontSize).toBe(36);
    expect(style.fontWeight).toBe(400);
  });

  it("cta with no brand returns primaryColor #FFFFFF, bodyFontSize 36, fontWeight 700", () => {
    const style = resolveRoleStyle("cta");
    expect(style.color).toBe("#FFFFFF");
    expect(style.fontSize).toBe(36);
    expect(style.fontWeight).toBe(700);
  });

  // ── Custom brand values ──────────────────────────────────────────────────

  const customBrand = {
    primaryColor: "#FF0000",
    secondaryColor: "#00FF00",
    fontFamily: "Rubik" as const,
    hookFontSize: 60,
    bodyFontSize: 40,
    hookFontWeight: 900,
    overlayColor: "#000000",
    overlayOpacity: 0.55,
    borderRadius: 16,
    textPosition: "top" as const,
    textAlign: "center" as const,
    animationSpeedMs: 500,
  };

  it("hook with custom brand returns primaryColor, hookFontSize, hookFontWeight", () => {
    const style = resolveRoleStyle("hook", customBrand);
    expect(style.color).toBe("#FF0000");
    expect(style.fontSize).toBe(60);
    expect(style.fontWeight).toBe(900);
  });

  it("body with custom brand returns secondaryColor, bodyFontSize, fontWeight 400", () => {
    const style = resolveRoleStyle("body", customBrand);
    expect(style.color).toBe("#00FF00");
    expect(style.fontSize).toBe(40);
    expect(style.fontWeight).toBe(400);
  });

  it("cta with custom brand returns primaryColor, bodyFontSize, fontWeight 700", () => {
    const style = resolveRoleStyle("cta", customBrand);
    expect(style.color).toBe("#FF0000");
    expect(style.fontSize).toBe(40);
    expect(style.fontWeight).toBe(700);
  });

  // ── Partial brand overrides ──────────────────────────────────────────────

  it("hook with partial brand {primaryColor: #FF0000, hookFontSize: 60} uses those values", () => {
    const partial = {
      primaryColor: "#FF0000",
      secondaryColor: "#FFFFFF",
      fontFamily: "Heebo" as const,
      hookFontSize: 60,
      bodyFontSize: 36,
      hookFontWeight: 700,
      overlayColor: "#000000",
      overlayOpacity: 0.55,
      borderRadius: 16,
      textPosition: "top" as const,
      textAlign: "center" as const,
      animationSpeedMs: 500,
    };
    const style = resolveRoleStyle("hook", partial);
    expect(style.color).toBe("#FF0000");
    expect(style.fontSize).toBe(60);
    expect(style.fontWeight).toBe(700);
  });
});
