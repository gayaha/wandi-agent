# Feature Research

**Domain:** Programmatic video rendering for social media content (Instagram Reels)
**Researched:** 2026-03-11
**Confidence:** HIGH (core rendering features), MEDIUM (competitive landscape, RTL specifics)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that must exist for the output to be usable. Missing any of these means the rendered video is unpublishable or the service is broken from the client's perspective.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Correct output format (1080x1920 MP4, H.264, AAC, 30fps) | Instagram Reels rejects or degrades anything off-spec; wrong codec triggers aggressive re-encoding | LOW | H.264 video + AAC audio at 256kbps/48kHz; export at exactly 1080p rather than 4K (Instagram compresses to 1080p anyway, causing quality loss) |
| Text visible within the safe zone | Instagram UI (username, CTA buttons, footer) covers top ~250px and bottom ~250px of a 1080x1920 frame; text outside is hidden from viewers | LOW | Safe zone is roughly 1080x1420px centered on canvas; enforce in template, not per-render |
| Readable text contrast | Text must be legible on motion video backgrounds — minimum 4.5:1 contrast ratio (WCAG AA) | LOW | Solid background behind text, semi-transparent overlay, or drop-shadow are all valid; pick one per template |
| RTL text direction for Hebrew | Hebrew reads right-to-left; LTR rendering makes text backward and word order wrong | MEDIUM | CSS `direction: rtl` + `unicode-bidi: embed` on text elements; Remotion renders through Chromium so CSS applies normally |
| Bidirectional text handling (Hebrew + English mix) | SDMF content regularly mixes Hebrew body with English terms, brand names, numbers | HIGH | Unicode BiDi algorithm applies automatically when `dir="rtl"` is set in HTML/React; however punctuation placement (commas, periods, question marks) can drift — requires explicit Unicode control characters (U+202B, U+200F) around mixed segments and thorough testing |
| Per-client brand colors applied to text and overlays | Each business client has distinct brand identity; undifferentiated output looks generic and undermines client trust | MEDIUM | Template system takes a brand config object (colors, fonts) and applies via CSS variables or inline styles |
| Per-client font selection | Brand typography is non-negotiable for professional output | MEDIUM | Remotion supports Google Fonts via `@remotion/google-fonts` or custom font files via `loadFont()`; Hebrew requires a Hebrew-capable font (Heebo, Assistant, Frank Ruhl Libre all have Latin+Hebrew coverage) |
| Static text overlay on video | Core product — text content rendered on top of raw footage | LOW | Remotion `<AbsoluteFill>` with positioned `<div>` over `<Video>` component |
| Video plays at original speed (no distortion) | Client-supplied raw footage must be presented naturally | LOW | Remotion `<Video>` component passes through the source; no default speed mutation |
| Output accessible via URL | Rendered MP4 must be downloadable by the Python backend for Airtable attachment upload | LOW | Remotion SSR renders to local disk; Python service fetches file and uploads to Airtable attachment endpoint |
| Render triggered via HTTP API | Python backend must be able to initiate a render and receive a result without manual intervention | MEDIUM | Remotion SSR API exposed via a Node.js Express/Fastify wrapper; Python calls it via HTTP POST |

---

### Differentiators (Competitive Advantage)

