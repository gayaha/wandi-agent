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
});
