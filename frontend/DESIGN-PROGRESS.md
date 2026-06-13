# DeepVerify Frontend — Design/UX Progress Log

Autonomous polish backlog for the DeepVerify frontend (https://deepverify.site). Next.js + Tailwind + shadcn/ui, dark theme. Repo: YashChoudhary13/DeepVerify, this app lives in `frontend/`.

## Deploy note
The Vercel "frontend" project is NOT git-connected as of 2026-06-13, so a `git push` does NOT auto-deploy the frontend. The loop should: make the change, verify `npm run build` (next build) passes, commit, and push. Deployment to Vercel is manual/separate until git integration is connected (root dir = `frontend/`). Always log in the entry that the change is "pushed, awaiting Vercel deploy" so nothing is assumed live. Backend (FastAPI) changes DO auto-deploy via GitHub Actions.

## Done
- 2026-06-13 — Infra: NEXT_PUBLIC_API_URL pointed to https://api.deepverify.site; domain split (frontend on deepverify.site, API on api.deepverify.site).
- **2026-06-13** — Typography fix: load Inter via `next/font` + wire to Tailwind `font-sans` (commit `e82f6e9`, `next build` green, pushed — **awaiting Vercel deploy**).
  - Root cause: `globals.css` declared `--font-sans: Inter` but nothing consumed it and no font was ever loaded, so the whole site (incl. the 60px hero) rendered in the OS system stack — the classic AI-slop "gave up on typography" signal.
  - Fix: `Inter({ subsets:["latin"], display:"swap", variable:"--font-inter" })`, `fontFamily.sans = ["var(--font-inter)", ...defaults]`, variable lifted to `:root` so portaled Radix content inherits it. Self-hosted, zero CLS.
  - Verified: 7 Inter woff2 emitted, computed `body`/`h1` font-family now `__Inter_…`, no console errors, before/after screenshots captured.

## Design-review findings (2026-06-13, live https://deepverify.site, light theme)
First impression: clean and competent but reads as a generic SaaS starter template. Classifier = MARKETING/LANDING. Several AI-slop blacklist hits.
- [x] **Typography ships system font, not Inter.** FIXED above (was the #1 highest-leverage fix).
- [ ] **AI-slop: centered-everything.** Hero, all section headings, all feature cards are `text-align:center`. Introduce left-aligned rhythm / asymmetry for at least one section.
- [ ] **AI-slop: 3-column icon-in-circle feature grid** (the single most recognizable AI layout) — 6 cards, icon-in-tinted-square + bold title + 2-line desc. Needs a more editorial treatment.
- [ ] **Flat near-white hero, weak brand anchor + generic copy** ("Multi-Model Deepfake Detection" / "Professional authenticity analysis…"). No strong visual anchor. Brand-first hierarchy is missing.
- [ ] **Perf: load event ~5.6s** in the audit session (download 1.5s, domReady jumps to 5.6s) — re-measure on a warm Vercel deploy; if real, investigate the `ssr:false` dynamic Navbar + render-blocking.

## Backlog (in priority order)
1. [ ] Landing/hero: one strong visual anchor, brand-first hierarchy, clear single primary CTA (upload/analyze); reduce center-alignment.
2. [ ] Upload/analyze flow: loading + progress states for inference (it can take seconds); skeleton/spinner with reassuring copy.
3. [ ] Result display: clear verdict hierarchy (real vs fake confidence), readable heatmaps, per-model breakdown legibility.
4. [ ] Empty/error states: friendly copy + next action (e.g., unsupported file, model unavailable).
5. [ ] Accessibility: WCAG AA contrast, 44px touch targets, focus-visible rings, alt text on result images.
6. [ ] Motion: tasteful entrance/scroll reveals + reduced-motion support (framer-motion is present @ v10).
7. [ ] Feature section: replace the symmetric 3×2 icon-in-circle grid with a more editorial layout.
8. [ ] Performance: confirm/fix the ~5.6s load; image lazy-loading, no layout shift on result render.

## Guardrails
- Frontend design/UX/a11y/perf only. Do NOT touch ML inference logic, auth, payments, DB schema, or backend infra.
- Verify `next build` before every push. One focused commit per run. Never push a broken build.
