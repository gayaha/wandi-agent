# Stack Research

**Domain:** Programmatic video rendering with text overlays — Node.js microservice for Instagram Reels
**Researched:** 2026-03-11
**Confidence:** HIGH (core stack verified against official Remotion docs and official npm registry)

---

## Recommended Stack

### Core Technologies — Node.js Renderer Service

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Node.js | 22 LTS (Bookworm) | Runtime for Remotion service | Official Remotion Docker base image is `node:22-bookworm-slim` since Nov 2024; do not use Alpine (causes Rust component slowdowns and Chrome downgrade failures) |
| TypeScript | 5.8.x | Language for renderer service | Official render server template ships with TS 5.8.2; type safety on composition props prevents runtime shape mismatches |
| remotion | 4.0.x (currently 4.0.434) | Core framework — React-to-video engine | The standard library; Rust-powered, built-in FFmpeg, no external FFmpeg install required since v4 |
| @remotion/renderer | 4.0.x (currently 4.0.429) | Server-side render APIs — `renderMedia()`, `selectComposition()` | The programmatic rendering API used by all SSR patterns; must match `remotion` version exactly |
| @remotion/bundler | 4.0.x (currently 4.0.341) | Webpack bundling of Remotion compositions | Bundles the React compositions for server-side execution; required for SSR; must match `remotion` version exactly |
| React | 19.0.0 | Composition components | Remotion renders React components to video; the official template now targets React 19 |
| Express | 5.1.0 | HTTP API layer | Official Remotion render server template uses Express 5; wraps `renderMedia()` with a job-tracking REST API |
| Zod | 3.22.x | Schema validation for composition props | Official template dependency; validates input payloads from Python backend before passing to renderer |

### Core Technologies — Python Backend Layer (Abstraction + Orchestration)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| httpx | 0.27.x | Async HTTP client for calling Node.js render service | Native async/await support with asyncio; preferred over `requests` for FastAPI (sync requests block the event loop); supports streaming and timeouts |
| supabase-py | 2.x (currently 2.13.x) | Download raw video from Supabase Storage | Already likely in use; `supabase.storage.from_(bucket).download()` returns bytes; use signed URLs for private buckets |
| pyairtable | 3.x | Upload rendered video back to Airtable | `pyairtable.utils.attachment(url=...)` pattern — pass a public URL and Airtable fetches and stores it; no file bytes upload needed |

### Supporting Libraries — Node.js Service

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @remotion/google-fonts | 4.0.x | Type-safe Google Fonts loading (Noto Sans Hebrew, etc.) | Use for Hebrew font loading; provides `loadFont()` that blocks render until font is ready; Noto Sans Hebrew is available via Google Fonts API |
| @remotion/fonts | 4.0.x (requires >=4.0.164) | Load local font files from `public/` directory | Use when self-hosting font files instead of loading from Google CDN; more reliable in air-gapped Docker containers |
| tsx | 4.19.x | TypeScript execution in development | Dev-only; runs the Express server in TS without a compile step; official template uses this |
| @types/express | 5.0.x | TypeScript definitions for Express | Dev-only; required when using Express with TypeScript |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Docker (node:22-bookworm-slim) | Container the Node.js renderer service | Install Chrome Headless Shell via `npx remotion browser ensure` in Dockerfile; install `fonts-noto-color-emoji` and Hebrew font packages (`fonts-noto-hebrew` or bundle font files) |
| ESLint + @remotion/eslint-config-flat | Linting with Remotion-specific rules | Official template includes this; catches common Remotion pitfalls like frame-rate-dependent code |
| npx create-video@latest --render-server | Bootstrap the render server | Official Remotion template; saves significant setup time vs building from scratch |

---

## Installation

```bash
# Bootstrap (preferred — uses official template with correct wiring)
npx create-video@latest --render-server

# Or manually install core packages (ALL must be same version)
npm install remotion @remotion/renderer @remotion/bundler react react-dom express zod

# Font support (choose one or both)
npm install @remotion/google-fonts   # Google Fonts CDN (Noto Sans Hebrew available)
npm install @remotion/fonts          # Local font file loading (>=4.0.164)

# Dev dependencies
npm install -D typescript tsx @types/express @types/react @remotion/eslint-config-flat eslint
```

