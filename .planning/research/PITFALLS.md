# Pitfalls Research

**Domain:** Remotion video rendering integration — Python/FastAPI backend, Hebrew RTL text, Instagram Reels output
**Researched:** 2026-03-11
**Confidence:** MEDIUM (Remotion-specific: HIGH via official docs; RTL in video context: MEDIUM via community; cross-service patterns: MEDIUM via official FastAPI docs)

---

## Critical Pitfalls

### Pitfall 1: Hebrew RTL Text Reversal from `unicode-bidi: bidi-override`

**What goes wrong:**
Hebrew text renders with individual characters reversed (right characters appear on the left), making text completely unreadable. This happens silently — the render completes successfully, but the output looks broken.

**Why it happens:**
CSS resets, normalize stylesheets, or component libraries sometimes apply `unicode-bidi: bidi-override` globally or to container elements. This property forces all text to render strictly in the `direction` property's order, ignoring the Unicode Bidirectional Algorithm. Combined with any LTR default, Hebrew letters appear in reversed character order within each word.

**How to avoid:**
- Never use `unicode-bidi: bidi-override` on containers that hold Hebrew text.
- Always set `direction: rtl` AND `unicode-bidi: embed` (or `isolate`) on Hebrew text containers — not `bidi-override`.
- For mixed Hebrew/English content, use `unicode-bidi: isolate` per text segment, not `bidi-override` on the parent.
- Add a visual smoke test to Phase 1: render a Hebrew sentence with embedded English and verify character order in the output frame.

**Warning signs:**
- Hebrew words appear but letters within each word are reversed (e.g., "שלום" renders as "מולש").
- Text looks like it was typed backwards but positioned correctly.
- The issue only manifests in rendered output, not necessarily in browser preview (rendering and preview use different pipelines).

**Phase to address:** Phase 1 (Remotion service setup) — verify RTL rendering before building any template logic.

---

### Pitfall 2: Font Not Loaded at Render Time — Silent Fallback to System Font

**What goes wrong:**
Remotion renders the video successfully, but Hebrew text displays in a generic system font (or no visible text at all if the system font lacks Hebrew glyphs). The font was loaded for preview but not guaranteed to be available at render time in a headless/server environment.

**Why it happens:**
Calling `loadFont()` without blocking on it, or relying on CSS `@import` in a way that races with the render start. On servers, `loadFont()` from `@remotion/google-fonts` attempts to download all weights and subsets by default — this can trigger a `delayRender()` timeout (28–58 seconds) if the network is slow or the font request is large, causing Remotion to abort and fall back silently.

**How to avoid:**
- Always call `loadFont()` at the top level of the composition module (not inside a component), and await its promise with `delayRender()`/`continueRender()`.
- Narrow the font load: specify only required weights (e.g., `{ weights: ['400', '700'] }`) and the `hebrew` subset explicitly. This prevents timeout caused by loading all 20+ weights of a font.
- Bundle Hebrew fonts locally in `public/` folder and load via the `FontFace` API to avoid network dependency during render.
- Validate with `validateFontIsLoaded: true` in any `measureText()` call to surface font loading failures early.
- Test font loading with `--log verbose` flag on first render.

**Warning signs:**
- Text appears in Times New Roman or a generic sans-serif instead of the brand font.
- Render times become long (30+ seconds for a simple composition) — indicates font download timeout race.
- `delayRender() was called but not cleared after 28000ms` error in render logs.

**Phase to address:** Phase 1 (Remotion service setup) — include font loading verification in the "hello world" render before any template work.

---

### Pitfall 3: `OffthreadVideo` Timeout When Loading Raw Video from Supabase Signed URLs

**What goes wrong:**
Renders fail with a timeout error or hang indefinitely because Remotion's `OffthreadVideo` component must download the entire source video before it can extract a single frame. For a 30–90 second raw video at full quality, this can easily exceed Remotion's default 30-second `delayRender()` timeout.

**Why it happens:**
`OffthreadVideo` (which uses FFmpeg under the hood) does not support partial/range downloads — it needs the complete file. A 90-second 1080p video could be 500MB–2GB. Additionally, Supabase signed URLs expire; if the URL expires while the video is being downloaded mid-render, the download fails with a 403.

