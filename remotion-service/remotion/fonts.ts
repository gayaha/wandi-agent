import { loadFont } from "@remotion/google-fonts/Heebo";

// Load Heebo at module level with narrow subset to prevent delayRender timeout.
// Weights 400 (body) and 700 (hook/bold) only, hebrew subset.
const loaded = loadFont("normal", {
  weights: ["400", "700"],
  subsets: ["hebrew"],
});

export const fontFamily = loaded.fontFamily;
