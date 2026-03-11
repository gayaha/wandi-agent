# Phase 3: Brand Template System - Research

**Researched:** 2026-03-11
**Domain:** Remotion dynamic font loading, Pydantic brand config models, Zod schema extension, Airtable field fetch, SDMF stage modifiers
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Brand Visual Identity**
- Two-color model: primary color (hook text, accents) + secondary color (body text or overlay tint)
- Curated font set: 3-5 pre-vetted Hebrew+Latin Google Fonts (Heebo, Assistant, Rubik, etc.) — client picks from list. Guarantees Hebrew rendering works without fallback issues.
- Overlay background is configurable per brand: overlay color + opacity (0.3-0.8). Still a solid box with rounded corners.
- Brand template sets a default animation style (fade/slide). Can be overridden per render request for flexibility.
- Current hardcoded values (Heebo, white text, rgba(0,0,0,0.55)) become the defaults for clients without brand config.

**Awareness-Stage Styling**
- Global SDMF stage map shared across all brands — not per-brand stage configs
- Stage map applies modifiers on top of the brand's base colors/fonts (e.g., scale font size, adjust weight)
- 3 visual tiers: attention (stages 1-2), authority (stage 3), conversion (stages 4-5)
- Awareness stage is passed explicitly in the render request (not inferred from Airtable)
- Stage modifiers affect: font weight, font size scaling, animation speed — subtle differentiation within brand identity

**Template Data Storage**
- Brand fields added to existing Airtable Clients table (primary_color, secondary_color, font_family, etc.)
- Keeps all client data in one place — staff edits brand in same Airtable view they already use
- Render request includes client_id (Airtable record ID) — Python fetches brand config from Clients table before calling Remotion
- Fresh fetch from Airtable on every render (no caching) — simplest approach, ensures changes picked up immediately
- Default fallback: clients without brand config get the current hardcoded look (Heebo, white, dark overlay). Brand config is an enhancement, not a requirement.

**Text Positioning & Sizing**
- Brand template picks vertical position from 3 presets: top (current default), center, bottom — within the safe zone
- Brand template sets text alignment: center (current default), right (natural for Hebrew RTL), or left
- Hook and body font sizes are independently configurable per brand (default 52/36). Allows brands to be bolder or subtler.
- Overlay box shape: configurable border radius per brand (0 for sharp, 16 for rounded default, 50+ for pill). Subtle brand personality touch.

### Claude's Discretion
- Exact Airtable field names for brand config columns
- Font loading implementation for multiple font families in Remotion
- Stage modifier exact values (font size multipliers, weight mappings)
- Brand config validation rules (color format, font name validation)
- How brand config flows through the Python→Remotion HTTP boundary (JSON structure)
- Error handling for invalid brand config values
- Default font sizes and color values

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TMPL-01 | Each client has a brand template defining primary/secondary colors, font selection, text positioning, and overlay style | Airtable Clients table already fetched via `get_client()`. Add brand fields. BrandConfig Pydantic model validates and applies defaults. Font loaded dynamically per brand from curated set. Zod schema extended for Remotion to accept all brand props. TextOverlay.tsx accepts brand config via inputProps. |
| TMPL-02 | Text styling varies by SDMF awareness stage (e.g., Stage 1 bold/attention-grabbing vs Stage 3 authoritative/methodical) | Global STAGE_MODIFIERS constant maps stage number to font-weight/size-scale/animation-speed overrides. Applied in Python before sending payload to Remotion — final computed values flow as explicit props. No separate template files needed. |
</phase_requirements>

---

## Summary

Phase 3 threads brand configuration through the full stack: Airtable Clients table (data source) → Python BrandConfig model (validation + defaults) → Remotion HTTP payload (JSON) → Zod schema validation at enqueue → TextOverlay.tsx rendering. The existing `get_client()` function already fetches the Clients record — brand fields ride on the same record. Python merges brand config with SDMF stage modifiers and computes final resolved values before handing off to Remotion, so Remotion's side is a purely dumb renderer that accepts explicit values.

Dynamic font loading in Remotion is the most technically complex piece. The `@remotion/google-fonts` package uses per-font named imports (`import { loadFont } from "@remotion/google-fonts/Heebo"`), so multi-font support requires loading all curated fonts at module initialization, then selecting the right `fontFamily` string based on the brand config prop. The key constraint from Phase 1 holds: load only `{ subsets: ["hebrew"], weights: ["400", "700"] }` to avoid `delayRender` timeouts. All four curated fonts (Heebo, Assistant, Rubik, Frank Ruhl Libre) have confirmed `hebrew` subset support.

The brand config JSON boundary between Python and Remotion is a nested `brandConfig` object within the existing render payload. Zod validates it at enqueue with all fields optional + defaults, so a render request with no `brandConfig` key renders exactly as before — backward compatible by design.

