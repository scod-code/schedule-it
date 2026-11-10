# Frontend Build Summary

## What was created

A complete React + Vite frontend was built at `frontend/` with the following structure:

### Config files
- `package.json` — React 18, React Router v6, react-hook-form, axios, Vite 5, Tailwind CSS 3
- `vite.config.js` — dev server on port 5173, proxy `/api` and `/webhook` to `localhost:8000`
- `tailwind.config.js` — custom `primary` / `primary-dark` indigo colours
- `postcss.config.js` — Tailwind + Autoprefixer
- `index.html` — SPA root shell
- `.env.example` — `VITE_API_BASE_URL` placeholder
- `Dockerfile` — multi-stage Node 20 → nginx:alpine build
- `nginx.conf` — SPA fallback + `/api/` reverse proxy to `backend:8000`

### API client
- `src/api/scheduleApi.js` — axios wrappers for `generateSchedule`, `getJob`, `createCheckout`, `downloadUrl`; field names confirmed against `backend/app/models.py` (`round_num`, `home_team`, `away_team`, `venue`, `venue_name`, etc.)

### Components
- `Navbar.jsx` — sticky top nav, mobile hamburger toggle
- `Footer.jsx` — links to privacy/terms/refund
- `ScheduleForm.jsx` — full form with react-hook-form + useFieldArray for venues and slots
- `VenueFields.jsx` — venue name + capacity row with remove button
- `SlotFields.jsx` — date + time + venue_name row with remove button
- `PreviewTable.jsx` — match table with locked-row blur overlay for unpaid matches
- `QualityBadge.jsx` — clash count, home/away breaks, balance score, solve time
- `DownloadLinks.jsx` — PDF, CSV, and per-team ICS download links

### Pages
- `HomePage.jsx` — hero + feature cards + ScheduleForm
- `PreviewPage.jsx` — preview table, quality badge, unlock CTA (£9 Stripe checkout)
- `SuccessPage.jsx` — post-payment download links via DownloadLinks
- `PrivacyPage.jsx`, `TermsPage.jsx`, `RefundPage.jsx` — legal pages

### Routing
- `App.jsx` — BrowserRouter with routes: `/`, `/preview/:jobId`, `/success`, `/privacy`, `/terms`, `/refund`

### docker-compose.yml
Updated root compose file: renamed `web` service to `backend`, added `frontend` service building `./frontend` and serving on port `3000`.

## Build result

```
dist/
  assets/
    index-CP8QeqoF.css   (15 KB)
    index-DNXKV_Yr.js    (293 KB)
  index.html
  vite.svg
```

Build: **PASSED** — 0 errors.

## Running locally

```powershell
# Backend (FastAPI)
cd backend
uvicorn app.main:app --reload
# → http://localhost:8000

# Frontend (Vite dev server)
cd frontend
npm run dev
# → http://localhost:5173  (proxies /api → :8000)
```
