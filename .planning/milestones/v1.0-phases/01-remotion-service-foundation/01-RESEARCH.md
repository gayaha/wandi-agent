# Phase 1: Remotion Service Foundation - Research

**Researched:** 2026-03-11
**Domain:** Remotion 4.x Node.js render service — Hebrew RTL text, Instagram Reels format, Docker deployment
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Text Placement**
- Hook text appears in the upper portion of the safe zone (top of the 1080x1420px visible area)
- Body text appears below the hook, within the safe zone — natural top-down reading flow
- Text uses a semi-transparent dark overlay/box behind it for readability on any video background
- Text is center-aligned by default (common in Reels, looks balanced on vertical video)

**Animation Timing & Style**
- Default animation: fade-in/fade-out with medium speed (~0.5-1s transition)
- Additional animation option: slide-up from bottom as an alternative entrance
- Exit mirrors entrance (fade in → fade out, slide up → slide down)
- Brief clean gap between text segments (0.3-0.5s pause)

**Font & Text Sizing**
- Default font: Heebo (clean, modern sans-serif, popular for Israeli marketing content)
- Font loading narrowed to `{ subsets: ['hebrew'], weights: ['400', '700'] }` (prevents delayRender timeout)
- Hook text is bold (700 weight) and larger than body text (~1.5x scale)
- Body text uses regular weight (400)

**Video Duration Handling**
- If source video is longer than text content: trim to text duration + 1-2s outro
- If source video is shorter than text content: loop the video seamlessly
- Video plays at original speed, no distortion

**RTL & Hebrew (from research — locked)**
- Use `direction: rtl` + `unicode-bidi: embed` on text containers
- NEVER use `unicode-bidi: bidi-override` (reverses Hebrew character order — silent failure)
- Hebrew + English mixed text handled by Chromium's native BiDi algorithm
- Pre-download Supabase source video to local disk before `renderMedia()` (signed URLs expire mid-render)

**Docker & Infrastructure (from research — locked)**
- Base image: `node:22-bookworm-slim` (Debian, not Alpine — 35% faster renders)
- Official Remotion render server template as scaffold
- Express 5 + TypeScript + React 19 + Zod for schema validation
- Async job pattern: POST returns 202 + job ID, GET polls for status/result

### Claude's Discretion
- Exact pixel values for text positioning within safe zone
- Semi-transparent overlay opacity level
- Exact animation easing curves (spring constants, interpolation ranges)
- Video loop crossfade duration
- Error response format and HTTP status codes
- Docker multi-stage build optimization
- Remotion composition structure (component hierarchy)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REND-01 | Renderer produces 1080x1920 vertical MP4 with H.264 video, AAC audio at 30fps — Instagram Reels spec | Remotion `<Composition>` with `width=1080, height=1920, fps=30` + `renderMedia({ codec: 'h264' })`. Codec table in Architecture Patterns section. |
| REND-02 | User can see generated text content overlaid on raw video footage in the rendered output | `<AbsoluteFill>` + `<OffthreadVideo>` + positioned text `<div>` inside Remotion composition. Code Examples section. |
| REND-03 | Text overlays are positioned within the Instagram safe zone (avoiding top ~250px and bottom ~250px UI overlap) | Safe zone is 1080x1420px band at y=250 to y=1670. Absolute pixel positioning enforced in ReelTemplate.tsx. Architecture Patterns section. |
| REND-04 | Text elements animate on entry and exit (fade-in/out at minimum, slide and spring as options) | Remotion `interpolate()` for opacity fade, `spring()` for slide motion. Both are frame-based and work in headless. Code Examples section. |
| HEBR-01 | Hebrew text renders right-to-left correctly in video output | CSS `direction: rtl` + `unicode-bidi: embed` on text container. Never `bidi-override`. Common Pitfalls section. |
| HEBR-02 | Mixed Hebrew + English text in the same element renders with correct bidirectional ordering | Chromium's native BiDi algorithm handles it when `dir="rtl"` is set on the parent. Wrap English sub-spans in `dir="ltr"`. Code Examples section. |
| HEBR-03 | Renderer loads a Hebrew-capable font (Heebo or Assistant) that covers Latin + Hebrew Unicode blocks | `@remotion/google-fonts/Heebo` with `loadFont("normal", { weights: ['400', '700'], subsets: ['hebrew'] })`. Standard Stack section. |
</phase_requirements>

---

## Summary

Phase 1 delivers a standalone Node.js Docker service that accepts render jobs via HTTP POST, renders a 1080x1920 MP4 with Hebrew RTL text overlaid on a Supabase source video, and makes the result accessible via GET. The official Remotion render server template (`npx create-video@latest --render-server`) provides a fully wired Express 5 + job queue + TypeScript baseline — do not build the HTTP layer from scratch. The phase is self-contained: no Python integration, no brand templates, no multi-segment text. Its sole purpose is to prove the full rendering stack works correctly before anything else is built on top of it.