**Primary recommendation:** Pre-load all curated fonts at module init in a refactored `fonts.ts`; select active family by string match. Compute final resolved styles in Python's `_run_render()` by merging brand config + stage modifiers before sending to Remotion.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@remotion/google-fonts` | ^4.0.0 (already installed) | Named per-font loaders with subset/weight control | Only official Remotion font loading mechanism; handles `delayRender` lifecycle |
| `zod` | 4.3.6 (already installed) | Extend `ReelInputSchema` with brand config fields | Already the validation layer at enqueue; consistent with Phase 1 decision |
| `pydantic` v2 | already installed | `BrandConfig` model + `RenderRequest` extension | Already the Python validation layer; optional fields + defaults follow established pattern |
| `httpx` (async) | already installed | Fetch brand config from Airtable Clients table | Already used in `airtable_client.py` for all Airtable calls |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` (stdlib) | stdlib | Validate hex color format in Python | Simple `#RRGGBB` / `#RGB` regex check on `primary_color` / `secondary_color` |
| `vitest` | ^3.0.0 (already installed) | TypeScript tests for schema + style helpers | Existing test runner for remotion-service |
| `pytest-asyncio` | already installed | Python async tests for brand config fetch + merge | Existing test framework |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pre-load all curated fonts at module init | Dynamic import on first use | Dynamic import inside Remotion composition would trigger `delayRender` inside render loop — unsafe. Module-init is the established safe pattern. |
| Compute resolved styles in Python | Compute in Remotion TSX | Keeping computation in Python means Remotion receives only final explicit values, easier to test, easier to log, no TypeScript stage logic needed |
| Optional Pydantic model with defaults | Required brand config | Optional with defaults means backward compatibility — existing callers with no brand config continue to work |

**Installation:** No new packages required. All libraries already in the project.

---

## Architecture Patterns

### Recommended Project Structure Changes

```
renderer/
├── models.py          # Add BrandConfig model + extend RenderRequest with client_id, awareness_stage
├── brand.py           # NEW: STAGE_MODIFIERS constant, merge_brand_with_stage() helper
├── protocol.py        # Unchanged
├── remotion.py        # Extend render() to include brand config payload
└── __init__.py        # Unchanged

remotion-service/remotion/
├── fonts.ts           # Extend to load all curated fonts; export getFontFamily(name) helper
├── schemas.ts         # Extend ReelInputSchema with optional brandConfig object
├── TextOverlay.tsx    # Accept brand config props; apply primary/secondary colors, sizes, border-radius
├── ReelTemplate.tsx   # Accept brand config; pass positioning props for vertical alignment
├── constants.ts       # Unchanged (safe zone values)
└── stage-modifiers.ts # NEW: STAGE_MODIFIERS record; applyStageModifiers() (TypeScript mirror for reference only)

airtable_client.py     # Add extract_brand_config() helper that reads brand fields from client record

tests/
├── test_brand_config.py      # NEW: Python-side BrandConfig model + stage merge tests
└── test_render_routes.py     # Extend with client_id + awareness_stage in render payloads

remotion-service/src/__tests__/
├── schema.test.ts            # Extend with brand config field tests
├── brand-styles.test.ts      # NEW: exported style helpers for color/position/size props
└── font-loading.test.ts      # Extend: getFontFamily() returns correct fontFamily string per name
```

### Pattern 1: Multi-Font Module-Level Loading

**What:** Load all curated fonts at `fonts.ts` module initialization. Export a `getFontFamily(name)` lookup function. This follows the established Phase 1 pattern of module-level font loading (never inside render functions).

**When to use:** Any time a brand config specifies a font family by string name from the curated set.

**Example:**
```typescript
// remotion-service/remotion/fonts.ts
import { loadFont as loadHeebo, fontFamily as heeboFamily } from "@remotion/google-fonts/Heebo";
import { loadFont as loadAssistant, fontFamily as assistantFamily } from "@remotion/google-fonts/Assistant";
import { loadFont as loadRubik, fontFamily as rubikFamily } from "@remotion/google-fonts/Rubik";
import { loadFont as loadFrankRuhlLibre, fontFamily as frankRuhlFamily } from "@remotion/google-fonts/FrankRuhlLibre";

// Load all at module init — narrow subset to prevent delayRender timeout
// Phase 1 decision: { subsets: ["hebrew"], weights: ["400", "700"] } only
const _loadOpts = { weights: ["400", "700"] as const, subsets: ["hebrew"] as const };
loadHeebo("normal", _loadOpts);
loadAssistant("normal", _loadOpts);
loadRubik("normal", _loadOpts);
loadFrankRuhlLibre("normal", _loadOpts);

const FONT_MAP: Record<string, string> = {
  Heebo: heeboFamily,
  Assistant: assistantFamily,
  Rubik: rubikFamily,
  "Frank Ruhl Libre": frankRuhlFamily,
};

export const DEFAULT_FONT_FAMILY = heeboFamily; // backward compat

export function getFontFamily(name: string | undefined): string {
  if (!name) return DEFAULT_FONT_FAMILY;
  return FONT_MAP[name] ?? DEFAULT_FONT_FAMILY;
}
```

### Pattern 2: BrandConfig Pydantic Model with Optional Fields + Defaults

**What:** A standalone `BrandConfig` Pydantic model where every field is `Optional` with a default matching the current hardcoded look. `RenderRequest` gains `client_id`, `awareness_stage`, and `brand_config` fields.

