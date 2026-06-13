# DeepVerify Frontend — Design/UX Progress Log

Autonomous polish backlog for the DeepVerify frontend (https://deepverify.site). Next.js + Tailwind + shadcn/ui, dark theme. Repo: YashChoudhary13/DeepVerify, this app lives in `frontend/`.

## Deploy note
The Vercel "frontend" project is NOT git-connected as of 2026-06-13, so a `git push` does NOT auto-deploy the frontend. The loop should: make the change, verify `npm run build` (next build) passes, commit, and push. Deployment to Vercel is manual/separate until git integration is connected (root dir = `frontend/`). Always log in the entry that the change is "pushed, awaiting Vercel deploy" so nothing is assumed live. Backend (FastAPI) changes DO auto-deploy via GitHub Actions.

## Done
- 2026-06-13 — Infra: NEXT_PUBLIC_API_URL pointed to https://api.deepverify.site; domain split (frontend on deepverify.site, API on api.deepverify.site).

## Backlog (run /design-review against https://deepverify.site to refine, then implement in priority order)
1. [ ] Run a full /design-review pass on the live site; capture first-impression + design-system extraction; record concrete findings here.
2. [ ] Landing/hero: ensure one strong visual anchor, brand-first hierarchy, clear single primary CTA (upload/analyze).
3. [ ] Upload/analyze flow: loading + progress states for inference (it can take seconds); skeleton/spinner with reassuring copy.
4. [ ] Result display: clear verdict hierarchy (real vs fake confidence), readable heatmaps, per-model breakdown legibility.
5. [ ] Empty/error states: friendly copy + next action (e.g., unsupported file, model unavailable).
6. [ ] Accessibility: WCAG AA contrast, 44px touch targets, focus-visible rings, alt text on result images.
7. [ ] Motion: tasteful entrance/scroll reveals + reduced-motion support (framer-motion if present, else CSS).
8. [ ] Performance: image lazy-loading, font-display swap, no layout shift on result render.

## Guardrails
- Frontend design/UX/a11y/perf only. Do NOT touch ML inference logic, auth, payments, DB schema, or backend infra.
- Verify `next build` before every push. One focused commit per run. Never push a broken build.