The three highest risks are all silent: (1) Hebrew RTL text can render with reversed character order if `unicode-bidi: bidi-override` is applied anywhere in the CSS stack; (2) the Heebo font can silently fall back to a system font if `loadFont()` is not called before render starts; (3) source video download from Supabase can time out mid-render if passed as a signed URL directly to `OffthreadVideo`. All three must be caught and verified in Phase 1's smoke test before any downstream work begins. "It renders" is not the same as "it renders correctly."

Prior project-level research is extensive and HIGH confidence. This document synthesizes and phase-scopes that research rather than duplicating it. Key update from live template inspection: the official render server template now uses **Zod 4.3.6** (not Zod 3.22.x as earlier research noted) and **React 19.2.3** and **TypeScript 5.9.3** — use the live template versions, not the earlier estimates.

**Primary recommendation:** Bootstrap with `npx create-video@latest --render-server`, then add the `ReelTemplate.tsx` composition, Heebo font loading, RTL CSS, and the video pre-download step. Run a smoke-test render of Hebrew + English mixed text on a real Supabase video before declaring this phase done.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `remotion` | ^4.0.0 (4.0.434+) | Core React-to-video framework | Official Remotion package; Rust-powered renderer, built-in FFmpeg, no external install required |
| `@remotion/renderer` | ^4.0.0 | SSR APIs: `renderMedia()`, `selectComposition()`, `bundle()` | Required for all server-side rendering; must match `remotion` version exactly |
| `@remotion/bundler` | ^4.0.0 | Webpack bundling of React compositions | Required for SSR to produce executable composition bundle |
| `@remotion/zod-types` | ^4.0.0 | Remotion-specific Zod types for composition props | Used by official template for prop validation |
| `express` | 5.1.0 | HTTP API layer for render jobs | Official template choice; wraps `renderMedia()` with job-tracking REST endpoints |
| `react` | 19.2.3 | Composition components | Remotion renders React components; official template targets React 19 |
| `react-dom` | 19.2.3 | React DOM rendering | Required alongside react |
| `zod` | 4.3.6 | Input props schema validation | Current version in official template (note: Zod 4.x, not 3.x) |
| `@remotion/google-fonts` | ^4.0.0 | Hebrew font loading (Heebo) | Provides `loadFont()` with type-safe subset/weight selection; blocks render until font is ready |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tsx` | 4.19.3 | TypeScript execution in dev (no compile step) | Dev server; used by official template for `npm run dev` |
| `@types/express` | 5.0.1 | TypeScript definitions for Express 5 | Required — Express 5 changed Router type signatures; use v5 not v4 |
| `@types/react` | 19.2.7 | TypeScript definitions for React 19 | Dev dependency |
| `@remotion/eslint-config-flat` | ^4.0.0 | Remotion-specific ESLint rules | Catches frame-rate-dependent code and other Remotion anti-patterns |
| `typescript` | 5.9.3 | TypeScript compiler | Official template version; used for production build |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@remotion/google-fonts/Heebo` | Self-hosted font files via `@remotion/fonts` | Self-hosted is more reliable in air-gapped Docker (no Google CDN dependency), but requires bundling the .woff2 file in `public/`. Use self-hosting if the deployment environment has restricted outbound HTTP. |
| `node:22-bookworm-slim` Docker base | `node:22-alpine` | Alpine uses musl libc, which causes 35% slower renders (Rust component slowdown) and prevents Chrome version pinning. Alpine is NOT a valid choice here. |
| Express 5 | Fastify | Marginally better throughput, but not what the official template uses — adds untested integration surface. Stick with Express 5. |
| `renderMedia()` with job queue | Synchronous render-and-return | Synchronous times out at 30-300 seconds. Job queue is mandatory. |

**Installation:**

```bash
# Bootstrap from official template (preferred)
npx create-video@latest --render-server
# Choose: TypeScript, then add Heebo font package
npm install @remotion/google-fonts
```

---

## Architecture Patterns

### Recommended Project Structure

```
remotion-service/               # Standalone Node.js service (separate Docker container)
├── remotion/                   # Composition layer — what the video looks like
│   ├── index.ts                # Root: registers all <Composition> entries
│   ├── ReelTemplate.tsx        # Primary Instagram Reel composition
│   ├── TextOverlay.tsx         # RTL-aware text overlay subcomponent
│   └── schemas.ts              # Zod schemas for inputProps validation
├── server/                     # HTTP layer — how renders are managed
│   ├── index.ts                # Express server entrypoint, port 3000
│   └── render-queue.ts         # makeRenderQueue() — job state Map + serial Promise chain
├── public/                     # Static assets (font files if self-hosting)
├── Dockerfile                  # node:22-bookworm-slim, system deps, browser ensure
├── remotion.config.ts          # Remotion webpack config
├── package.json
└── tsconfig.json
```