**When to use:** Python-side, before calling `RemotionRenderer.render()`. The brand config is fetched from Airtable, validated into this model, then merged with stage modifiers.

**Example:**
```python
# renderer/models.py additions
from typing import Literal, Optional
import re
from pydantic import BaseModel, Field, field_validator

ALLOWED_FONTS = {"Heebo", "Assistant", "Rubik", "Frank Ruhl Libre"}

class BrandConfig(BaseModel):
    """Per-client brand visual configuration. All fields optional with defaults."""
    primary_color: str = Field(default="#FFFFFF", description="Hook text color (hex)")
    secondary_color: str = Field(default="#FFFFFF", description="Body text color (hex)")
    font_family: str = Field(default="Heebo", description="Font from curated set")
    hook_font_size: int = Field(default=52, ge=20, le=120)
    body_font_size: int = Field(default=36, ge=14, le=80)
    overlay_color: str = Field(default="#000000", description="Overlay box background color (hex)")
    overlay_opacity: float = Field(default=0.55, ge=0.3, le=0.8)
    border_radius: int = Field(default=16, ge=0, le=100)
    text_position: Literal["top", "center", "bottom"] = Field(default="top")
    text_align: Literal["center", "right", "left"] = Field(default="center")
    animation_style: Literal["fade", "slide"] | None = Field(default=None)

    @field_validator("primary_color", "secondary_color", "overlay_color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        if not re.match(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$", v):
            raise ValueError(f"Invalid hex color: {v}")
        return v.upper()

    @field_validator("font_family")
    @classmethod
    def validate_font_family(cls, v: str) -> str:
        if v not in ALLOWED_FONTS:
            raise ValueError(f"Font '{v}' not in curated set: {ALLOWED_FONTS}")
        return v


class RenderRequest(BaseModel):
    source_video_url: str
    hook_text: str
    body_text: str
    record_id: str
    text_direction: Literal["rtl", "ltr"] = "rtl"
    animation_style: Literal["fade", "slide"] = "fade"
    duration_in_seconds: int = Field(default=15, ge=3, le=90)
    callback_url: str | None = None
    # Phase 3 additions
    client_id: str | None = None
    awareness_stage: int | None = Field(default=None, ge=1, le=5)
    brand_config: BrandConfig | None = None  # pre-fetched by _run_render()
```

### Pattern 3: Stage Modifier Merge in Python

**What:** A global `STAGE_MODIFIERS` dict in `renderer/brand.py` maps stage number (1-5) to modifier overrides. A `merge_brand_with_stage()` function produces a final resolved `dict` that is sent to Remotion as-is.

**When to use:** In `main._run_render()`, after fetching brand config from Airtable, before calling `renderer.render()`.

**Example:**
```python
# renderer/brand.py
from typing import Any

# 3 visual tiers: attention (1-2), authority (3), conversion (4-5)
# Modifiers are relative: hook_size_scale multiplies brand's hook_font_size
STAGE_MODIFIERS: dict[int, dict[str, Any]] = {
    1: {"hook_size_scale": 1.15, "hook_font_weight": 900, "animation_speed": "fast"},
    2: {"hook_size_scale": 1.10, "hook_font_weight": 700, "animation_speed": "fast"},
    3: {"hook_size_scale": 1.0,  "hook_font_weight": 700, "animation_speed": "normal"},
    4: {"hook_size_scale": 0.95, "hook_font_weight": 600, "animation_speed": "slow"},
    5: {"hook_size_scale": 0.95, "hook_font_weight": 600, "animation_speed": "slow"},
}


def resolve_brand_for_render(
    brand: "BrandConfig", awareness_stage: int | None
) -> dict[str, Any]:
    """Merge brand base config with stage modifiers. Returns flat dict for Remotion payload."""
    mods = STAGE_MODIFIERS.get(awareness_stage or 3, {})
    scale = mods.get("hook_size_scale", 1.0)

    return {
        "primaryColor": brand.primary_color,
        "secondaryColor": brand.secondary_color,
        "fontFamily": brand.font_family,
        "hookFontSize": round(brand.hook_font_size * scale),
        "bodyFontSize": brand.body_font_size,
        "hookFontWeight": mods.get("hook_font_weight", 700),
        "overlayColor": brand.overlay_color,
        "overlayOpacity": brand.overlay_opacity,
        "borderRadius": brand.border_radius,
        "textPosition": brand.text_position,
        "textAlign": brand.text_align,
    }
```

### Pattern 4: Zod Schema Extension for Brand Config

**What:** Add an optional `brandConfig` nested object to `ReelInputSchema`. All fields optional with defaults matching Python defaults. Zod validates at enqueue time — if brand config fields are invalid, the job fails immediately with a clear error (established Phase 1 pattern).

**When to use:** In `render-queue.ts` enqueue path.

