import { describe, it, expect } from "vitest";
import { ReelInputSchema } from "../../remotion/schemas.js";

describe("ReelInputSchema", () => {
  const validInput = {
    sourceVideoUrl: "https://example.com/video.mp4",
    hookText: "שלום עולם",
    bodyText: "גוף הטקסט כאן",
  };

  it("validates correct input", () => {
    const result = ReelInputSchema.safeParse({
      ...validInput,
      textDirection: "rtl",
      animationStyle: "fade",
      durationInSeconds: 15,
    });
    expect(result.success).toBe(true);
  });

  it("rejects missing hookText", () => {
    const result = ReelInputSchema.safeParse({
      sourceVideoUrl: "https://example.com/video.mp4",
      bodyText: "some body",
    });
    expect(result.success).toBe(false);
  });

  it("applies defaults", () => {
    const result = ReelInputSchema.safeParse(validInput);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.textDirection).toBe("rtl");
      expect(result.data.animationStyle).toBe("fade");
      expect(result.data.durationInSeconds).toBe(15);
    }
  });

  it("rejects invalid animationStyle", () => {
    const result = ReelInputSchema.safeParse({
      ...validInput,
      animationStyle: "bounce",
    });
    expect(result.success).toBe(false);
  });

  it("rejects durationInSeconds out of range (too low)", () => {
    const result = ReelInputSchema.safeParse({
      ...validInput,
      durationInSeconds: 0,
    });
    expect(result.success).toBe(false);
  });

  it("rejects durationInSeconds out of range (too high)", () => {
    const result = ReelInputSchema.safeParse({
      ...validInput,
      durationInSeconds: 91,
    });
    expect(result.success).toBe(false);
  });

  // ── BrandConfigSchema tests ────────────────────────────────────────────────

  it("accepts input with no brandConfig (backward compat)", () => {
    const result = ReelInputSchema.safeParse(validInput);
    expect(result.success).toBe(true);
    if (result.success) {
      // brandConfig should be undefined (it's optional)
      expect(result.data.brandConfig).toBeUndefined();
    }
  });

  it("accepts empty brandConfig object and applies all defaults", () => {
    const result = ReelInputSchema.safeParse({
      ...validInput,
      brandConfig: {},
    });
    expect(result.success).toBe(true);
    if (result.success) {
      const bc = result.data.brandConfig;
      expect(bc).toBeDefined();
      expect(bc?.primaryColor).toBe("#FFFFFF");
      expect(bc?.secondaryColor).toBe("#FFFFFF");
      expect(bc?.fontFamily).toBe("Heebo");
      expect(bc?.hookFontSize).toBe(52);
      expect(bc?.bodyFontSize).toBe(36);
      expect(bc?.overlayColor).toBe("#000000");
      expect(bc?.overlayOpacity).toBe(0.55);
      expect(bc?.borderRadius).toBe(16);
      expect(bc?.textPosition).toBe("top");
      expect(bc?.textAlign).toBe("center");
      expect(bc?.animationSpeedMs).toBe(500);
    }
  });

  it("accepts partial brandConfig and merges with defaults", () => {
    const result = ReelInputSchema.safeParse({
      ...validInput,
      brandConfig: { primaryColor: "#FF0000" },
    });
    expect(result.success).toBe(true);
    if (result.success) {
      const bc = result.data.brandConfig;
      expect(bc?.primaryColor).toBe("#FF0000");
      // Other fields should have defaults
      expect(bc?.fontFamily).toBe("Heebo");
      expect(bc?.hookFontSize).toBe(52);
    }
  });

  it("rejects brandConfig with invalid fontFamily", () => {
    const result = ReelInputSchema.safeParse({
      ...validInput,
      brandConfig: { fontFamily: "Comic Sans" },
    });
    expect(result.success).toBe(false);
  });

  it("rejects brandConfig with overlayOpacity below 0.3", () => {
    const result = ReelInputSchema.safeParse({
      ...validInput,
      brandConfig: { overlayOpacity: 0.1 },
    });
    expect(result.success).toBe(false);
  });

  it("rejects brandConfig with hookFontSize below 20", () => {
    const result = ReelInputSchema.safeParse({
      ...validInput,
      brandConfig: { hookFontSize: 10 },
    });
    expect(result.success).toBe(false);
  });

  it("rejects brandConfig with hookFontSize above 120", () => {
    const result = ReelInputSchema.safeParse({
      ...validInput,
      brandConfig: { hookFontSize: 200 },
    });
    expect(result.success).toBe(false);
  });

  it("accepts brandConfig with valid fontFamily from curated set", () => {
    for (const font of ["Heebo", "Assistant", "Rubik", "Frank Ruhl Libre"]) {
      const result = ReelInputSchema.safeParse({
        ...validInput,
        brandConfig: { fontFamily: font },
      });
      expect(result.success).toBe(true);
    }
  });
});