The composition layer (`remotion/`) is fully separated from the server layer (`server/`). Changes to the template design never require server changes. Changes to HTTP API behavior never require touching composition code.

### Pattern 1: Async Job Queue (HTTP 202 + Polling)

**What:** POST /renders enqueues a job and returns `{ jobId }` immediately with HTTP 202. GET /renders/:id returns job state. The render queue serializes jobs to prevent Chromium resource contention.

**When to use:** Always. This is non-negotiable — renders take 15-120+ seconds.

**Example:**

```typescript
// server/index.ts
import express from "express";
import { makeRenderQueue } from "./render-queue";

const app = express();
const queue = makeRenderQueue();

app.post("/renders", express.json(), (req, res) => {
  const jobId = crypto.randomUUID();
  queue.enqueue(jobId, req.body);        // non-blocking — returns immediately
  res.status(202).json({ jobId });       // HTTP 202 Accepted
});

app.get("/renders/:id", (req, res) => {
  const job = queue.getJob(req.params.id);
  if (!job) return res.status(404).json({ error: "Job not found" });
  res.json(job);                         // { state, progress, videoUrl? }
});
```

```typescript
// server/render-queue.ts — serial queue prevents concurrent render OOM
type JobState = {
  state: "queued" | "in-progress" | "completed" | "failed";
  progress: number;
  videoUrl?: string;
  error?: string;
};

export function makeRenderQueue() {
  const jobs = new Map<string, JobState>();
  let queue: Promise<void> = Promise.resolve();

  function enqueue(jobId: string, inputProps: unknown) {
    jobs.set(jobId, { state: "queued", progress: 0 });
    queue = queue.then(() => runRender(jobId, inputProps));
  }

  async function runRender(jobId: string, inputProps: unknown) {
    jobs.set(jobId, { state: "in-progress", progress: 0 });
    // ... renderMedia() call, update progress, set completed/failed
  }

  return { enqueue, getJob: (id: string) => jobs.get(id) };
}
```

### Pattern 2: Remotion Composition with inputProps

**What:** All per-render customization (text, source video URL, font, colors) is passed as JSON `inputProps`. The React composition is a pure rendering function of those props. The Zod schema validates all inputs at the HTTP layer, not inside the component.

**When to use:** Always in Remotion — composition registered once at startup, parameterized at render time.

**Example:**

```typescript
// remotion/schemas.ts
import { z } from "zod";

export const ReelInputSchema = z.object({
  sourceVideoLocalPath: z.string(),     // Local path after pre-download from Supabase
  hookText: z.string(),                 // Hebrew headline (bold, larger)
  bodyText: z.string(),                 // Hebrew body content (regular weight)
  textDirection: z.enum(["rtl", "ltr"]).default("rtl"),
  animationStyle: z.enum(["fade", "slide"]).default("fade"),
});

export type ReelInput = z.infer<typeof ReelInputSchema>;
```

```typescript
// remotion/index.ts
import { Composition } from "remotion";
import { ReelTemplate } from "./ReelTemplate";
import { ReelInputSchema } from "./schemas";

export const RemotionRoot = () => (
  <Composition
    id="ReelTemplate"
    component={ReelTemplate}
    durationInFrames={90 * 30}   // 90 seconds at 30fps = 2700 frames
    fps={30}
    width={1080}
    height={1920}
    schema={ReelInputSchema}
    defaultProps={{
      sourceVideoLocalPath: "/tmp/sample.mp4",
      hookText: "שלום עולם",
      bodyText: "גוף הטקסט כאן",
      textDirection: "rtl",
      animationStyle: "fade",
    }}
  />
);
```

### Pattern 3: renderMedia() Call

**What:** The server calls `renderMedia()` with the bundled composition, input props, output path, and codec settings.

```typescript
// server/render-queue.ts — inside runRender()
import { bundle } from "@remotion/bundler";
import { selectComposition, renderMedia } from "@remotion/renderer";
import path from "path";

const compositionBundlePath = await bundle({
  entryPoint: path.join(process.cwd(), "remotion/index.ts"),
  webpackOverride: (config) => config,
});

const composition = await selectComposition({
  serveUrl: compositionBundlePath,
  id: "ReelTemplate",
  inputProps,
});

await renderMedia({
  composition,
  serveUrl: compositionBundlePath,
  codec: "h264",           // H.264 video — Instagram Reels spec
  // audioCodec defaults to "aac" for h264 — matches REND-01
  outputLocation: `/tmp/renders/${jobId}.mp4`,
  inputProps,
  onProgress: ({ progress }) => {
    jobs.set(jobId, { state: "in-progress", progress });
  },
  concurrency: 1,          // Single thread — headless server, no GPU
});
```

