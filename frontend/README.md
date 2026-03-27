# Wandi AI — Frontend

React frontend for Wandi AI, replacing the Lovable-hosted frontend.

## Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router v6
- Supabase Auth + Storage
- shadcn/ui (Radix UI)
- framer-motion
- sonner (toasts)
- lucide-react (icons)
- date-fns
- recharts

## Setup

```bash
cd frontend
cp .env.example .env
# Fill in VITE_SUPABASE_ANON_KEY in .env
npm install
npm run dev
```

The app runs on http://localhost:5173.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | Yes | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase anon/public key |
| `VITE_AGENT_API_URL` | Yes | wandi-agent API base URL |
| `VITE_META_APP_ID` | Yes | Meta/Facebook App ID for OAuth |

## Build

```bash
npm run build
```

Output goes to `dist/`. Serve with any static file server.

## Architecture

- `src/lib/supabase.ts` — Supabase client singleton
- `src/lib/api.ts` — wandi-agent API calls
- `src/lib/edge-functions.ts` — Supabase Edge Function calls
- `src/hooks/` — React hooks for data fetching
- `src/components/` — Reusable components
- `src/pages/` — Route page components
- `src/contexts/` — Language context (HE/EN)

## What changed vs Lovable

- Only the frontend layer — same Supabase, same agent, same Edge Functions
- No Tanstack Query — direct fetch calls
- Import paths: `@/lib/supabase` instead of `@/integrations/supabase/client`
- No `supabase.functions.invoke()` — direct `fetch()` to Edge Functions

## What didn't change

- wandi-agent (main.py, agent.py, etc.) — zero changes
- Supabase tables/policies/Edge Functions — zero changes
- Airtable, n8n, remotion-service — zero changes