**Example:**
```typescript
// remotion-service/remotion/schemas.ts
import { z } from "zod";

const BrandConfigSchema = z.object({
  primaryColor: z.string().regex(/^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/).default("#FFFFFF"),
  secondaryColor: z.string().regex(/^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/).default("#FFFFFF"),
  fontFamily: z.enum(["Heebo", "Assistant", "Rubik", "Frank Ruhl Libre"]).default("Heebo"),
  hookFontSize: z.number().int().min(20).max(120).default(52),
  bodyFontSize: z.number().int().min(14).max(80).default(36),
  hookFontWeight: z.number().int().default(700),
  overlayColor: z.string().regex(/^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/).default("#000000"),
  overlayOpacity: z.number().min(0.3).max(0.8).default(0.55),
  borderRadius: z.number().int().min(0).max(100).default(16),
  textPosition: z.enum(["top", "center", "bottom"]).default("top"),
  textAlign: z.enum(["center", "right", "left"]).default("center"),
}).default({});

export const ReelInputSchema = z.object({
  sourceVideoUrl: z.string(),
  hookText: z.string(),
  bodyText: z.string(),
  textDirection: z.enum(["rtl", "ltr"]).default("rtl"),
  animationStyle: z.enum(["fade", "slide"]).default("fade"),
  durationInSeconds: z.number().min(3).max(90).default(15),
  sourceVideoLocalPath: z.string().optional(),
  // Phase 3 addition — optional; absent = full defaults = current hardcoded look
  brandConfig: BrandConfigSchema.optional(),
});
```

### Pattern 5: Airtable Brand Config Extraction

**What:** `get_client()` already fetches the full Clients record. An `extract_brand_config()` helper reads brand-specific fields from the record's `fields` dict and constructs a `BrandConfig` (letting Pydantic fill defaults for missing fields).

**When to use:** In `main._run_render()`, after fetching the client record.

**Example:**
```python
# airtable_client.py — new helper
from renderer.models import BrandConfig

def extract_brand_config(client_record: dict) -> BrandConfig:
    """Parse brand config from an Airtable Clients record.

    Returns BrandConfig with defaults for any missing/invalid field.
    Airtable returns empty string for blank cells — treat as absent.
    """
    fields = client_record.get("fields", {})
    raw: dict = {}

    for at_field, model_field in {
        "Brand Primary Color": "primary_color",
        "Brand Secondary Color": "secondary_color",
        "Brand Font Family": "font_family",
        "Brand Hook Font Size": "hook_font_size",
        "Brand Body Font Size": "body_font_size",
        "Brand Overlay Color": "overlay_color",
        "Brand Overlay Opacity": "overlay_opacity",
        "Brand Border Radius": "border_radius",
        "Brand Text Position": "text_position",
        "Brand Text Align": "text_align",
    }.items():
        value = fields.get(at_field)
        if value not in (None, ""):
            raw[model_field] = value

    try:
        return BrandConfig(**raw)
    except Exception:
        # Invalid values in Airtable → fall back to defaults silently
        logger.warning(f"Invalid brand config in Airtable for client — using defaults: {raw}")
        return BrandConfig()
```

### Pattern 6: TextOverlay.tsx Brand Props

**What:** `TextOverlay` accepts brand config props and applies them. The `getTextContainerStyle()` exported helper is extended to accept brand-config parameters (for testability without React).

**When to use:** Brand config flows from `ReelInput` through `ReelTemplate` to `TextOverlay`. No prop drilling beyond 2 levels.

**Example:**
```typescript
// remotion-service/remotion/TextOverlay.tsx (new props shape)
type TextOverlayProps = {
  hookText: string;
  bodyText: string;
  animationStyle: "fade" | "slide";
  textDirection: "rtl" | "ltr";
  // Brand config — all optional with defaults matching current hardcoded values
  primaryColor?: string;      // hook text color, default "#FFFFFF"
  secondaryColor?: string;    // body text color, default "#FFFFFF"
  fontFamily?: string;        // resolved fontFamily string, default heeboFamily
  hookFontSize?: number;      // default 52
  bodyFontSize?: number;      // default 36
  hookFontWeight?: number;    // default 700
  overlayColor?: string;      // default "#000000"
  overlayOpacity?: number;    // default 0.55
  borderRadius?: number;      // default 16
  textAlign?: "center" | "right" | "left"; // default "center"
};
```

### Pattern 7: ReelTemplate.tsx Vertical Positioning

**What:** `ReelTemplate` currently hardcodes `justifyContent: "flex-start"` (top). With brand config, `textPosition` maps to a flexbox justification: top=flex-start, center=center, bottom=flex-end.

**Example:**
```typescript
// remotion-service/remotion/ReelTemplate.tsx
const POSITION_MAP = {
  top: "flex-start",
  center: "center",
  bottom: "flex-end",
} as const;

// In AbsoluteFill style:
justifyContent: POSITION_MAP[brandConfig?.textPosition ?? "top"],
```

### Anti-Patterns to Avoid