**Important:** Bundle once at startup and reuse the bundle path. Do NOT re-bundle on every render — it takes 15-30 seconds and defeats the queue performance model.

### Pattern 4: Hebrew RTL Text Overlay

**What:** The safe zone is enforced at the composition level, not per-render. RTL CSS is applied consistently to all text containers.

```typescript
// remotion/ReelTemplate.tsx
import { AbsoluteFill, OffthreadVideo, useCurrentFrame } from "remotion";
import { TextOverlay } from "./TextOverlay";
import type { ReelInput } from "./schemas";

// Safe zone constants — Instagram UI covers top 250px and bottom 250px
const SAFE_ZONE_TOP = 250;
const SAFE_ZONE_BOTTOM = 250;
const SAFE_ZONE_HEIGHT = 1920 - SAFE_ZONE_TOP - SAFE_ZONE_BOTTOM; // 1420px

export const ReelTemplate = ({
  sourceVideoLocalPath,
  hookText,
  bodyText,
  animationStyle,
}: ReelInput) => {
  return (
    <AbsoluteFill>
      {/* Source video fills the full frame */}
      <OffthreadVideo
        src={sourceVideoLocalPath}   // local file path (not Supabase URL)
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
      {/* Text overlay within safe zone */}
      <AbsoluteFill
        style={{
          top: SAFE_ZONE_TOP,
          height: SAFE_ZONE_HEIGHT,
          position: "absolute",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "40px 60px",
        }}
      >
        <TextOverlay
          hookText={hookText}
          bodyText={bodyText}
          animationStyle={animationStyle}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

```typescript
// remotion/TextOverlay.tsx
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";

const FADE_IN_FRAMES = 15;   // 0.5s at 30fps
const FADE_OUT_FRAMES = 15;

export const TextOverlay = ({ hookText, bodyText, animationStyle }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const opacity = interpolate(
    frame,
    [0, FADE_IN_FRAMES, durationInFrames - FADE_OUT_FRAMES, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const textContainerStyle = {
    direction: "rtl" as const,          // RTL for Hebrew
    unicodeBidi: "embed" as const,      // NEVER use bidi-override
    textAlign: "center" as const,
    width: "100%",
  };

  const overlayBoxStyle = {
    backgroundColor: "rgba(0, 0, 0, 0.55)",
    borderRadius: 16,
    padding: "24px 32px",
    opacity,
  };

  return (
    <div style={overlayBoxStyle}>
      {/* Hook text: bold, larger */}
      <div style={{ ...textContainerStyle, fontSize: 52, fontWeight: 700, marginBottom: 16 }}>
        {hookText}
      </div>
      {/* Body text: regular weight */}
      <div style={{ ...textContainerStyle, fontSize: 36, fontWeight: 400 }}>
        {bodyText}
      </div>
    </div>
  );
};
```

### Pattern 5: Heebo Font Loading

**What:** Load Heebo at the module top level — outside any React component — so it blocks render start via Remotion's `delayRender`/`continueRender` mechanism.

```typescript
// remotion/index.ts (or a shared fonts.ts module)
import { loadFont } from "@remotion/google-fonts/Heebo";

// Called at module load time — Remotion automatically delays render
// until the returned Promise resolves
const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],      // Only weights used in the composition
  subsets: ["hebrew"],          // Only the Hebrew subset — prevents delayRender timeout
});

export { fontFamily };          // Pass to component via inputProps or context
```

Apply in the TextOverlay component:

```typescript
import { fontFamily } from "../fonts";

const textStyle = {
  fontFamily,                  // "Heebo" — guaranteed loaded at render time
  direction: "rtl" as const,
  unicodeBidi: "embed" as const,
};
```

### Pattern 6: Video Pre-Download from Supabase

**What:** Download the source video to local disk on the Node.js service before calling `renderMedia()`. Pass the local file path to `OffthreadVideo`, not the Supabase URL.

**Why:** Supabase signed URLs expire (often in 60 seconds by default). A 90-second source video can take longer than that to download, causing a mid-render 403 failure. Local disk eliminates this race condition entirely.

```typescript
// server/render-queue.ts — inside runRender()
import fs from "node:fs";
import https from "node:https";
import path from "node:path";

async function downloadVideo(url: string, destPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(destPath);
    https.get(url, (response) => {
      response.pipe(file);
      file.on("finish", () => { file.close(); resolve(); });
    }).on("error", reject);
  });
}

// In runRender(), before calling renderMedia():
const videoLocalPath = path.join("/tmp", `${jobId}-source.mp4`);
await downloadVideo(inputProps.sourceVideoUrl, videoLocalPath);

// Pass local path to renderMedia inputProps
const localInputProps = { ...inputProps, sourceVideoLocalPath: videoLocalPath };

