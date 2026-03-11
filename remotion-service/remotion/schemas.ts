import { z } from "zod";

export const ReelInputSchema = z.object({
  sourceVideoUrl: z.string(),
  hookText: z.string(),
  bodyText: z.string(),
  textDirection: z.enum(["rtl", "ltr"]).default("rtl"),
  animationStyle: z.enum(["fade", "slide"]).default("fade"),
  durationInSeconds: z.number().min(3).max(90).default(15),
});

export type ReelInput = z.infer<typeof ReelInputSchema>;
