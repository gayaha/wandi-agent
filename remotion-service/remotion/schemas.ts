import { z } from "zod";

/**
 * BrandConfigSchema — optional per-client brand configuration.
 *
 * All fields are optional with defaults matching the current hardcoded look.
 * fontFamily is restricted to the 4 curated Google Fonts loaded by fonts.ts.
 * overlayOpacity is constrained to 0.3–0.8 to maintain readability.
 *
 * When brandConfig is present (even as {}), all fields get their defaults.
 * When brandConfig is absent from the payload, it remains undefined.
 */
export const BrandConfigSchema = z.object({
  primaryColor: z.string().default("#FFFFFF"),
  secondaryColor: z.string().default("#FFFFFF"),
  fontFamily: z
    .enum(["Heebo", "Assistant", "Rubik", "Frank Ruhl Libre"])
    .default("Heebo"),
  hookFontSize: z.number().int().min(20).max(120).default(52),
  bodyFontSize: z.number().int().min(14).max(80).default(36),
  hookFontWeight: z.number().int().default(700),
  overlayColor: z.string().default("#000000"),
  overlayOpacity: z.number().min(0.3).max(0.8).default(0.55),
  borderRadius: z.number().int().min(0).max(100).default(16),
  textPosition: z.enum(["top", "center", "bottom"]).default("top"),
  textAlign: z.enum(["center", "right", "left"]).default("center"),
  animationSpeedMs: z.number().int().default(500),
});

export type BrandConfig = z.infer<typeof BrandConfigSchema>;

export const ReelInputSchema = z.object({
  sourceVideoUrl: z.string(),
  hookText: z.string(),
  bodyText: z.string(),
  textDirection: z.enum(["rtl", "ltr"]).default("rtl"),
  animationStyle: z.enum(["fade", "slide"]).default("fade"),
  durationInSeconds: z.number().min(3).max(90).default(15),
  // Injected at render time by the render queue after pre-downloading the video.
  // Not part of the HTTP request schema — added via spread in render-queue.ts.
  sourceVideoLocalPath: z.string().optional(),
  // Optional per-client brand configuration. When absent, Zod fills all defaults.
  brandConfig: BrandConfigSchema.optional(),
});

export type ReelInput = z.infer<typeof ReelInputSchema>;