// After renderMedia() completes, clean up temp source file
fs.unlink(videoLocalPath, () => {});
```

### Pattern 7: Dockerfile for Remotion Service

```dockerfile
FROM node:22-bookworm-slim

# Install Chrome Headless Shell system dependencies (Debian packages)
RUN apt-get update && apt-get install -y \
  libnss3 \
  libdbus-1-3 \
  libatk1.0-0 \
  libgbm-dev \
  libasound2 \
  libxrandr2 \
  libxkbcommon-dev \
  libxfixes3 \
  libxcomposite1 \
  libxdamage1 \
  libatk-bridge2.0-0 \
  libpango-1.0-0 \
  libcairo2 \
  libcups2 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# Install Chrome Headless Shell for Remotion rendering
RUN npx remotion browser ensure

COPY . .

EXPOSE 3000
CMD ["npx", "tsx", "server/index.ts"]
```

### Anti-Patterns to Avoid

- **`unicode-bidi: bidi-override` on Hebrew containers:** Reverses character order silently. Text renders but is completely unreadable. Use `embed` or `isolate`.
- **`loadFont()` inside a React component:** Called per-render, not at module load time — font readiness signaling breaks. Must be at module top level.
- **Passing Supabase signed URLs to `OffthreadVideo` directly:** URL expires mid-render for any video over 60 seconds. Always pre-download.
- **Re-bundling on every render:** `bundle()` takes 15-30 seconds. Call it once at service startup and reuse the bundle path.
- **Alpine Linux base image:** musl libc incompatibilities cause 35% render slowdowns and Chrome version pinning failures. Use `node:22-bookworm-slim`.
- **Synchronous HTTP response from POST /renders:** Holds connection open until render completes (15-300s). Times out at nginx/load-balancer layer. Always return 202 immediately.
- **Mixing `remotion` package versions:** ALL `@remotion/*` packages must be the same version. Version mismatches produce cryptic runtime errors. Run `npx remotion versions` to audit.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP render server with job queue | Custom Express boilerplate | `npx create-video@latest --render-server` | Official template already has serial queue, job state machine, cancellation, Express 5 wiring, TypeScript config — tested against the actual Remotion API |
| Hebrew font delivery | Manual CSS `@font-face` + load detection | `@remotion/google-fonts/Heebo` | Built-in `delayRender`/`continueRender` integration; type-safe subset/weight selection; no manual readiness polling |
| Frame-accurate opacity animation | CSS transitions | Remotion `interpolate()` | CSS transitions are time-based; Remotion renders frame-by-frame and needs frame-based values. CSS will not animate correctly in SSR renders. |
| Spring physics animation | Manual spring equations | Remotion `spring()` | Remotion's spring() is frame-aware and integrates with the render pipeline; custom math produces different behavior than preview |
| Video format validation | Manual codec/resolution checks | Remotion's codec parameter + composition dimensions | Setting `codec: 'h264'`, `width: 1080`, `height: 1920`, `fps: 30` in `renderMedia()` and `<Composition>` guarantees spec compliance |
| Job ID tracking | Redis or external queue | `Map<string, JobState>` in-process | At Phase 1 scale (1-10 renders/hour) an in-process Map is sufficient; no infrastructure overhead |

**Key insight:** Remotion is already a complete rendering pipeline. The job is to configure and compose it correctly, not to re-implement what it provides. The most dangerous mistake is building custom solutions for problems Remotion already solves (font loading, frame animation, codec output).

---

## Common Pitfalls

### Pitfall 1: Hebrew Character Reversal from `unicode-bidi: bidi-override`

**What goes wrong:** Hebrew text renders with individual characters reversed within each word — visually unreadable. The render completes without error. No warnings in logs.

**Why it happens:** CSS resets or normalize stylesheets sometimes apply `unicode-bidi: bidi-override` globally. With `direction: ltr` as default, this forces Hebrew letters into LTR order, reversing them.

**How to avoid:** Always use `direction: rtl` + `unicode-bidi: embed` (not `bidi-override`) on Hebrew text containers. Never add any CSS reset or normalize library without auditing its bidi behavior first.

**Warning signs:** Letters within words appear reversed but word order is correct. Issue only visible in rendered MP4, may not appear in Studio preview.

### Pitfall 2: Font Silent Fallback to System Font

**What goes wrong:** Rendered video uses Times New Roman or generic sans-serif instead of Heebo. All Hebrew glyphs may render as empty boxes if system font lacks Hebrew Unicode block (U+0590–U+05FF).

**Why it happens:** `loadFont()` called inside a component (per-render) instead of at module top level. Or font download timed out because all weights/subsets were requested.

**How to avoid:** Call `loadFont()` at module top level (outside any function or component) with `{ weights: ['400', '700'], subsets: ['hebrew'] }`. This narrows the download to ~2 font files rather than 20+, preventing `delayRender` timeout.

**Warning signs:** Render takes 30+ seconds for a simple composition. `delayRender() was called but not cleared after 28000ms` error. Text appears in wrong font family when opening the MP4 in a video player.

### Pitfall 3: OffthreadVideo Timeout on Supabase Source Video

**What goes wrong:** Render hangs or fails mid-way for videos over 30 seconds. Intermittent failures that correlate with video length.

**Why it happens:** `OffthreadVideo` must download the entire source video before extracting the first frame. Supabase signed URLs have default 60-second expiry. A 90-second raw video at 1080p can be 200MB-1GB, taking longer than 60 seconds to download.

**How to avoid:** Pre-download the video to the Node.js service's `/tmp/` directory before calling `renderMedia()`. Pass the local file path (or `staticFile()` reference) to `OffthreadVideo`, not the Supabase URL.

**Warning signs:** Renders succeed for 5-second test clips but fail for real source videos. Error logs show `delayRender() was called but not cleared` attributed to video loading.

### Pitfall 4: Bundle Regenerated on Every Render

**What goes wrong:** Each render takes 45-75 seconds even for short videos. Service throughput collapses under any load.

**Why it happens:** `bundle()` is called inside the `renderMedia()` call or inside the request handler, creating a fresh webpack bundle on every render. Bundling takes 15-30 seconds.

**How to avoid:** Call `bundle()` once at service startup (before Express listens on the port). Store the bundle path and reuse it for all subsequent `renderMedia()` calls. Only re-bundle when composition code changes (i.e., on service restart).

**Warning signs:** All renders take roughly the same extra 15-30 seconds even for 3-second compositions. First render and tenth render have identical total times.

### Pitfall 5: CSS Animations That Work in Studio but Not in Render

**What goes wrong:** Fade and slide animations visible in Remotion Studio preview are absent or incorrect in the rendered MP4.

**Why it happens:** CSS transitions and keyframe animations are time-based, not frame-based. Remotion renders frame-by-frame; it does not "play" the animation — it snapshot-renders each frame independently. A CSS transition will show the same value for every frame.

**How to avoid:** Use only Remotion's `interpolate()` and `spring()` for all animations. These are frame-based: they take `useCurrentFrame()` as input and return the animated value for that exact frame.

**Warning signs:** Animation looks correct in Studio but the MP4 shows elements stuck at their initial or final state. Fade-in is missing; text just appears at full opacity from frame 1.

---

## Code Examples

### Composition Registration (remotion/index.ts)

```typescript
// Source: https://www.remotion.dev/docs/composition
import { Composition } from "remotion";
import { ReelTemplate } from "./ReelTemplate";
import { ReelInputSchema } from "./schemas";

export const RemotionRoot = () => (
  <Composition
    id="ReelTemplate"
    component={ReelTemplate}
    durationInFrames={90 * 30}  // 90 seconds max; actual duration from inputProps
    fps={30}
    width={1080}
    height={1920}
    schema={ReelInputSchema}
    defaultProps={{
      sourceVideoLocalPath: "",
      hookText: "טקסט לדוגמה",
      bodyText: "גוף הטקסט",
      textDirection: "rtl",
      animationStyle: "fade",
    }}
  />
);
```

### renderMedia() Call with H.264/AAC

```typescript
// Source: https://www.remotion.dev/docs/renderer/render-media
import { renderMedia } from "@remotion/renderer";

await renderMedia({
  composition,
  serveUrl: bundlePath,
  codec: "h264",           // H.264 video codec — Instagram Reels spec
  // audioCodec: "aac" is the default for h264 — do not need to set
  outputLocation: `/tmp/renders/${jobId}.mp4`,
  inputProps,
  concurrency: 1,          // Safe for single-core headless server
  onProgress: ({ progress }) => {
    jobs.set(jobId, { state: "in-progress", progress });
  },
});
```

### interpolate() for Fade Animation

```typescript
// Source: https://www.remotion.dev/docs/animating-properties
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";

const frame = useCurrentFrame();
const { durationInFrames } = useVideoConfig();

const FADE_FRAMES = 15; // 0.5s at 30fps

const opacity = interpolate(
  frame,
  [0, FADE_FRAMES, durationInFrames - FADE_FRAMES, durationInFrames],
  [0, 1, 1, 0],
  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
);
```

### spring() for Slide-Up Entrance

```typescript
// Source: https://www.remotion.dev/docs/spring
import { useCurrentFrame, useVideoConfig, spring } from "remotion";

const frame = useCurrentFrame();
const { fps } = useVideoConfig();

const slideY = spring({
  frame,
  fps,
  from: 80,               // Start 80px below final position
  to: 0,
  config: { damping: 14, stiffness: 120, mass: 1 },
});

// Apply: style={{ transform: `translateY(${slideY}px)` }}
```

### Mixed Hebrew + English BiDi

```typescript
// Correct pattern: outer RTL container, inline LTR spans for English
// Source: https://developer.mozilla.org/en-US/docs/Web/CSS/unicode-bidi

const style = {
  direction: "rtl" as const,
  unicodeBidi: "embed" as const,  // NOT bidi-override
};

// In JSX:
<div style={style}>
  {/* Pure Hebrew: BiDi algorithm handles correctly */}
  אנחנו עובדים עם{" "}
  {/* Inline English within Hebrew: explicitly LTR */}
  <span dir="ltr">React</span>
  {" "}ו-{" "}
  <span dir="ltr">TypeScript</span>
