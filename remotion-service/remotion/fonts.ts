import { loadFont as loadHeebo } from "@remotion/google-fonts/Heebo";
import { loadFont as loadAssistant } from "@remotion/google-fonts/Assistant";
import { loadFont as loadRubik } from "@remotion/google-fonts/Rubik";
import { loadFont as loadFrankRuhlLibre } from "@remotion/google-fonts/FrankRuhlLibre";
import { staticFile, continueRender, delayRender } from "remotion";

// Load all 4 curated Google Fonts at module init with narrow subset.
// Weights 400 (body) and 700 (hook/bold) only, hebrew subset.
const heebo = loadHeebo("normal", {
  weights: ["400", "700"] as const,
  subsets: ["hebrew"] as const,
});

const assistant = loadAssistant("normal", {
  weights: ["400", "700"] as const,
  subsets: ["hebrew"] as const,
});

const rubik = loadRubik("normal", {
  weights: ["400", "700"] as const,
  subsets: ["hebrew"] as const,
});

const frankRuhlLibre = loadFrankRuhlLibre("normal", {
  weights: ["400", "700"] as const,
  subsets: ["hebrew"] as const,
});

// ── Local font: Ploni (commercial Hebrew font) ──────────────────────────────
// Loaded via @font-face from public/fonts/ploni/ directory.
// Two weights: Regular (400) and Bold (700) for consistency with other fonts.
const PLONI_FAMILY = "Ploni";

const ploniFontFaces = [
  {
    src: staticFile("fonts/ploni/PloniRegular.otf"),
    weight: "400" as const,
  },
  {
    src: staticFile("fonts/ploni/PloniBold.otf"),
    weight: "700" as const,
  },
];

// Register @font-face declarations for Ploni
if (typeof document !== "undefined") {
  const waitHandle = delayRender("Loading Ploni font");

  const loadPromises = ploniFontFaces.map(({ src, weight }) => {
    const face = new FontFace(PLONI_FAMILY, `url(${src})`, {
      weight,
      style: "normal",
    });
    document.fonts.add(face);
    return face.load();
  });

  Promise.all(loadPromises)
    .then(() => continueRender(waitHandle))
    .catch((err) => {
      console.error("Failed to load Ploni font:", err);
      continueRender(waitHandle); // Don't block render on font failure
    });
}

// ── Font map ────────────────────────────────────────────────────────────────

// Map display names to CSS fontFamily strings
const FONT_MAP: Record<string, string> = {
  Heebo: heebo.fontFamily,
  Assistant: assistant.fontFamily,
  Rubik: rubik.fontFamily,
  "Frank Ruhl Libre": frankRuhlLibre.fontFamily,
  Ploni: PLONI_FAMILY,
  ploni: PLONI_FAMILY, // case-insensitive match
};

/**
 * Default font family (Heebo) — exported for backward compatibility.
 * All components that previously used `fontFamily` from this module
 * will continue to work until Plan 02 updates them to use getFontFamily().
 */
export const DEFAULT_FONT_FAMILY: string = heebo.fontFamily;

/**
 * Look up the CSS fontFamily string for a given font display name.
 * Falls back to DEFAULT_FONT_FAMILY for unknown or undefined names.
 */
export function getFontFamily(name: string | undefined): string {
  if (!name) return DEFAULT_FONT_FAMILY;
  return FONT_MAP[name] ?? DEFAULT_FONT_FAMILY;
}

// Backward-compat export: components importing `fontFamily` still work.
export const fontFamily = DEFAULT_FONT_FAMILY;