**How to avoid:**
- Increase `delayRenderTimeoutInMilliseconds` on the `<OffthreadVideo>` component (set to 120,000–180,000ms for large videos).
- Pre-download the raw video to the Node.js service's local disk before calling `renderMedia()`, then pass a `file://` path or `staticFile()` reference instead of a remote URL.
- Generate Supabase signed URLs with expiry of at least 10 minutes, not the default 60 seconds.
- For the service architecture: the Python backend should trigger a "prepare" step (download raw video locally) before the actual render job runs.

**Warning signs:**
- Renders fail consistently for videos over 30 seconds but succeed for short test clips.
- Error logs show `delayRender() was called but not cleared` on the video asset rather than on a fetch or font.
- Intermittent failures that correlate with render time (URL expires mid-download).

**Phase to address:** Phase 1 (Remotion service setup) and Phase 2 (video pipeline) — test with full-length raw video files from Supabase, not just short test clips.

---

### Pitfall 4: Mixed Hebrew/English Text With No Explicit `direction` per Segment

**What goes wrong:**
When Hebrew text includes embedded English words (brand names, numbers, URLs), the English segments render in the wrong position — appearing at the far left of a RTL container instead of inline in the flow. Punctuation (exclamation marks, parentheses) appears on the wrong side of the sentence.

**Why it happens:**
The Unicode Bidirectional Algorithm handles simple mixed text, but it does not correctly handle all edge cases, particularly when English appears at the end of a Hebrew sentence or when numbers appear mid-sentence. Without explicit `direction` and `unicode-bidi` attributes on inline spans, the browser's bidi algorithm makes heuristic decisions that are often wrong in video overlay contexts.

**How to avoid:**
- Wrap every inline English segment in `<span dir="ltr">...</span>` within a Hebrew RTL container.
- Set the outer text container to `direction: rtl; unicode-bidi: embed`.
- Do not rely on the browser's auto-detection — the content is generated programmatically, so the language boundary is known and should be marked explicitly.
- Test with representative content: a Hebrew sentence ending in an English brand name, a sentence with a number in the middle, and a sentence with parentheses.

**Warning signs:**
- English words or numbers appear at the wrong end of the line.
- Punctuation (period, exclamation mark, quote) is on the wrong side of the last word.
- Text looks correct in some templates but broken in others — indicates inconsistent `direction` application.

**Phase to address:** Phase 2 (template system) — build a test matrix of text patterns before implementing all template variations.

---

### Pitfall 5: Synchronous HTTP Timeout on Python → Node.js Render Calls

**What goes wrong:**
The Python FastAPI endpoint that triggers a render call blocks waiting for the Node.js service to complete and return. Video rendering takes 30–300 seconds. HTTP clients (and reverse proxies like nginx) have default timeouts of 30–60 seconds. The client gets a 504/timeout, retries, and the original render continues running — producing duplicate render jobs and potentially corrupt output files.

**Why it happens:**
Video rendering is inherently long-running. Treating it like a synchronous API call is the natural first implementation. Retry behavior at the HTTP layer (load balancers, client SDKs) multiplies the problem.

**How to avoid:**
- Design the render API as async from the start: Python submits a job to the Node.js service and gets back a `job_id` immediately (202 Accepted). The frontend polls a `/status/{job_id}` endpoint, or the service POSTs to a webhook when complete.
- On the Node.js service: use a simple in-process job queue (e.g., a `Map` of job states) for MVP; no need for Redis/BullMQ at this scale.
- Set explicit `asyncio.wait_for()` timeouts on any synchronous render calls used only in testing/CLI contexts.
- Configure nginx/reverse-proxy read timeout to at least 5 minutes if a synchronous API is unavoidable (not recommended).

**Warning signs:**
- Renders appear to complete but no output file is created — indicates the response was received after a timeout and the job was orphaned.
- Multiple identical renders in the output storage — indicates retry duplication.
- 504 Gateway Timeout errors appearing in logs right around 60 seconds.

**Phase to address:** Phase 1 (service architecture) — define the async job pattern before writing any endpoint code.