- **Loading fonts inside the React render function:** Any `loadFont()` call inside a React component or inside `runRender()` will trigger `delayRender()` in the wrong lifecycle phase, causing timeouts. Load all fonts at module initialization.
- **Per-brand dynamic imports:** `import("@remotion/google-fonts/" + fontName)` won't work in webpack-bundled Remotion. All font modules must be statically imported.
- **Passing `rgba(...)` strings from Python to Remotion:** Remotion CSS uses `rgba()` but computing it requires the hex color + opacity separately. Send them as separate fields (`overlayColor` + `overlayOpacity`) and compose `rgba` in TSX using a helper.
- **Caching brand config between renders:** The decision is explicit: fresh fetch every time. Do not add any in-process LRU cache.
- **Inferring awareness stage from Airtable:** Stage is explicitly provided in the render request only. Do not attempt to read it from the Clients record or Content Queue record.
- **Separate template files per SDMF stage:** Stage modifiers are applied as numeric overrides to brand base values. There are no separate Remotion compositions or template files per stage.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Font loading with subset control | Custom font loader using CSS @font-face | `@remotion/google-fonts/[Font]` named imports | Integrates with Remotion's `delayRender`/`continueRender` lifecycle; handles CORS, caching, timeout correctly |
| Hex color validation | Manual string parsing | Pydantic `field_validator` with `re.match` + Zod `.regex()` | Both sides already do validation; keep it consistent |
| SDMF stage logic | Per-stage template files | `STAGE_MODIFIERS` constant dict + `resolve_brand_for_render()` | A dict lookup is O(1) and trivially testable; separate template files multiply maintenance burden |
| Default fallback for missing brand config | Conditional branching in every render file | Pydantic optional-with-defaults + Zod `.default({})` | Framework defaults compose cleanly; missing config = full defaults = current hardcoded look |

**Key insight:** The hardest part of multi-font support in Remotion is that dynamic imports are not possible at render time. Pre-loading all curated fonts at module init costs ~4 network requests on cold start but is the only safe approach.

---

## Common Pitfalls

### Pitfall 1: Font Timeout from Over-Loading
**What goes wrong:** Loading too many font weights/subsets causes Remotion's `delayRender` to timeout (18-second limit per font face load).
**Why it happens:** Each weight+subset combination is a separate network request. Loading "all" variants for 4 fonts = 16+ requests easily.
**How to avoid:** Load exactly `{ weights: ["400", "700"], subsets: ["hebrew"] }` for each font. This matches the existing Phase 1 decision and has been validated.
**Warning signs:** Render hangs at composition selection step; logs show "Timed out loading Google Font".

### Pitfall 2: Static Import Constraint for Dynamic Font Selection
**What goes wrong:** Trying to use `import()` (dynamic import) to load a font based on the brand config value causes webpack bundler failure.
**Why it happens:** Remotion uses webpack to bundle the composition. Dynamic import paths cannot be statically analyzed.
**How to avoid:** Import ALL curated fonts statically at module top. Build a `FONT_MAP` lookup dict. `getFontFamily("Rubik")` returns `rubikFamily` (the CSS string) without any dynamic loading.
**Warning signs:** Webpack compilation errors mentioning "dynamic import not supported" or "cannot resolve module".

### Pitfall 3: rgba() Composition at Boundary
**What goes wrong:** Python sends `"rgba(0,0,0,0.55)"` string and Remotion uses it directly. When the opacity changes independently, the string must be recomputed.
**Why it happens:** Trying to combine a human-readable CSS shorthand across a JSON boundary.
**How to avoid:** Always send `overlayColor` (hex) and `overlayOpacity` (float) as separate fields. Compose in TSX: `` `${overlayColor}${Math.round(overlayOpacity * 255).toString(16).padStart(2, "0")}` `` or use an `rgba(r,g,b,opacity)` helper that converts hex to RGB.
**Warning signs:** Overlay appearance doesn't change when opacity is updated in Airtable.

### Pitfall 4: Brand Config Leaking Between Concurrent Jobs
**What goes wrong:** Mutable module-level state (like a `currentBrandConfig` variable) shared between concurrent render jobs causes one client's brand to appear in another's render.
**Why it happens:** Remotion's render queue processes jobs serially in the Node.js service, but Python's FastAPI handles concurrent HTTP requests.
**How to avoid:** Brand config is always passed as part of the `inputProps` payload to each individual render job. Never store it as module-level state. The Remotion render-queue processes jobs serially (Phase 1 queue design), so concurrency isolation is naturally maintained as long as brand config flows only through `inputProps`.
**Warning signs:** Isolation test shows brand from job A appearing in job B output.

### Pitfall 5: Airtable Empty String vs. Absent Field
**What goes wrong:** Airtable returns `""` (empty string) for a blank field instead of `null`. Passing `""` to `primary_color` triggers hex validation failure, crashing brand fetch instead of gracefully falling back to default.
**Why it happens:** Airtable's REST API behavior for empty cell values.
**How to avoid:** In `extract_brand_config()`, treat any value that is `None` or `""` as absent. Only include the field in the `raw` dict if it has a non-empty value. Wrap the `BrandConfig()` constructor in try/except that falls back to `BrandConfig()` (all defaults) and logs a warning.
**Warning signs:** All renders with clients who have partial brand config fail; logs show Pydantic validation errors for empty string hex values.

