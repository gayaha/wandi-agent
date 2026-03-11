import { z } from "zod";

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
});

export type ReelInput = z.infer<typeof ReelInputSchema>;
