# Frontend — whatdidimiss

Next.js 16 + React 19 frontend for AI-powered YouTube content coaching.

## Prerequisites

- Node.js 18+
- Backend API running on http://localhost:8000

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

Runs on http://localhost:3000.

## Environment Variables

Create `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_AUTH_DISABLED=false
```

Set `NEXT_PUBLIC_AUTH_DISABLED=true` to bypass Google OAuth in dev (uses a dev user from the backend).

## Build

```bash
npm run build
npm start     # serve production build
```

## Lint

```bash
npm run lint
```

## Tech Stack

- **Framework**: Next.js 16 (App Router, Turbopack)
- **UI**: Base UI (headless) + Tailwind CSS 4 + CVA
- **Data**: TanStack React Query + Axios
- **Charts**: Recharts
- **Icons**: Lucide React
- **Notifications**: Sonner

## Project Structure

```
src/
  app/
    (auth)/login/          # Login page (Google OAuth)
    (auth)/callback/       # OAuth callback handler
    (app)/videos/          # Video list page
    (app)/videos/analyze/  # Analyze (YouTube URL + upload)
    (app)/videos/browse/   # Browse channel videos
    (app)/dashboard/[videoId]/  # Video dashboard + sub-pages
  components/
    ui/                    # Shadcn-style base components
    layout/                # Sidebar, topbar
    dashboard/             # Dashboard-specific components
    videos/                # Video-specific components (status badge)
    providers/             # Auth provider (React Context)
    charts/                # Recharts wrappers
  lib/
    api/                   # Axios client, API functions, types
    hooks/                 # React Query hooks
    utils/                 # Formatting helpers
```