### Pitfall 6: textAlign on RTL Hebrew Text
**What goes wrong:** Setting `textAlign: "right"` with `direction: "rtl"` and `unicodeBidi: "embed"` produces different visual results than expected. "Right" is the natural RTL start — it may look like "left" visually to LTR readers.
**Why it happens:** RTL and textAlign interact. `textAlign: "right"` in RTL is the natural paragraph start (same as `textAlign: "start"`).
**How to avoid:** Document this in code. For Hebrew brands that want text to start at the natural RTL side, `textAlign: "right"` is correct. For center-aligned brands (the default), `textAlign: "center"` works regardless of direction. Test both combinations visually.
**Warning signs:** Hebrew text appears flush to the unexpected side of the overlay box.

---

## Code Examples

### Font Loading: Multi-Font Module Init
```typescript
// Source: Verified by inspecting /remotion-service/node_modules/@remotion/google-fonts/dist/esm/
// All four fonts confirmed to have "hebrew" subset available

import { loadFont as loadHeebo, fontFamily as heeboFamily } from "@remotion/google-fonts/Heebo";
import { loadFont as loadAssistant, fontFamily as assistantFamily } from "@remotion/google-fonts/Assistant";
import { loadFont as loadRubik, fontFamily as rubikFamily } from "@remotion/google-fonts/Rubik";
import { loadFont as loadFrankRuhlLibre, fontFamily as frankRuhlFamily } from "@remotion/google-fonts/FrankRuhlLibre";

const _opts = { weights: ["400", "700"] as const, subsets: ["hebrew"] as const };
loadHeebo("normal", _opts);
loadAssistant("normal", _opts);
loadRubik("normal", _opts);
loadFrankRuhlLibre("normal", _opts);

export const DEFAULT_FONT_FAMILY = heeboFamily;

export function getFontFamily(name: string | undefined): string {
  const map: Record<string, string> = {
    "Heebo": heeboFamily,
    "Assistant": assistantFamily,
    "Rubik": rubikFamily,
    "Frank Ruhl Libre": frankRuhlFamily,
  };
  return (name && map[name]) ? map[name] : heeboFamily;
}
```

### Zod BrandConfig with Nested Default Object
```typescript
// Source: Zod v4 docs — .default({}) on an object schema populates all inner defaults
const BrandConfigSchema = z.object({
  primaryColor: z.string().default("#FFFFFF"),
  // ... other fields with defaults
}).default({});

// Usage: passing undefined brandConfig → full defaults applied
const result = ReelInputSchema.parse({ sourceVideoUrl: "...", hookText: "...", bodyText: "..." });
// result.brandConfig.primaryColor === "#FFFFFF"  ✓
```

### Hex-to-RGBA Composition in TSX
```typescript
// Source: Standard JavaScript, no library needed
function hexToRgba(hex: string, opacity: number): string {
  const clean = hex.replace("#", "");
  const full = clean.length === 3
    ? clean.split("").map(c => c + c).join("")
    : clean;
  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

// In TextOverlay.tsx:
backgroundColor: hexToRgba(overlayColor ?? "#000000", overlayOpacity ?? 0.55)
```

### SDMF Stage Modifier Application
```python
# renderer/brand.py
STAGE_MODIFIERS = {
    1: {"hook_size_scale": 1.15, "hook_font_weight": 900, "animation_speed_ms": 400},
    2: {"hook_size_scale": 1.10, "hook_font_weight": 700, "animation_speed_ms": 400},
    3: {"hook_size_scale": 1.00, "hook_font_weight": 700, "animation_speed_ms": 500},
    4: {"hook_size_scale": 0.95, "hook_font_weight": 600, "animation_speed_ms": 600},
    5: {"hook_size_scale": 0.95, "hook_font_weight": 600, "animation_speed_ms": 600},
}

def resolve_brand_for_render(brand: BrandConfig, awareness_stage: int | None) -> dict:
    mods = STAGE_MODIFIERS.get(awareness_stage or 3, STAGE_MODIFIERS[3])
    return {
        "primaryColor": brand.primary_color,
        "secondaryColor": brand.secondary_color,
        "fontFamily": brand.font_family,
        "hookFontSize": round(brand.hook_font_size * mods["hook_size_scale"]),
        "bodyFontSize": brand.body_font_size,
        "hookFontWeight": mods["hook_font_weight"],
        "overlayColor": brand.overlay_color,
        "overlayOpacity": brand.overlay_opacity,
        "borderRadius": brand.border_radius,
        "textPosition": brand.text_position,
        "textAlign": brand.text_align,
    }
```

