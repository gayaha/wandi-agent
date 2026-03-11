import { describe, it, expect } from "vitest";
import {
  SAFE_ZONE_TOP,
  SAFE_ZONE_BOTTOM,
  SAFE_ZONE_HEIGHT,
} from "../../remotion/constants.js";

describe("REND-03: Safe zone positioning", () => {
  it("SAFE_ZONE_TOP is 250", () => {
    expect(SAFE_ZONE_TOP).toBe(250);
  });

  it("SAFE_ZONE_BOTTOM is 250", () => {
    expect(SAFE_ZONE_BOTTOM).toBe(250);
  });

  it("SAFE_ZONE_HEIGHT is 1420 (1920 - 250 - 250)", () => {
    expect(SAFE_ZONE_HEIGHT).toBe(1420);
  });

  it("Safe zone does not overlap Instagram UI bars", () => {
    expect(SAFE_ZONE_TOP).toBeGreaterThanOrEqual(250);
    expect(1920 - SAFE_ZONE_BOTTOM).toBeLessThanOrEqual(1670);
  });
});
