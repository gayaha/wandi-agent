import { describe, it, expect } from "vitest";
import { fontFamily, getFontFamily, DEFAULT_FONT_FAMILY } from "../../remotion/fonts.js";

describe("HEBR-03: Font loading", () => {
  it("HEBR-03: fontFamily is Heebo (backward compat export)", () => {
    expect(fontFamily).toContain("Heebo");
  });

  // ── Multi-font loading tests ───────────────────────────────────────────────

  it("DEFAULT_FONT_FAMILY is a non-empty string", () => {
    expect(typeof DEFAULT_FONT_FAMILY).toBe("string");
    expect(DEFAULT_FONT_FAMILY.length).toBeGreaterThan(0);
  });

  it("DEFAULT_FONT_FAMILY contains Heebo", () => {
    expect(DEFAULT_FONT_FAMILY).toContain("Heebo");
  });

  it("getFontFamily('Heebo') returns Heebo fontFamily CSS string", () => {
    const result = getFontFamily("Heebo");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("Heebo");
  });

  it("getFontFamily('Assistant') returns Assistant fontFamily CSS string", () => {
    const result = getFontFamily("Assistant");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("Assistant");
  });

  it("getFontFamily('Rubik') returns Rubik fontFamily CSS string", () => {
    const result = getFontFamily("Rubik");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("Rubik");
  });

  it("getFontFamily('Frank Ruhl Libre') returns Frank Ruhl Libre fontFamily CSS string", () => {
    const result = getFontFamily("Frank Ruhl Libre");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("getFontFamily(undefined) returns DEFAULT_FONT_FAMILY", () => {
    const result = getFontFamily(undefined);
    expect(result).toBe(DEFAULT_FONT_FAMILY);
  });

  it("getFontFamily('UnknownFont') returns DEFAULT_FONT_FAMILY", () => {
    const result = getFontFamily("UnknownFont");
    expect(result).toBe(DEFAULT_FONT_FAMILY);
  });

  it("fontFamily export equals DEFAULT_FONT_FAMILY (backward compat)", () => {
    expect(fontFamily).toBe(DEFAULT_FONT_FAMILY);
  });
});