```bash
# Python side — add to existing requirements
pip install httpx supabase pyairtable
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Node.js SSR with `@remotion/renderer` | Remotion Lambda (@remotion/lambda) | Use Lambda when: rendering speed is critical (parallel chunks), AWS is already in stack, and you can accept the operational overhead of Lambda + S3 deployment. For this project, a self-hosted Docker service is simpler and keeps infrastructure consolidated. |
| Remotion Lambda | Remotion Cloud Run | Cloud Run is Alpha with limited active development — avoid for production workloads. Use Lambda if going serverless. |
| Express 5 | Fastify | Fastify offers marginally better throughput, but Express 5 is what the official Remotion template uses — sticking with it reduces debugging against untested integration patterns. |
| httpx (Python) | requests | `requests` is synchronous and blocks FastAPI's event loop. `httpx` is a drop-in upgrade with native async support via `httpx.AsyncClient`. |
| @remotion/google-fonts + local font fallback | Raw CSS @font-face | `@remotion/google-fonts` provides type-safe font loading with built-in readiness signaling. Raw CSS @font-face works but requires manual load-detection to prevent rendering before fonts are ready. |
| Docker container (self-hosted) | Vercel Sandbox | Vercel Sandbox is the easiest deployment path for Vercel customers. This project already has a Python backend with existing infrastructure — adding a sidecar Docker container is more natural than adding a second cloud provider. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Alpine Linux as Docker base | Two confirmed issues: significantly slower Rust component startup times AND inability to downgrade Chrome versions when breaking changes occur. Official Remotion docs explicitly warn against it. | `node:22-bookworm-slim` (official recommendation as of Nov 2024) |
| FFmpeg-direct video composition (without Remotion) | Animated text overlays (fade in/out, enter/exit) require frame-by-frame compositing logic. FFmpeg filters are string-based, fragile, and cannot express React animations. | Remotion (which bundles FFmpeg internally and uses it as an encoder, not as a compositor) |
| Media Parser (`@remotion/media-parser`) | Deprecated as of February 2026; team is migrating to Mediabunny. Do not build new integrations against it. | Mediabunny (open-source, sponsored by Remotion team) — but for this use case you don't need a media parser at all; you're rendering, not parsing |
| Mixing `remotion`, `@remotion/renderer`, `@remotion/bundler` versions | ALL Remotion packages must be the exact same version. Version mismatches produce cryptic runtime errors. Run `npx remotion versions` to audit. | Pin all `@remotion/*` packages to the same version in package.json |
| `requests` (Python) for calling render service | Synchronous; blocks FastAPI's async event loop. Video rendering takes 10-90 seconds — a blocking call will exhaust server workers. | `httpx.AsyncClient` with `await client.post(...)` |
| Uploading video bytes directly to Airtable | Airtable's upload_attachment API expects file bytes but has strict size limits. MP4 files for 90-second Reels can be 50-200 MB. | Store rendered video in accessible storage (Supabase Storage or temporary URL), then use `pyairtable.utils.attachment(url=...)` so Airtable fetches and stores its own copy |

---

## Stack Patterns by Variant

**If rendering load is low (<10 renders/hour):**
- Run `renderMedia()` synchronously within the POST handler
- Return the rendered file URL in the response
- No job queue needed

**If rendering load is moderate to high (>10 renders/hour):**
- Use the job queue pattern from the official render server template
- POST /renders → returns job ID immediately
- GET /renders/:id → poll for completion
- Python side uses httpx with polling loop or webhook callback

**If deploying to cloud without persistent storage:**
- Render to a temp path inside the container
- Upload to Supabase Storage immediately after render
- Return Supabase signed URL; Python backend passes this to Airtable
- Clean up temp files after upload

**If deploying to cloud with persistent volume:**
- Render to mounted volume path
- Serve rendered file via Express static middleware
- Python backend constructs the URL from the known host

**For Hebrew RTL text overlays specifically:**
- Use `@remotion/google-fonts` to load Noto Sans Hebrew (available in Google Fonts)
- Apply CSS `direction: rtl` and `unicode-bidi: embed` on the text container
- Test with mixed Hebrew+English content early — bidi algorithm in Chrome handles mixing, but requires explicit `direction` CSS on parent elements
- For embedded English within Hebrew sentences, wrap English spans with `direction: ltr`

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| remotion@4.0.434 | @remotion/renderer@4.0.x, @remotion/bundler@4.0.x | ALL @remotion/* packages must be pinned to the same minor version; use `^4.0.434` and lock with package-lock.json |
| React@19 | remotion@4.0.x | Remotion 4 supports React 19; the official render server template targets React 19 |
| Express@5 | @types/express@5.0.x | Express 5 changed the Router type signatures; use @types/express@5 not @types/express@4 |
| Node.js 22 LTS | @remotion/renderer@4.0.x | Remotion requires Node 16+; Node 22 LTS is the current recommended version for Docker |
| supabase-py@2.x | Python 3.8+ | Async client available via `AsyncClient`; sync client sufficient for background tasks |

---

## Composition Configuration for Instagram Reels

Remotion composition settings to use in `remotion/Root.tsx`:

```typescript
// Standard Instagram Reels spec
export const MyComposition = () => {
  return (
    <Composition
      id="InstagramReel"
      component={ReelTemplate}
      durationInFrames={90 * 30}   // 90 seconds at 30fps = 2700 frames
      fps={30}
      width={1080}
      height={1920}                 // 9:16 vertical
      schema={reelPropsSchema}      // Zod schema for props validation
    />
  );
};
```

Safe zone for text: keep text at least 420px from bottom, 250px from top (Instagram UI overlaps these areas).

---

## Sources

- [Remotion Official Site](https://www.remotion.dev/) — Framework overview, deployment options
- [Remotion render server template (DeepWiki)](https://deepwiki.com/remotion-dev/template-render-server) — Package versions: Express 5.1.0, React 19, TypeScript 5.8.2, Zod 3.22.3, tsx 4.19.3 (HIGH confidence)
- [Remotion compare-ssr docs](https://www.remotion.dev/docs/compare-ssr) — SSR option comparison; Node.js API vs Lambda vs Cloud Run vs Vercel (HIGH confidence)
- [Remotion Docker docs](https://www.remotion.dev/docs/docker) — Base image `node:22-bookworm-slim`, system dependencies, Alpine warning (HIGH confidence)
- [Remotion render server template](https://www.remotion.dev/templates/render-server) — Official Express-based render service template (HIGH confidence)
- [remotion npm package](https://www.npmjs.com/package/remotion) — Current version 4.0.434 as of March 2026 (HIGH confidence)
- [@remotion/renderer npm](https://www.npmjs.com/package/@remotion/renderer) — Current version 4.0.429 (HIGH confidence)
- [Remotion fonts docs](https://www.remotion.dev/docs/fonts) — `loadFont()` API, `@remotion/google-fonts` usage (HIGH confidence)
- [Remotion Chrome Headless Shell docs](https://www.remotion.dev/docs/miscellaneous/chrome-headless-shell) — `enableMultiProcessOnLinux` default since v4.0.137 (HIGH confidence)
- [Instagram Reels dimensions 2026](https://zeely.ai/blog/instagram-reels-dimensions-aspect-ratio-in-2026/) — 1080x1920, 9:16, 30fps, H.264, safe zones (MEDIUM confidence — third-party source consistent with multiple sources)
- [HTTPX async docs](https://www.python-httpx.org/async/) — AsyncClient pattern for calling render service (HIGH confidence)
- [pyAirtable attachment utility](https://pyairtable.readthedocs.io/en/stable/api.html) — `attachment(url=...)` for URL-based Airtable attachments (MEDIUM confidence — verified via community confirmation)
- [supabase-py PyPI](https://pypi.org/project/supabase/) — Python Supabase client v2.13.x (HIGH confidence)
- [Remotion blog — Mediabunny transition](https://www.remotion.dev/blog) — Media Parser deprecated February 2026 (HIGH confidence)

---

*Stack research for: Remotion-based video renderer microservice — Instagram Reels with Hebrew RTL text overlays*
*Researched: 2026-03-11*
