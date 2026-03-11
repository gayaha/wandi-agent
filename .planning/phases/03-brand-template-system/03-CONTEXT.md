# Phase 3: Brand Template System - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

The render pipeline accepts per-client brand configuration — primary/secondary colors, font family, text positioning, and awareness-stage styling — and produces visually distinct, branded output for each client.

This phase delivers brand template support ONLY. Multi-segment text (Phase 4) is a separate phase.

</domain>

<decisions>
## Implementation Decisions

### Brand Visual Identity
- Two-color model: primary color (hook text, accents) + secondary color (body text or overlay tint)
- Curated font set: 3-5 pre-vetted Hebrew+Latin Google Fonts (Heebo, Assistant, Rubik, etc.) — client picks from list. Guarantees Hebrew rendering works without fallback issues.
- Overlay background is configurable per brand: overlay color + opacity (0.3-0.8). Still a solid box with rounded corners.
- Brand template sets a default animation style (fade/slide). Can be overridden per render request for flexibility.
- Current hardcoded values (Heebo, white text, rgba(0,0,0,0.55)) become the defaults for clients without brand config.

### Awareness-Stage Styling
- Global SDMF stage map shared across all brands — not per-brand stage configs
- Stage map applies modifiers on top of the brand's base colors/fonts (e.g., scale font size, adjust weight)
- 3 visual tiers: attention (stages 1-2), authority (stage 3), conversion (stages 4-5)
- Awareness stage is passed explicitly in the render request (not inferred from Airtable)
- Stage modifiers affect: font weight, font size scaling, animation speed — subtle differentiation within brand identity

### Template Data Storage
- Brand fields added to existing Airtable Clients table (primary_color, secondary_color, font_family, etc.)
- Keeps all client data in one place — staff edits brand in same Airtable view they already use
- Render request includes client_id (Airtable record ID) — Python fetches brand config from Clients table before calling Remotion
- Fresh fetch from Airtable on every render (no caching) — simplest approach, ensures changes picked up immediately
- Default fallback: clients without brand config get the current hardcoded look (Heebo, white, dark overlay). Brand config is an enhancement, not a requirement.

### Text Positioning & Sizing
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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `remotion-service/remotion/TextOverlay.tsx`: Currently hardcodes colors (#FFFFFF), background (rgba(0,0,0,0.55)), font sizes (52/36). These become overridable by brand config via inputProps.
- `remotion-service/remotion/fonts.ts`: Loads Heebo only. Must extend to dynamically load from curated font list based on brand config.
- `remotion-service/remotion/schemas.ts`: ReelInputSchema needs brand config fields (colors, font, sizes, position).
- `renderer/models.py`: RenderRequest needs client_id and awareness_stage fields. Brand config flows as part of the Remotion render payload.
- `airtable_client.py`: Has `get_client()` — already fetches client record. Brand fields will be on the same record, accessible with existing function.
- `remotion-service/remotion/constants.ts`: SAFE_ZONE values are fixed. Position presets (top/center/bottom) calculate offsets within these bounds.

### Established Patterns
- Zod schema validation at enqueue time in Remotion service (Phase 1 decision)
- Pydantic models for Python-side validation (renderer/models.py)
- Optional fields with defaults — brand config follows this pattern (all brand fields optional, defaults to current look)
- `airtable_client.py` uses httpx with async pattern — brand config fetch follows same pattern

### Integration Points
- `renderer/models.py`: Add client_id, awareness_stage to RenderRequest. Add BrandConfig model.
- `remotion-service/remotion/schemas.ts`: Add brand config fields to ReelInputSchema (Zod)
- `remotion-service/remotion/TextOverlay.tsx`: Accept brand config props for colors, font, sizes
- `remotion-service/remotion/ReelTemplate.tsx`: Pass brand config through to TextOverlay
- `remotion-service/remotion/fonts.ts`: Dynamic font loading based on brand's chosen font family
- `airtable_client.py`: Add function to fetch brand config from Clients table fields
- `main.py _run_render()`: Insert brand config fetch step before calling Remotion service
- `config.py`: Airtable Clients table ID already configured (TABLE_CLIENTS)

</code_context>

<specifics>
## Specific Ideas

- Current Heebo + white text + dark overlay is already a clean professional look — it should be the fallback default, not lost
- Brand templates should make each client's output visually distinct enough that the client recognizes "their brand" in the video
- SDMF stage styling is about intensity/tone, not about completely different designs — subtle modifiers on the brand base
- The curated font list ensures every font is tested with Hebrew rendering — no surprise glyph fallbacks in production

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-brand-template-system*
*Context gathered: 2026-03-11*
