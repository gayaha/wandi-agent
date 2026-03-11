import { describe, it, expect } from "vitest";
import { interpolate } from "remotion";
import { FADE_IN_FRAMES, FADE_OUT_FRAMES, VIDEO_FPS } from "../../remotion/constants.js";

describe("REND-04: Fade animation interpolation", () => {
  const durationInSeconds = 15;
  const totalFrames = durationInSeconds * VIDEO_FPS; // 450

  function getOpacity(frame: number): number {
    return interpolate(
      frame,
      [0, FADE_IN_FRAMES, totalFrames - FADE_OUT_FRAMES, totalFrames],
      [0, 1, 1, 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  }

  it("REND-04: opacity is 0 at frame 0 (fade-in start)", () => {
    expect(getOpacity(0)).toBe(0);
  });

  it("REND-04: opacity is 1 at FADE_IN_FRAMES", () => {
    expect(getOpacity(FADE_IN_FRAMES)).toBe(1);
  });

  it("REND-04: opacity is 1 before fade-out starts", () => {
    expect(getOpacity(totalFrames - FADE_OUT_FRAMES)).toBe(1);
  });

  it("REND-04: opacity is 0 at last frame", () => {
    expect(getOpacity(totalFrames)).toBe(0);
  });
});
