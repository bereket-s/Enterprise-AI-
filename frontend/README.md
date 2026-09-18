# Frontend — Enterprise AI Decision Intelligence Platform

Next.js 14 (App Router) + TypeScript + Tailwind CSS dashboard for the platform.

## Development

```bash
npm install
npm run dev
```

Requires the backend running at `http://localhost:8000` (see `../backend`). Override
with `NEXT_PUBLIC_API_BASE_URL` if needed (see `next.config.js`).

## Structure

```
app/
  login/, register/        Auth pages
  dashboard/
    layout.tsx              Sidebar shell — only shows enabled modules
    page.tsx                Overview + AI Copilot widget
    bi/, inventory/, fraud/, maintenance/, workforce/
    settings/                Module enable/disable toggles (org_admin only)
components/                 Shared UI primitives (Card, StatTile, RiskBadge...) + CopilotWidget
lib/
  api.ts                    Axios instance with JWT auth interceptor
  auth.tsx                  React context: current user + enabled modules
  types.ts                  Shared TypeScript interfaces
```

## Type-checking

```bash
npx tsc --noEmit
```
