import { describe, it, expect } from "vitest";
import { getTextContainerStyle, hexToRgba, getOverlayBoxStyle } from "../../remotion/TextOverlay.js";
import { POSITION_MAP } from "../../remotion/ReelTemplate.js";

describe("getTextContainerStyle", () => {
  it("with default brand config returns direction rtl and unicodeBidi embed", () => {
    const style = getTextContainerStyle("rtl");
    expect(style.direction).toBe("rtl");
    expect(style.unicodeBidi).toBe("embed");
  });

  it("with default brand config returns textAlign center", () => {
    const style = getTextContainerStyle("rtl");
    expect(style.textAlign).toBe("center");
  });

  it("with default brand config returns white color", () => {
    const style = getTextContainerStyle("rtl");
    expect(style.color).toBe("#FFFFFF");
  });

  it("with default brand config returns Heebo fontFamily", () => {
    const style = getTextContainerStyle("rtl");
    // Should contain 'Heebo' in the CSS font family string
    expect(style.fontFamily).toContain("Heebo");
  });

  it("with Rubik fontFamily override returns Rubik in fontFamily", () => {
    const style = getTextContainerStyle("rtl", { fontFamily: "Rubik" });
    expect(style.fontFamily).toContain("Rubik");
  });

  it("with textAlign right override returns textAlign right", () => {
    const style = getTextContainerStyle("rtl", { textAlign: "right" });
    expect(style.textAlign).toBe("right");
  });

  it("with primaryColor override returns that color", () => {
    const style = getTextContainerStyle("rtl", { primaryColor: "#FF0000" });
    expect(style.color).toBe("#FF0000");
  });

  it("with all overrides applies fontFamily, textAlign, and color", () => {
    const style = getTextContainerStyle("rtl", {
      fontFamily: "Rubik",
      textAlign: "right",
      primaryColor: "#FF0000",
    });
    expect(style.fontFamily).toContain("Rubik");
    expect(style.textAlign).toBe("right");
    expect(style.color).toBe("#FF0000");
  });
});

describe("hexToRgba", () => {
  it("converts #000000 at 0.55 to rgba(0, 0, 0, 0.55)", () => {
    expect(hexToRgba("#000000", 0.55)).toBe("rgba(0, 0, 0, 0.55)");
  });

  it("converts #FF0000 at 0.8 to rgba(255, 0, 0, 0.8)", () => {
    expect(hexToRgba("#FF0000", 0.8)).toBe("rgba(255, 0, 0, 0.8)");
  });

  it("expands 3-char hex #abc to rgba(170, 187, 204, 0.5)", () => {
    expect(hexToRgba("#abc", 0.5)).toBe("rgba(170, 187, 204, 0.5)");
  });

  it("converts #FFFFFF at 1 to rgba(255, 255, 255, 1)", () => {
    expect(hexToRgba("#FFFFFF", 1)).toBe("rgba(255, 255, 255, 1)");
  });
});

describe("POSITION_MAP", () => {
  it("maps top to flex-start", () => {
    expect(POSITION_MAP["top"]).toBe("flex-start");
  });

  it("maps center to center", () => {
    expect(POSITION_MAP["center"]).toBe("center");
  });

  it("maps bottom to flex-end", () => {
    expect(POSITION_MAP["bottom"]).toBe("flex-end");
  });
});

describe("getOverlayBoxStyle", () => {
  it("with defaults returns black overlay at 0.55 opacity and borderRadius 16", () => {
    const style = getOverlayBoxStyle();
    expect(style.backgroundColor).toBe("rgba(0, 0, 0, 0.55)");
    expect(style.borderRadius).toBe(16);
  });

  it("with custom overlayColor returns that color in rgba", () => {
    const style = getOverlayBoxStyle({ overlayColor: "#FF0000", overlayOpacity: 0.8 });
    expect(style.backgroundColor).toBe("rgba(255, 0, 0, 0.8)");
  });

  it("with borderRadius 0 returns borderRadius 0", () => {
    const style = getOverlayBoxStyle({ borderRadius: 0 });
    expect(style.borderRadius).toBe(0);
  });

  it("with all custom opts applies all values", () => {
    const style = getOverlayBoxStyle({
      overlayColor: "#FF0000",
      overlayOpacity: 0.8,
      borderRadius: 0,
    });
    expect(style.backgroundColor).toBe("rgba(255, 0, 0, 0.8)");
    expect(style.borderRadius).toBe(0);
  });
});