### main.py _run_render() Extension
```python
# In main.py _run_render(), before calling renderer.render(request):
if request.client_id:
    client_record = await at.get_client(request.client_id)
    brand_config = at.extract_brand_config(client_record)
else:
    brand_config = BrandConfig()  # all defaults

from renderer.brand import resolve_brand_for_render
resolved_brand = resolve_brand_for_render(brand_config, request.awareness_stage)

# Override animation_style from brand default if not explicitly set in request
# (request.animation_style always has a value from Pydantic default, so this needs
#  a sentinel or explicit None check to know if caller set it deliberately)
# Solution: request carries animation_style from brand config if client_id provided:
anim = brand_config.animation_style or request.animation_style

# Pass resolved brand to renderer — renderer merges into Remotion payload
remotion_job_id = await renderer.render(request, resolved_brand, anim)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single hardcoded font (Heebo) in fonts.ts | Multi-font static imports with FONT_MAP lookup | Phase 3 | No dynamic imports; all fonts bundled statically |
| Hardcoded colors/sizes in TextOverlay.tsx | Brand config props with defaults matching current hardcoded values | Phase 3 | Backward compatible; no visual change for clients without brand config |
| No client_id or awareness_stage in RenderRequest | Optional client_id + awareness_stage; brand config fetched in _run_render() | Phase 3 | Existing callers with no client_id continue to work with defaults |
| justifyContent hardcoded to flex-start | textPosition prop mapped to flexbox justification | Phase 3 | Only ReelTemplate.tsx needs the change |

**Deprecated/outdated:**
- `export const fontFamily = loaded.fontFamily` (current fonts.ts): Replaced by `getFontFamily(name)` + `DEFAULT_FONT_FAMILY` export. Both exports needed for backward compat.

---

## Open Questions

1. **Airtable field name convention for brand columns**
   - What we know: Airtable Clients table uses "Client Name", "Niche" (existing fields). Brand fields don't exist yet.
   - What's unclear: Airtable field names are set by whoever creates them in the UI. The `extract_brand_config()` mapping dict controls the names — they should be human-readable for staff editing in Airtable.
   - Recommendation: Use the names in the code example above ("Brand Primary Color", "Brand Font Family", etc.). These are clear and follow Airtable's convention of Title Case with spaces. The mapping in `extract_brand_config()` makes them easy to change later without touching the model.

2. **Animation speed modifier implementation**
   - What we know: Stage modifiers affect animation speed. FADE_IN_FRAMES and FADE_OUT_FRAMES are currently constants in constants.ts.
   - What's unclear: Whether animation speed should change the frame counts (and thus affect timing relative to total duration) or change a spring/interpolation parameter.
   - Recommendation: Expose `animationSpeedMs` as a brand config field passed to Remotion. In TextOverlay.tsx, convert ms to frames using `fps`: `const fadeFrames = Math.round(animationSpeedMs / 1000 * fps)`. Keeps animation timing relative to duration. Start with this approach — it's the simplest and most predictable.

3. **Brand config not found for client_id**
   - What we know: `get_client()` raises `httpx.HTTPStatusError` if the record doesn't exist (404).
   - What's unclear: Should a missing client_id fail the render or fall back to defaults?
   - Recommendation: If `client_id` is provided and Airtable returns 404, fail the render with a clear error message. If `client_id` is absent (None), use defaults silently. This prevents silent misidentification of clients.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Python framework | pytest with pytest-asyncio (asyncio_mode = "auto") |
| Python config | `pyproject.toml` — `[tool.pytest.ini_options]` |
| Python quick run | `python -m pytest tests/test_brand_config.py -x` |
| Python full suite | `python -m pytest tests/ -x` |
| TypeScript framework | vitest ^3.0.0 |
| TS config | `remotion-service/vitest.config.ts` |
| TS quick run | `cd remotion-service && npm test -- --reporter=verbose src/__tests__/brand-styles.test.ts` |
| TS full suite | `cd remotion-service && npm test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TMPL-01 | Two different BrandConfigs produce different resolved render payloads | unit (Python) | `python -m pytest tests/test_brand_config.py::test_different_brands_produce_different_payloads -x` | ❌ Wave 0 |
| TMPL-01 | BrandConfig with no fields produces all-default values | unit (Python) | `python -m pytest tests/test_brand_config.py::test_brand_config_defaults -x` | ❌ Wave 0 |
| TMPL-01 | Invalid hex color rejected by BrandConfig validator | unit (Python) | `python -m pytest tests/test_brand_config.py::test_invalid_hex_rejected -x` | ❌ Wave 0 |
| TMPL-01 | Font family not in curated set rejected | unit (Python) | `python -m pytest tests/test_brand_config.py::test_invalid_font_rejected -x` | ❌ Wave 0 |
| TMPL-01 | extract_brand_config() handles empty string Airtable fields gracefully | unit (Python) | `python -m pytest tests/test_brand_config.py::test_extract_brand_config_empty_strings -x` | ❌ Wave 0 |
| TMPL-01 | extract_brand_config() with invalid Airtable value falls back to defaults | unit (Python) | `python -m pytest tests/test_brand_config.py::test_extract_brand_config_fallback -x` | ❌ Wave 0 |
| TMPL-01 | ReelInputSchema accepts brandConfig with all optional fields | unit (TS) | `cd remotion-service && npm test -- src/__tests__/schema.test.ts` | ❌ Wave 0 (extend existing) |
| TMPL-01 | ReelInputSchema with no brandConfig applies full defaults | unit (TS) | `cd remotion-service && npm test -- src/__tests__/schema.test.ts` | ❌ Wave 0 (extend existing) |
| TMPL-01 | getFontFamily("Rubik") returns Rubik's fontFamily CSS string | unit (TS) | `cd remotion-service && npm test -- src/__tests__/font-loading.test.ts` | ❌ Wave 0 (extend existing) |
| TMPL-01 | getFontFamily(undefined) returns DEFAULT_FONT_FAMILY (Heebo) | unit (TS) | `cd remotion-service && npm test -- src/__tests__/font-loading.test.ts` | ❌ Wave 0 (extend existing) |
| TMPL-01 | textPosition "center" maps to justifyContent "center" in ReelTemplate | unit (TS) | `cd remotion-service && npm test -- src/__tests__/brand-styles.test.ts` | ❌ Wave 0 |
| TMPL-01 | POST /render with client_id fetches brand from Airtable and includes it in renderer.render() call | integration (Python) | `python -m pytest tests/test_render_routes.py::TestBrandConfig -x` | ❌ Wave 0 |
| TMPL-01 | POST /render with no client_id uses defaults (backward compat) | integration (Python) | `python -m pytest tests/test_render_routes.py::TestBrandConfigDefaults -x` | ❌ Wave 0 |
| TMPL-01 | Concurrent renders with different client_ids produce isolated brand configs | integration (Python) | `python -m pytest tests/test_brand_config.py::test_concurrent_brand_isolation -x` | ❌ Wave 0 |
| TMPL-02 | Stage 1 resolve_brand_for_render produces larger hook font size than stage 3 | unit (Python) | `python -m pytest tests/test_brand_config.py::test_stage_1_larger_than_stage_3 -x` | ❌ Wave 0 |
| TMPL-02 | Stage 1 produces hookFontWeight 900; stage 3 produces 700 | unit (Python) | `python -m pytest tests/test_brand_config.py::test_stage_modifier_weights -x` | ❌ Wave 0 |
| TMPL-02 | Stage modifiers apply on top of brand base — different brands with same stage show different absolute sizes | unit (Python) | `python -m pytest tests/test_brand_config.py::test_stage_modifiers_relative_to_brand -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_brand_config.py -x && cd remotion-service && npm test -- src/__tests__/brand-styles.test.ts`
- **Per wave merge:** `python -m pytest tests/ -x && cd remotion-service && npm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_brand_config.py` — covers TMPL-01 (BrandConfig model, extract_brand_config, merge, isolation) and TMPL-02 (stage modifiers)
- [ ] `remotion-service/src/__tests__/brand-styles.test.ts` — covers TMPL-01 (position map, textAlign, style helper exports)
- [ ] Extend `remotion-service/src/__tests__/schema.test.ts` — brandConfig optional fields + defaults
- [ ] Extend `remotion-service/src/__tests__/font-loading.test.ts` — getFontFamily() with all four curated fonts
- [ ] `renderer/brand.py` — new module, no install needed (stdlib only)
- [ ] No new package installs required