---

### Pitfall 6: GPU-Accelerated CSS Effects Causing 10x Slowdowns on Headless Servers

**What goes wrong:**
Compositions that look fast in Remotion Studio preview render 5–20x slower in the actual render pipeline. The render may take several minutes per video instead of seconds.

**Why it happens:**
Remotion Studio preview runs in a GPU-enabled browser. The render pipeline uses headless Chromium, which by default disables the GPU. CSS properties like `text-shadow`, `box-shadow`, `filter: blur()`, `filter: drop-shadow()`, and `background: linear-gradient()` rely on GPU acceleration when available. Without a GPU, Chromium falls back to software rendering, which is dramatically slower.

**How to avoid:**
- Avoid `text-shadow` with blur radius > 0. Use a pre-rendered shadow image as a background layer instead.
- Avoid `filter: blur()` on any element that changes per-frame. Blur a static background image as a pre-processed asset.
- Use `--gl=angle` or `--gl=vulkan` flags in the Remotion render command to force an OpenGL backend where available.
- Benchmark early: run `npx remotion benchmark` in the actual server environment (not your dev machine) before finalizing template designs.
- Use solid colors or simple gradients as brand colors rather than complex multi-stop gradients.

**Warning signs:**
- Template renders fine in Studio (seconds) but takes minutes when called via `renderMedia()`.
- Profiling shows specific frames with text-shadow or blur taking 500ms+ each.
- Render time scales linearly with number of animated frames rather than staying roughly constant.

**Phase to address:** Phase 2 (template design) — benchmark each template on the actual server environment before moving to integration testing.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Synchronous Python → Node.js HTTP call | Simpler code, no job tracking needed | Times out on any real render; forces retry logic everywhere | Never — always async from day one |
| Hardcode Hebrew as `direction: rtl` on root `<div>` only | Works for pure Hebrew content | Breaks mixed Hebrew/English bidi; requires rewrite when English appears | Never for mixed content |
| Skip `loadFont()`, use CSS `@import` | Less code | Font may not load before render starts; silent fallback to system font | Never in server-side rendering |
| Use `<Video>` instead of `<OffthreadVideo>` for Supabase URLs | Simpler component | CORS failures on signed URLs; codec support issues | Only if serving via staticFile() locally |
| Store rendered video locally on Node.js server disk | Simplest storage | Ephemeral on container restart; no persistence; Airtable can't access | Never in production |
| Hardcode font weights (e.g., `weight: 400`) | Works for initial build | Per-client bold/light brand fonts require template rework | MVP only if all clients use same weight |
| Pass raw video URL directly to `<OffthreadVideo>` | One fewer step | Signed URL expires mid-render; unreliable for long videos | Never for videos > 30 seconds |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Supabase Storage → Remotion | Pass signed URL directly to OffthreadVideo; URL expires mid-render | Download file to local disk first; pass local path to renderMedia |
| Supabase Storage signed URLs | Use default 60s expiry for render pipeline | Generate 10-minute+ expiry; or use public bucket URLs for raw source videos |
| Remotion → Airtable attachment | Upload the rendered file as Base64 via Airtable direct upload API | Upload large MP4 to intermediate storage first; pass the accessible URL to Airtable's attachment field (Airtable fetches by URL) |
| Python FastAPI → Node.js render service | Synchronous POST and await full render response | Submit job (202 + job_id), poll status endpoint, fetch result URL when complete |
| Node.js render service → file output | Write output to `/tmp` or process cwd | Write to a dedicated, persistent output directory; clean up old files explicitly |
| Airtable API rate limiting | Upload rendered video + update record in rapid succession | Respect 5 req/sec limit; batch record updates; add retry with exponential backoff on 429 |
| Remotion font loading → Hebrew Google Fonts | Load all subsets/weights by default | Specify `{ subsets: ['hebrew'], weights: ['400', '700'] }` explicitly |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| CSS `text-shadow` / `box-shadow` in headless Chromium | Render time per video 5-20x longer than preview | Replace with pre-rendered image assets; benchmark on server | Immediately — any production render without GPU |
| `OffthreadVideo` downloading full raw video on every render | Timeout errors; slow renders; Supabase egress costs | Pre-download and cache raw videos locally before render | Any video > 30 seconds |
| `concurrency` set too high in `renderMedia()` | Render slower than single-threaded; memory pressure; Chromium crashes | Benchmark with `npx remotion benchmark`; start at CPU count / 2 | > 2 simultaneous renders on a low-memory server |
| Multiple concurrent renders without a queue | Server OOM crash; Chromium zombie processes | Implement a simple job queue; limit concurrent `renderMedia()` calls to 1–2 | Any traffic beyond single-user testing |
| Loading all Google Font weights for Hebrew | `delayRender` timeout (28–58s) | Load only needed weights + `hebrew` subset | Any font with > 4 weights at slow network |
| Not memoizing inputProps in Remotion composition | Full tree re-render every frame; slow renders | Wrap inputProps with `useMemo()`; define outside component | Any composition receiving non-memoized props |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing Remotion render service on public port without auth | Unauthorized renders consume server resources and storage costs | Bind render service to `localhost` only; Python backend is the single entry point |
| Passing raw Supabase service key in render job payload | Key leaks via logs, error messages, or output files | Use signed URLs with short expiry; never put credentials in render input props |
| No rate limiting on Python render endpoint | Malicious actor triggers hundreds of renders, exhausting disk/CPU | Add per-client rate limiting on the FastAPI render endpoint from the start |
| Storing rendered videos in a public Supabase bucket | Anyone with the URL can access client video content | Use private bucket + signed URLs for serving; store in Airtable as attachment (requires authentication) |
| Airtable API key hardcoded in Node.js service | Key exposed in Node.js service environment or logs | Render service should not hold Airtable credentials; Python backend handles all Airtable writes |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No render status visibility | User submits render, sees nothing for 2–5 minutes, thinks it failed; submits again | Return job_id immediately; expose a status endpoint the frontend can poll |
| Render failure with no error message | User doesn't know if retry will help or if input is invalid | Capture and return Remotion's error output; distinguish user-input errors (bad video URL) from system errors (timeout) |
| Rendered video with wrong brand colors (hex typo in template) | Client videos use wrong brand; discovered at review stage | Include a "preview frame" endpoint that renders frame 1 without full encode — fast sanity check |
| Hebrew text clipped at container edge | Text runs off screen in vertical Reel format | Always test with the longest expected Hebrew headline (50–70 chars); implement text auto-sizing from Phase 2 |
| Silent font fallback in output | Rendered video uses wrong font; professional quality concern | Validate font loading and fail loudly (return error) rather than silently using system font |

