import { describe, it, expect } from "vitest";
import { ReelInputSchema, SegmentSchema } from "../../remotion/schemas.js";

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
      durationInSeconds: 601,
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

// ── SegmentSchema and segments in ReelInput ────────────────────────────────

describe("SegmentSchema and segments in ReelInput", () => {
  const validSegment = {
    text: "שלום",
    startSeconds: 0,
    endSeconds: 5,
    role: "hook",
  };

  const validSegmentOnlyInput = {
    sourceVideoUrl: "https://example.com/video.mp4",
    segments: [validSegment],
  };

  const validLegacyInput = {
    sourceVideoUrl: "https://example.com/video.mp4",
    hookText: "שלום",
    bodyText: "גוף הטקסט",
  };

  // ── SegmentSchema ────────────────────────────────────────────────────────

  it("SegmentSchema parses a valid segment with all fields", () => {
    const result = SegmentSchema.safeParse({
      text: "hello",
      startSeconds: 0,
      endSeconds: 5,
      animationStyle: "slide",
      role: "body",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.text).toBe("hello");
      expect(result.data.startSeconds).toBe(0);
      expect(result.data.endSeconds).toBe(5);
      expect(result.data.animationStyle).toBe("slide");
      expect(result.data.role).toBe("body");
    }
  });

  it("SegmentSchema applies default animationStyle of 'fade'", () => {
    const result = SegmentSchema.safeParse(validSegment);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.animationStyle).toBe("fade");
    }
  });

  it("SegmentSchema accepts role 'hook'", () => {
    const result = SegmentSchema.safeParse({ ...validSegment, role: "hook" });
    expect(result.success).toBe(true);
  });

  it("SegmentSchema accepts role 'body'", () => {
    const result = SegmentSchema.safeParse({ ...validSegment, role: "body" });
    expect(result.success).toBe(true);
  });

  it("SegmentSchema accepts role 'cta'", () => {
    const result = SegmentSchema.safeParse({ ...validSegment, role: "cta" });
    expect(result.success).toBe(true);
  });

  it("SegmentSchema rejects invalid role", () => {
    const result = SegmentSchema.safeParse({ ...validSegment, role: "invalid" });
    expect(result.success).toBe(false);
  });

  it("SegmentSchema rejects negative startSeconds", () => {
    const result = SegmentSchema.safeParse({ ...validSegment, startSeconds: -1 });
    expect(result.success).toBe(false);
  });

  it("SegmentSchema rejects zero or negative endSeconds", () => {
    const result = SegmentSchema.safeParse({ ...validSegment, endSeconds: 0 });
    expect(result.success).toBe(false);
  });

  // ── ReelInputSchema with segments ───────────────────────────────────────

  it("ReelInputSchema accepts segments-only payload (no hookText/bodyText)", () => {
    const result = ReelInputSchema.safeParse(validSegmentOnlyInput);
    expect(result.success).toBe(true);
  });

  it("ReelInputSchema accepts legacy hookText+bodyText payload (no segments)", () => {
    const result = ReelInputSchema.safeParse(validLegacyInput);
    expect(result.success).toBe(true);
  });

  it("ReelInputSchema rejects payload with neither segments nor hookText/bodyText", () => {
    const result = ReelInputSchema.safeParse({
      sourceVideoUrl: "https://example.com/video.mp4",
    });
    expect(result.success).toBe(false);
  });

  it("ReelInputSchema rejects payload with only hookText (missing bodyText)", () => {
    const result = ReelInputSchema.safeParse({
      sourceVideoUrl: "https://example.com/video.mp4",
      hookText: "only hook",
    });
    expect(result.success).toBe(false);
  });

  it("ReelInputSchema accepts segments with all segment fields", () => {
    const result = ReelInputSchema.safeParse({
      ...validSegmentOnlyInput,
      segments: [
        { text: "hook text", startSeconds: 0, endSeconds: 5, role: "hook", animationStyle: "slide" },
        { text: "body text", startSeconds: 5, endSeconds: 15, role: "body" },
      ],
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.segments).toHaveLength(2);
      expect(result.data.segments?.[0].animationStyle).toBe("slide");
      expect(result.data.segments?.[1].animationStyle).toBe("fade"); // default
    }
  });
});