---

## Sources

### Primary (HIGH confidence)
- Inspected `/Users/openclaw/wandi-agent/remotion-service/node_modules/@remotion/google-fonts/dist/esm/Heebo.mjs`, `Rubik.mjs`, `Assistant.mjs`, `FrankRuhlLibre.mjs` — confirmed `hebrew` subset available in all four, confirmed `loadFont(style, options)` API signature
- Read all existing source files directly: `fonts.ts`, `schemas.ts`, `TextOverlay.tsx`, `ReelTemplate.tsx`, `constants.ts`, `render-queue.ts`, `models.py`, `remotion.py`, `airtable_client.py`, `main.py`, `config.py`
- Read all existing test files: `schema.test.ts`, `font-loading.test.ts`, `rtl-styles.test.ts`, `safe-zone.test.ts`, `render-queue.test.ts`, `test_render_routes.py`, `conftest.py`
- Read `pyproject.toml` and `vitest.config.ts` for test runner configuration
- Read `SDMF_agent_knowledge.md` for SDMF awareness stage definitions
- Read `.planning/REQUIREMENTS.md` and `.planning/STATE.md` for project state

### Secondary (MEDIUM confidence)
- Zod v4 `.default({})` on object schema behavior — confirmed consistent with installed zod@4.3.6 (saw in test files and package.json)

### Tertiary (LOW confidence)
- Stage modifier exact values (1.15x, 1.10x, etc.) — chosen by judgment; no external source. Flag for product review: are the subtle differences visually sufficient?

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries directly inspected in node_modules and existing source files; no new installs
- Architecture: HIGH — patterns derived from direct code inspection of existing Phase 1/2 decisions; all integration points verified
- Font loading: HIGH — four font modules directly inspected for `hebrew` subset presence and `loadFont` API shape
- Stage modifiers: MEDIUM — structure is correct (global map, scale multipliers); exact numeric values are LOW confidence and should be tuned visually
- Pitfalls: HIGH — derived from existing Phase 1 decisions in STATE.md (font timeout, delayRender, static imports) plus Airtable empty string behavior verified in existing `extract_brand_config` pattern

**Research date:** 2026-03-11
**Valid until:** 2026-04-10 (stable libraries; Remotion 4.x API unlikely to change significantly)