---

## "Looks Done But Isn't" Checklist

- [ ] **RTL rendering:** Test complete: Hebrew sentence with embedded English brand name, numbers, and punctuation — verify character and word order in actual rendered MP4, not just preview.
- [ ] **Font in render:** Verify the brand font (not system fallback) appears in the rendered output file — open MP4 in a video player and zoom in, not just in Remotion Studio.
- [ ] **Full-length video:** Test render with a 60–90 second source video from Supabase, not just a 5-second test clip — verify no timeout and correct output duration.
- [ ] **Concurrent renders:** Run two render jobs simultaneously and verify: (a) both complete successfully, (b) output files are distinct and correct, (c) no server OOM.
- [ ] **Airtable attachment accessible:** After upload, verify the attachment URL is accessible from an external browser (not just API response says success).
- [ ] **Signed URL expiry:** Verify render completes even when the Supabase signed URL used for sourcing would expire within the render window.
- [ ] **Template isolation:** Verify per-client brand data (colors, font, positioning) from one client does not bleed into another client's render job.
- [ ] **Service restart recovery:** After restarting the Node.js render service, verify existing rendered videos are still accessible (not stored on ephemeral local disk).
- [ ] **Hebrew at edge cases:** Test with a single-word headline, a 70-character headline, and a headline with only numbers — all must render correctly RTL.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| RTL bidi reversal discovered in production | MEDIUM | Identify affected renders; fix CSS direction/unicode-bidi; re-render affected videos; no DB migration needed |
| Font fallback in production renders | LOW | Fix font loading code; re-render affected videos; straightforward if job IDs are tracked |
| Synchronous API timeout architecture | HIGH | Requires redesign of Python endpoint, Node.js service API, and any frontend polling logic; do before any frontend integration |
| Rendered videos stored on ephemeral disk | HIGH | Data loss; requires storage redesign and re-render of all videos; do not go to production with local disk storage |
| GPU CSS slowdown discovered post-launch | MEDIUM | Audit all template CSS for shadow/blur/gradient; replace with precomputed assets; re-deploy; re-render on request |
| Supabase signed URL expiry mid-render | LOW | Switch to pre-download pattern; no data loss; just render failures to retry |
| Concurrent render OOM crash | MEDIUM | Add job queue; lower concurrency; implement process monitoring; all existing jobs must be retried |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| RTL bidi reversal | Phase 1: Remotion service setup | Render test with Hebrew + English mixed text; verify character order in MP4 |
| Font not loaded at render time | Phase 1: Remotion service setup | Render with brand font; verify font in output (not system fallback) |
| OffthreadVideo timeout on long videos | Phase 1: Video pipeline (Supabase → render) | Test with 60s+ source video; verify no timeout |
| Mixed Hebrew/English bidi edge cases | Phase 2: Template system | Test matrix of text patterns (see checklist above) |
| Synchronous HTTP timeout Python → Node | Phase 1: Service architecture | Verify async job pattern with 201/202 + polling before any other work |
| GPU CSS slowdown in headless | Phase 2: Template design | Benchmark each template CSS in headless mode before finalizing |
| Concurrent render OOM | Phase 2 or 3: Load testing | Run 2–3 simultaneous renders; verify server stability |
| Supabase signed URL expiry | Phase 1: Video pipeline | Test with 5s signed URL expiry; verify render still completes (should fail if not using pre-download) |
| Airtable rate limit on attachment upload | Phase 3: Storage integration | Test rapid successive uploads; verify 429 handling and retry backoff |
| Template data isolation between clients | Phase 2: Template system | Run same template with two different client configs simultaneously; verify output differences |