</div>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@remotion/media-parser` for video info | Mediabunny (open-source, Remotion-sponsored) | February 2026 | Do not build new integrations against `@remotion/media-parser` — it is deprecated. For Phase 1, you do not need a media parser at all (rendering only, not parsing). |
| Zod 3.x for prop validation | Zod 4.x (official template now uses 4.3.6) | 2025-2026 | Official render server template uses Zod 4 — align with it. Zod 4 has breaking API changes from Zod 3; do not mix versions. |
| Alpine Linux Docker base | `node:22-bookworm-slim` | November 2024 | Remotion officially switched Docker recommendations away from Alpine due to musl libc issues. |
| `<Video>` for source video | `<OffthreadVideo>` | Remotion 4.x | `OffthreadVideo` uses Rust + FFmpeg for frame extraction — frame-accurate, more codec support. Always use `OffthreadVideo` for source video in SSR renders. |

**Deprecated/outdated:**
- `@remotion/media-parser`: Deprecated February 2026. Replaced by Mediabunny. Not needed for Phase 1.
- Zod 3.x schemas: The official template now uses Zod 4. If bootstrapping from the template, Zod 4 is already installed.

---

## Open Questions

1. **Supabase bucket access policy for source videos**
   - What we know: The CONTEXT.md notes this as unresolved — public vs signed URL strategy
   - What's unclear: Whether raw source videos are in a public Supabase bucket (simplest — no signed URL needed) or a private bucket (requires signed URL generation with sufficient expiry)
   - Recommendation: If raw source videos are in a public bucket, the pre-download step is still recommended for reliability, but URL expiry is not a concern. Confirm bucket policy before Plan 01-02 is implemented. The code structure is the same either way (pre-download is the right pattern regardless).

2. **Heebo font availability via `@remotion/google-fonts`**
   - What we know: `@remotion/google-fonts` exposes Google Fonts at type-safe import paths; Noto Sans Hebrew is confirmed available; Heebo is on Google Fonts
   - What's unclear: Whether Heebo specifically is in the `@remotion/google-fonts` package's supported font list (the package lists available fonts)
   - Recommendation: Verify `import { loadFont } from "@remotion/google-fonts/Heebo"` resolves at install time. If it does not exist in the package, fall back to self-hosting the Heebo .woff2 file from Google Fonts CDN in the `public/` directory using `@remotion/fonts`.

3. **Video duration calculation for dynamic composition length**
   - What we know: The `<Composition>` requires `durationInFrames` at registration time; it's a fixed number
   - What's unclear: How to set the composition duration dynamically to match the actual source video length
   - Recommendation: For Phase 1, hardcode `durationInFrames={90 * 30}` (90-second maximum). The composition will render up to that many frames; `<OffthreadVideo>` will stop at the natural video end. Per-render duration control via `calculateMetadata` is a Phase 3+ concern.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None currently installed — Wave 0 must create Node.js test infrastructure for the new `remotion-service/` |
| Config file | `remotion-service/package.json` — add `"test"` script pointing to vitest or jest |
| Quick run command | `cd remotion-service && npm test -- --testNamePattern "smoke"` |
| Full suite command | `cd remotion-service && npm test` |

**Recommended Node.js test setup for `remotion-service/`:**

```bash
npm install -D vitest
```

Add to `package.json`:
```json
{
  "scripts": {
    "test": "vitest run"
  }
}
```

Note: The existing Python codebase has no test infrastructure either (confirmed by codebase analysis). Phase 1 introduces the first test files in the project, on the Node.js side only.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REND-01 | Rendered file is 1080x1920, H.264 video, AAC audio, 30fps | integration (smoke render) | `npm test -- --testNamePattern "REND-01"` | ❌ Wave 0 |
| REND-02 | Text content appears visibly in rendered output | manual (visual inspection of MP4) | visual only — open MP4 in player | ❌ Wave 0 |
| REND-03 | Text does not appear in top 250px or bottom 250px zones | unit (CSS position constants) + manual | `npm test -- --testNamePattern "REND-03"` | ❌ Wave 0 |
| REND-04 | Opacity at frame 0 is 0.0 and at frame 15 is 1.0 (fade-in) | unit (interpolate() output) | `npm test -- --testNamePattern "REND-04"` | ❌ Wave 0 |
| HEBR-01 | Hebrew text container has `direction: rtl` and `unicodeBidi: embed` in rendered DOM | unit (component style props) | `npm test -- --testNamePattern "HEBR-01"` | ❌ Wave 0 |
| HEBR-02 | Mixed Hebrew+English sentence has correct word order in rendered MP4 | manual (visual inspection of MP4 output) | visual only — inspect actual MP4 | ❌ Wave 0 |
| HEBR-03 | `loadFont()` returns `fontFamily: "Heebo"` (not system fallback) | unit (font module import) | `npm test -- --testNamePattern "HEBR-03"` | ❌ Wave 0 |

**REND-02 and HEBR-02 are manual-only.** Automated tests cannot verify pixel-level text appearance or bidi character order in a rendered video frame without frame-diffing infrastructure (out of scope for Phase 1). These MUST be verified by opening the actual MP4 output file in a video player and confirming visually.

### Sampling Rate

- **Per task commit:** `cd remotion-service && npm test -- --testNamePattern "unit"` (unit tests only, < 5 seconds)
- **Per wave merge:** `cd remotion-service && npm test` (full suite including smoke render, ~60-90 seconds for one render)
- **Phase gate:** Full suite green + visual MP4 inspection of REND-02 and HEBR-02 before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `remotion-service/vitest.config.ts` — vitest configuration
- [ ] `remotion-service/src/__tests__/safe-zone.test.ts` — covers REND-03 (pixel position constants)
- [ ] `remotion-service/src/__tests__/animation.test.ts` — covers REND-04 (interpolate() output at key frames)
- [ ] `remotion-service/src/__tests__/rtl-styles.test.ts` — covers HEBR-01 (direction/unicodeBidi props)
- [ ] `remotion-service/src/__tests__/font-loading.test.ts` — covers HEBR-03 (loadFont returns Heebo)
- [ ] `remotion-service/src/__tests__/smoke-render.test.ts` — covers REND-01 (actual MP4 output format check via file inspection)
- [ ] Framework install: `npm install -D vitest` inside `remotion-service/`

---

## Sources

### Primary (HIGH confidence)

- Official Remotion render server template package.json (live, fetched 2026-03-11): Express 5.1.0, React 19.2.3, Zod 4.3.6, TypeScript 5.9.3, tsx 4.19.3
- [Remotion Docker docs](https://www.remotion.dev/docs/docker) — `node:22-bookworm-slim`, system dependency list, `npx remotion browser ensure`
- [Remotion renderMedia() API](https://www.remotion.dev/docs/renderer/render-media) — codec, concurrency, outputLocation, onProgress parameters
- [Remotion Fonts docs](https://www.remotion.dev/docs/fonts) — `@remotion/google-fonts` `loadFont()` pattern with subset/weight selection
- [Remotion interpolate() docs](https://www.remotion.dev/docs/animating-properties) — frame-based animation API
- [Remotion spring() docs](https://www.remotion.dev/docs/spring) — physics-based animation
- [MDN unicode-bidi](https://developer.mozilla.org/en-US/docs/Web/CSS/unicode-bidi) — `embed` vs `bidi-override` behavior
- [MDN direction](https://developer.mozilla.org/en-US/docs/Web/CSS/direction) — RTL CSS

### Secondary (MEDIUM confidence)

- Prior project-level STACK.md research (2026-03-11) — comprehensive stack verification against official Remotion docs
- Prior project-level ARCHITECTURE.md research (2026-03-11) — system architecture and data flow patterns
- Prior project-level PITFALLS.md research (2026-03-11) — pitfalls verified against official Remotion docs and GitHub issues
- Prior project-level FEATURES.md research (2026-03-11) — feature landscape and MVP definition
- [Instagram Reels format spec 2026](https://zeely.ai/blog/instagram-reels-dimensions-aspect-ratio-in-2026/) — 1080x1920, H.264, AAC, 30fps, safe zones (consistent across multiple sources)

### Tertiary (LOW confidence)

- None for Phase 1 — all critical claims are verified against official sources or prior HIGH-confidence research.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — live template package.json fetched; all versions verified
- Architecture: HIGH — official Remotion template is the canonical source; patterns confirmed against SSR docs
- Pitfalls: HIGH (Remotion-specific, from official docs) / MEDIUM (RTL in video context, community-corroborated)
- Validation architecture: MEDIUM — test patterns are standard Node.js/vitest; exact test file contents are Wave 0 work, not research

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable Remotion 4.x ecosystem; Zod 4 just released so watch for minor breaking changes)
