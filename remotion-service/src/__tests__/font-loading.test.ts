import { describe, it, expect } from "vitest";
import { fontFamily } from "../../remotion/fonts.js";

describe("HEBR-03: Font loading", () => {
  it("HEBR-03: fontFamily is Heebo", () => {
    expect(fontFamily).toContain("Heebo");
  });
});