---

## Sources

- Remotion official docs — Performance Tips: https://www.remotion.dev/docs/performance
- Remotion official docs — Debugging Timeouts: https://www.remotion.dev/docs/timeout
- Remotion official docs — Font Loading Errors: https://www.remotion.dev/docs/troubleshooting/font-loading-errors
- Remotion official docs — OffthreadVideo vs Video: https://www.remotion.dev/docs/video-vs-offthreadvideo
- Remotion official docs — GPU usage: https://www.remotion.dev/docs/gpu
- Remotion official docs — Encoding Guide: https://www.remotion.dev/docs/encoding
- Remotion official docs — Media Support: https://www.remotion.dev/docs/media/support
- Remotion official docs — delayRender / continueRender: https://www.remotion.dev/docs/delay-render
- Remotion official docs — Supabase integration: https://www.remotion.dev/docs/lambda/supabase
- MDN — unicode-bidi: https://developer.mozilla.org/en-US/docs/Web/CSS/unicode-bidi
- MDN — direction: https://developer.mozilla.org/en-US/docs/Web/CSS/direction
- Airtable API — Rate Limits: https://airtable.com/developers/web/api/rate-limits
- Airtable API — Upload Attachment: https://airtable.com/developers/web/api/upload-attachment
- FastAPI docs — Async / Concurrency: https://fastapi.tiangolo.com/async/
- Supabase docs — Signed URLs: https://supabase.com/docs/reference/javascript/storage-from-createsignedurl
- GitHub issue — Remotion memory leak (v2.4.3–v2.6.6): https://github.com/remotion-dev/remotion/issues/479
- GitHub issue — Remotion concurrency performance: https://github.com/remotion-dev/remotion/issues/4300
- RTL Fixer blog — CSS RTL issues: https://rtlfixer.com/your-software-doesnt-support-right-to-left-languages-like-arabic-and-hebrew-heres-the-solution-you-were-looking-for/

---
*Pitfalls research for: Remotion video rendering integration — Wandi Instagram content platform*
*Researched: 2026-03-11*
