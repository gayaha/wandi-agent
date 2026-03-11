import { describe, it, expect } from "vitest";
import { getTextContainerStyle } from "../../remotion/TextOverlay.js";

describe("HEBR-01: RTL text styles", () => {
  const rtlStyle = getTextContainerStyle("rtl");

  it("HEBR-01: RTL text style has direction rtl", () => {
    expect(rtlStyle.direction).toBe("rtl");
  });

  it("HEBR-01: RTL text style has unicodeBidi embed", () => {
    expect(rtlStyle.unicodeBidi).toBe("embed");
  });

  it("HEBR-01: RTL text style never uses bidi-override", () => {
    expect(rtlStyle.unicodeBidi).not.toBe("bidi-override");
  });
});
