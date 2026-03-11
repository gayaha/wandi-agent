# Requirements: Wandi Video Renderer

**Defined:** 2026-03-11
**Core Value:** Business owners get publish-ready Instagram Reels with branded text overlays — no manual video editing.

## v1 Requirements

Requirements for the video renderer milestone. Each maps to roadmap phases.

### Rendering Core

- [x] **REND-01**: Renderer produces 1080x1920 vertical MP4 with H.264 video, AAC audio at 30fps — Instagram Reels spec
- [x] **REND-02**: User can see generated text content overlaid on raw video footage in the rendered output
- [x] **REND-03**: Text overlays are positioned within the Instagram safe zone (avoiding top ~250px and bottom ~250px UI overlap)
- [x] **REND-04**: Text elements animate on entry and exit (fade-in/out at minimum, slide and spring as options)

### Hebrew / RTL

- [x] **HEBR-01**: Hebrew text renders right-to-left correctly in video output
- [x] **HEBR-02**: Mixed Hebrew + English text in the same element renders with correct bidirectional ordering (punctuation, numbers, English words positioned correctly)
- [x] **HEBR-03**: Renderer loads a Hebrew-capable font (Heebo or Assistant) that covers Latin + Hebrew Unicode blocks

### Text Segments

- [ ] **SEGM-01**: Render request can specify multiple text segments (hook, body, CTA) each with independent start/end timing and animation

### Brand Templates

- [ ] **TMPL-01**: Each client has a brand template defining primary/secondary colors, font selection, text positioning, and overlay style
- [ ] **TMPL-02**: Text styling varies by SDMF awareness stage (e.g., Stage 1 bold/attention-grabbing vs Stage 3 authoritative/methodical)

### Integration

- [ ] **INTG-01**: Python backend exposes an HTTP endpoint that accepts render requests (text segments + video URL + template config) and returns a job ID
- [ ] **INTG-02**: Python backend defines a `VideoRendererProtocol` abstraction that can be implemented by any rendering engine (Remotion today, others tomorrow)
- [ ] **INTG-03**: Rendered MP4 is accessible via URL and saved as an Airtable attachment on the content queue record
- [ ] **INTG-04**: Raw source video is fetched from Supabase Storage at render time using the video URL
- [ ] **INTG-05**: Render API uses async job pattern (HTTP 202 + polling/callback) to handle 30-300 second render times without timeout

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Quality

- **QUAL-01**: Renderer validates text contrast ratio (4.5:1 minimum) against video background and warns if below threshold

### Multi-Format

- **FMTT-01**: Renderer supports additional output formats (4:5 feed, 1:1 square, 9:16 Stories) via format parameter

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Auto video selection (matching content to footage by tags) | Separate milestone — conflates content strategy with rendering |
| Audio mixing / background music | Separate pipeline, licensing concerns, orthogonal to text overlay |
| Real-time preview in browser | Remotion Studio covers dev preview; client-facing preview belongs in frontend |
| Multiple output formats | Only 9:16 Reels validated for this milestone; each format needs own safe-zone math |
| Watermarking | Billing logic belongs in API gateway, not renderer |
| Subtitle/transcription generation | Requires speech-to-text pipeline (Whisper); different system entirely |
| Client self-service template editor | Product in itself; far exceeds milestone scope |
| Frontend changes | Separate React/Lovable app, not in this repo |
| Modifications to existing content generation pipeline | Must remain unchanged |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REND-01 | Phase 1 | Complete (01-03) |
| REND-02 | Phase 1 | Complete (01-02) |
| REND-03 | Phase 1 | Complete (01-02) |
| REND-04 | Phase 1 | Complete (01-02) |
| HEBR-01 | Phase 1 | Complete (01-02) |
| HEBR-02 | Phase 1 | Complete (01-03) |
| HEBR-03 | Phase 1 | Complete (01-02) |
| SEGM-01 | Phase 4 | Pending |
| TMPL-01 | Phase 3 | Pending |
| TMPL-02 | Phase 3 | Pending |
| INTG-01 | Phase 2 | Pending |
| INTG-02 | Phase 2 | Pending |
| INTG-03 | Phase 2 | Pending |
| INTG-04 | Phase 2 | Pending |
| INTG-05 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-11 after roadmap creation — all 15 requirements mapped*