Features that lift the output above generic video editing tools and justify the platform's existence for business clients.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Animated text entry/exit (fade, slide, spring) | Polished motion design distinguishes brand content from static-looking videos; key reason Remotion was chosen over FFmpeg | MEDIUM | Remotion `interpolate()` for fade (opacity 0→1 over N frames), `spring()` for natural motion; enter/exit timing configured per-animation-segment |
| Per-client brand template system | Business owners get output that matches their brand without any manual editing step | MEDIUM | Template is a JSON/TS config: `{ primaryColor, secondaryColor, fontFamily, textPosition, overlayOpacity }`; Remotion composition receives this as `inputProps` |
| Abstraction layer (renderer-agnostic API) | Protects the calling Python code from the Remotion implementation; allows future engine swap (FFmpeg, Creatomate, etc.) without touching business logic | MEDIUM | Python defines a `RendererProtocol` (or ABC) with `render(text, video_url, template_id) -> str`; Remotion adapter implements it; calling code never knows which engine ran |
| Awareness-stage-aware text styling | SDMF methodology uses 5 awareness stages — text tone and visual weight can differ per stage | MEDIUM | Map stage ID to a set of style overrides in the template config; awareness-stage hook in the template component |
| Multiple text segments with independent timing | Real Reels content has intro hooks, body text, CTAs — each appears and disappears at different times | HIGH | Define text segments as an array: `[{ text, startFrame, endFrame, animation }]`; each renders only within its frame window |
| Hebrew font rendering at video quality | Hebrew glyphs rendered via Chromium in Remotion inherit the full font shaping pipeline (correct ligatures, nikud if needed) | LOW | Quality comes from font choice; Heebo and Assistant are the cleanest Hebrew fonts at video resolution |
| Supabase Storage as raw video source | Video URL from Supabase is fetched at render time without intermediate download step in Python | LOW | Pass Supabase signed URL as `videoSrc` prop; Remotion fetches it during render |

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem desirable but should be explicitly excluded from this milestone.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto video selection (matching content to footage by tags/AI) | Would make the pipeline fully autonomous — no human picks the video | Separate milestone; mixing it here conflates content strategy with rendering; doubles scope and testing surface | Implement as a separate pre-render step in a future milestone; keep renderer stateless — it receives a video URL, period |
| Real-time preview in browser | Designers want to see changes live | Remotion's Studio already provides this during development; exposing it to end-clients requires a full frontend feature that belongs in the React/Lovable app, not the renderer service | Use Remotion Studio locally for development; defer client-facing preview UI to the frontend team |
| Audio voiceover or music mixing | Natural extension of "video production" thinking | Adds ffmpeg dependency for audio mixing, licensing concerns for music, and sync complexity; orthogonal to current value prop (text overlay on silent footage) | Keep renders mute or passthrough source audio; add music as a separate future milestone |
| Multiple output formats (landscape, square, Stories) | Other Instagram formats exist | Blows up template complexity; 9:16 is the only validated format for this milestone; each format needs its own safe-zone math and template | Define a format parameter in the abstraction layer now (future-proofing), but implement only `REELS_9_16` |
| Watermarking for free-tier differentiation | Common SaaS upsell pattern | Adds conditional rendering logic tied to billing state; renderer should remain stateless and billing-unaware | Watermark logic belongs in the API gateway or business layer, not the renderer |
| Automatic subtitle/transcription generation | Accessibility is valuable | Requires speech-to-text pipeline (Whisper or similar) — entirely separate system; current use case is rendering pre-written text content, not transcribing speech | Render supplied text as subtitles; transcription is a different pipeline |
| Client self-service template editor | Clients want control | Full visual template editor is a product in itself (see Canva, Remotion's Editor Starter at $1200+); far exceeds milestone scope | Provide template config as structured JSON managed by the operator; client customization happens through the Airtable client record |

---

## Feature Dependencies

```
[Per-client brand template system]
    └──requires──> [Template config schema (colors, fonts, positions)]
                       └──requires──> [Remotion inputProps wiring]

[Animated text entry/exit]
    └──requires──> [Static text overlay on video]
                       └──requires──> [Correct output format]

[Multiple text segments with independent timing]
    └──requires──> [Static text overlay on video]
    └──requires──> [Animated text entry/exit]

[RTL Hebrew text direction]
    └──requires──> [Hebrew-capable font loaded]
    └──requires──> [Bidirectional text handling (Hebrew + English mix)]

[Render triggered via HTTP API]
    └──requires──> [Abstraction layer (renderer-agnostic API)]
    └──requires──> [Remotion SSR render function wired]

[Output accessible via URL]
    └──requires──> [Render triggered via HTTP API]
    └──requires──> [Rendered file saved to disk or returned]

[Awareness-stage-aware text styling]
    └──enhances──> [Per-client brand template system]

[Supabase Storage as raw video source]
    └──enhances──> [Static text overlay on video]
```

### Dependency Notes

- **Animated text entry/exit requires Static text overlay:** Animation is a property of a text element that already exists in the composition. The base overlay must work before timing/animation is layered on.
- **RTL requires Hebrew-capable font:** Correct Unicode shaping for Hebrew will silently fail or render tofu (empty boxes) if the loaded font does not include the Hebrew Unicode block (U+0590–U+05FF). Font selection is a prerequisite, not an afterthought.
- **Bidirectional text handling requires RTL:** BiDi is a secondary concern; it only arises after the base RTL direction is established. The two are often conflated but should be implemented in order.
- **Multiple text segments enhances Animated text entry/exit:** Each segment has its own entry/exit animation window. Segments without independent timing devolve into one static overlay for the whole video duration.
- **Abstraction layer is a prerequisite for the API endpoint:** The Python-side interface must be defined before the HTTP handler is written; otherwise the handler couples directly to Remotion internals, defeating the swappability goal.

---

## MVP Definition

### Launch With (v1)

Minimum viable for this milestone: a rendered Instagram Reel with branded Hebrew text overlay, delivered as an MP4 URL.

- [ ] Correct output format — 1080x1920 MP4, H.264, AAC, 30fps; no format = no uploadable video
- [ ] Safe-zone-aware text positioning — text inside the 1080x1420px safe band; foundational for all templates
- [ ] RTL Hebrew text direction — mandatory per project constraints; without it content is unreadable
- [ ] Bidirectional Hebrew+English text handling — SDMF content always mixes both; this is not optional
- [ ] Hebrew-capable font (Heebo or Assistant) — prerequisite for RTL to function visually
- [ ] Static text overlay on video — core product deliverable
- [ ] Animated text entry/exit (fade-in at least) — reason Remotion was chosen over FFmpeg; at minimum a simple opacity fade
- [ ] Per-client brand template (colors, font, position) — clients are businesses with brand identities; generic styling is a regression
- [ ] Render triggered via HTTP API — decoupled trigger that Python backend and future callers can use
- [ ] Abstraction layer in Python — swappability requirement from project constraints; must be in v1 to avoid coupling
- [ ] Output accessible via URL — Airtable attachment requires a URL; without it the render is stranded

### Add After Validation (v1.x)

- [ ] Multiple independent text segments with timing — add when clients request chapter-style or multi-message Reels; v1 can treat the whole content block as one timed segment
- [ ] Awareness-stage-aware text styling — add when the SDMF content pipeline starts tagging stage in render requests; v1 uses a single style per client
- [ ] Text contrast enforcement (4.5:1 check) — add as a render-time validation warning; v1 relies on template design to guarantee contrast

### Future Consideration (v2+)

- [ ] Multiple output format support (4:5 feed, 1:1 square) — defer until non-Reels content is in scope
- [ ] Audio mixing / background music — separate pipeline decision; requires licensing and audio sync work
- [ ] Auto video selection — next milestone per PROJECT.md
- [ ] Client-facing preview UI — belongs in the React/Lovable frontend, not this service

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Correct output format (MP4, codec, fps) | HIGH | LOW | P1 |
| Safe-zone-aware text positioning | HIGH | LOW | P1 |
| RTL Hebrew text direction | HIGH | MEDIUM | P1 |
| Bidirectional Hebrew+English handling | HIGH | HIGH | P1 |
| Hebrew-capable font loading | HIGH | LOW | P1 |
| Static text overlay on video | HIGH | LOW | P1 |
| Fade-in/out text animation | HIGH | MEDIUM | P1 |
| Per-client brand template system | HIGH | MEDIUM | P1 |
| HTTP render API endpoint | HIGH | MEDIUM | P1 |
| Python abstraction layer | MEDIUM | MEDIUM | P1 |
| Output accessible via URL | HIGH | LOW | P1 |
| Multiple text segments with timing | MEDIUM | HIGH | P2 |
| Awareness-stage text styling | MEDIUM | MEDIUM | P2 |
| Contrast enforcement at render time | LOW | LOW | P2 |
| Multi-format output (4:5, 1:1) | LOW | HIGH | P3 |
| Audio mixing | LOW | HIGH | P3 |
| Client self-service template editor | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

Relevant comparisons are tools that also do programmatic video generation with template and brand customization.

| Feature | Creatomate (API-first) | Canva (GUI-first) | Remotion (code-first, chosen) |
|---------|------------------------|---------------------|-------------------------------|
| Template variables (text, color, font) | YES — JSON/REST API, template editor | YES — Brand Hub, GUI only | YES — React `inputProps`, full code control |
| Per-client brand config | YES — via API parameters | YES — Brand Hub per org | YES — custom; must implement data model |
| RTL/Hebrew support | UNKNOWN — not documented | PARTIAL — UI is RTL-aware but video export behavior unverified | YES — CSS-native via Chromium renderer |
| Animation (fade, spring) | YES — JSON keyframes | LIMITED — preset animations only | YES — `interpolate()` + `spring()`, fully custom |
| Server-side rendering API | YES — cloud REST API | NO — GUI required | YES — `@remotion/renderer` SSR API |
| Output format control | YES — format param | LIMITED — preset formats | YES — full codec/fps/resolution control |
| Self-hosted option | NO — SaaS only | NO — SaaS only | YES — runs in Docker on any infra |
| Abstraction/swappability | N/A (is the vendor) | N/A (is the vendor) | YES — can be wrapped behind interface |

**Why Remotion is the right choice for this project:** RTL via native CSS (not a bolted-on workaround), full animation control (required for enter/exit), self-hosted (data stays in our infra), and code-native (templates as TypeScript, not GUI drag-and-drop). The code-first approach means templates are version-controlled and reproducible.

---

## Sources

- [Remotion — The Fundamentals](https://www.remotion.dev/docs/the-fundamentals) — core rendering model
- [Remotion — Animating Properties](https://www.remotion.dev/docs/animating-properties) — `interpolate()`, `spring()`, frame-based animation
- [Remotion — SSR API](https://www.remotion.dev/docs/ssr) — server-side rendering options
- [Instagram Reels Safe Zone Guide (2026) — Kreatli](https://kreatli.com/guides/instagram-reels-safe-zone) — safe zone dimensions
- [Instagram Reel Size and Dimensions (2026) — Outfy](https://www.outfy.com/blog/instagram-reel-size/) — format spec confirmation
- [Instagram Video Size Format Specs 2026 — Social Rails](https://socialrails.com/blog/instagram-video-size-format-specifications-guide) — codec and audio specs
- [RTL Subtitling Frustrations — ArtlangsTV](https://artlangstv.com/news-detail/tackling-the-frustrations-of-rtl-video-subtitling--when-punctuation-plays-tricks-in-arabic-and-beyond) — BiDi punctuation pitfalls in video
- [Hebrew/Arabic RTL Airtable Community thread](https://community.airtable.com/base-design-9/rtl-support-for-hebrew-arabic-text-mixed-with-english-interface-alignment-issues-28969) — mixed-direction alignment issues
- [Creatomate Programmatic Video Editing](https://creatomate.com/how-to/programmatic-video-editing) — template variable system reference
- [Text Overlays on Video (2026) — Project Aeon](https://project-aeon.com/blogs/text-overlay-on-video-master-engaging-techniques) — text overlay best practices
- [Instagram Safe Zones — Zeely](https://zeely.ai/blog/master-instagram-safe-zones/) — safe zone practical guidance

---

*Feature research for: Wandi — Programmatic Instagram Reels Video Renderer*
*Researched: 2026-03-11*
