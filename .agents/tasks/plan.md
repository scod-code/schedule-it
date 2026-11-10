# Implementation Plan: React + REST API Migration

This plan migrates Schedule-it from a Jinja2/HTMX monolith to a React frontend + REST API backend.

## Key Constraints & Facts
- **DO NOT MODIFY**: solver.py, exporter.py, payments.py, storage.py, models.py, config.py
- **storage.py exports**: create_job, find_cached_job, get_job, mark_paid, record_webhook_event, webhook_event_processed, background_cleanup, initialise_storage
- **models.py**: Job has .paid, .request (ScheduleRequest), .schedule (ScheduleResult). ScheduleResult has .metrics (QualityMetrics with .status). Match, Venue, TimeSlot.
- **Stripe deferred**: Payment routes must compile with placeholder keys; app must not crash
- **Windows PowerShell environment**

---

## FEAT-001: Backend API Refactor

- [ ] 1. Convert backend/app/main.py to pure JSON REST API with CORS
      
      **Changes**:
      - Remove StaticFiles, Jinja2Templates, HTMLResponse, RedirectResponse imports
      - Remove app.mount('/static') and templates lines
      - Add CORSMiddleware with origins: ['http://localhost:5173', 'http://localhost:3000']
      - Keep GET /health as-is
      - Replace GET / with {message: 'Schedule-it API', docs: '/docs'}
      - Remove HTMX routes (/htmx/venue-row, /htmx/slot-row)
      - Replace POST /generate with POST /api/generate accepting ScheduleRequest JSON:
        - If cached, return {job_id, status: 'cached'}
        - If infeasible (result.metrics.status == 'INFEASIBLE'), return JSONResponse({status: 'infeasible', reason: result.infeasibility_reason}, 422)
        - Else return {job_id, status: 'generated', preview: {matches: [first 5 rounds], remaining_count, quality_metrics: result.metrics.model_dump(), teams}}
      - Add GET /api/jobs/{job_id}: get_job, return {job_id, paid, teams, created_at} or 404
      - Replace GET /checkout/{job_id} with POST /api/checkout/{job_id}: return {checkout_url}
      - Keep POST /webhook unchanged
      - Replace GET /download/{job_id}/{format:path} with explicit routes:
        - GET /api/download/{job_id}/pdf
        - GET /api/download/{job_id}/csv
        - GET /api/download/{job_id}/ics/{team_name}
      - Remove: GET /preview/{job_id}, GET /success, GET /privacy, GET /terms, GET /refund
      
      **Files**: backend/app/main.py
      
      **Verify**: `cd backend && python -m pytest tests/test_api.py::test_health_endpoint_returns_ok -v` passes

---

## FEAT-002: Backend Test Updates

- [ ] 2. Update backend/tests/test_api.py for JSON REST API
      
      **Changes**:
      - Rename test_generate_redirects_to_preview to test_generate_returns_json
      - Change to POST /api/generate with JSON body (ScheduleRequest dict)
      - Assert 200 or 422, check for 'job_id' and 'preview' in resp.json()
      - Add test_get_job_returns_metadata: create job, GET /api/jobs/{job_id}, assert metadata
      - Add test_checkout_returns_url: POST /api/checkout/{job_id}, assert {checkout_url}
      - Update test_download_pdf_requires_payment: change URL to /api/download/{job_id}/pdf
      - Remove test_success_page_does_not_mark_job_paid, replace with test_only_webhook_marks_paid
      - Add test_generate_infeasible_returns_422: insufficient slots, assert 422 response
      - Keep test_health_endpoint_returns_ok, test_identical_request_reuses_persisted_schedule, test_webhook_invalid_signature_returns_400
      
      **Files**: backend/tests/test_api.py
      
      **Verify**: `cd backend && python -m pytest tests/test_api.py -v` all pass

---

## FEAT-003: Frontend Implementation

- [ ] 3. Create complete React 18 + Vite + TailwindCSS frontend
      
      **Directory structure**:
      ```
      frontend/
        src/
          components/
            Navbar.jsx
            VenueRow.jsx
            SlotRow.jsx
            ScheduleForm.jsx
            PreviewTable.jsx
            QualityMetrics.jsx
            PaymentButton.jsx
            DownloadLinks.jsx
          pages/
            HomePage.jsx
            PreviewPage.jsx
            SuccessPage.jsx
            PrivacyPage.jsx
            TermsPage.jsx
            RefundPage.jsx
          api/
            scheduleApi.js
          App.jsx
          main.jsx
          index.css
        public/
        index.html
        package.json
        vite.config.js
        tailwind.config.js
        postcss.config.js
        Dockerfile
        nginx.conf
        .env.example
        .eslintrc.cjs
        .gitignore
      ```
      
      **Key files**:
      - package.json: react@18, react-dom@18, react-router-dom@6, vite@5, tailwindcss@3
      - vite.config.js: port 5173, proxy /api to localhost:8000
      - scheduleApi.js: generateSchedule, getJob, createCheckoutSession, getDownloadUrl (uses VITE_API_BASE_URL)
      - ScheduleForm: teams textarea, dynamic venue/slot rows, submit to /api/generate
      - PreviewPage: fetch job, display first 5 rounds, QualityMetrics, PaymentButton if !paid, DownloadLinks if paid
      - SuccessPage: poll getJob until paid (webhook in-flight), show DownloadLinks when paid
      - App.jsx: React Router with routes /, /preview/:jobId, /success, /privacy, /terms, /refund
      - Dockerfile: multi-stage build, nginx serves dist/ on port 80
      - nginx.conf: proxy /api to http://backend:8000 (matches docker-compose service name)
      
      **Files**: All files in frontend/ directory (29 files total)
      
      **Verify**: 
      - `cd frontend && npm install` succeeds
      - `cd frontend && npm run build` succeeds
      - Start backend: `cd backend && uvicorn app.main:app --reload`
      - Start frontend: `cd frontend && npm run dev`
      - Visit http://localhost:5173, fill form, submit, verify preview page shows matches

---

## FEAT-004: Docker Compose Update

- [ ] 4. Update docker-compose.yml to add frontend service
      
      **Changes**:
      - Keep existing 'web' service (backend) as-is
      - Add 'frontend' service:
        - build: {context: ./frontend}
        - image: schedule-it-frontend:latest
        - ports: ['3000:80']
        - depends_on: [web]
        - restart: unless-stopped
      - Add comment: backend on :8000, frontend on :3000, frontend proxies /api to backend
      - Ensure frontend/nginx.conf uses http://web:8000 for proxy_pass (matches service name)
      
      **Files**: docker-compose.yml
      
      **Verify**:
      - `docker-compose build` succeeds for both services
      - `docker-compose up -d` starts both
      - `curl http://localhost:3000` returns HTML
      - `curl http://localhost:8000/health` returns {status: ok}
      - Open http://localhost:3000, submit form, verify it works end-to-end

---

## FEAT-005: Documentation Update

- [ ] 5. Update README.md for new architecture
      
      **Changes**:
      - Tech Stack: change to "Backend: FastAPI REST API", add "Frontend: React 18 + Vite + TailwindCSS + React Router"
      - Local Development Setup > Option 1: add Backend subsection (existing Python steps), Frontend subsection (cd frontend && npm install && npm run dev on :5173)
      - Local Development Setup > Option 2: update Docker note to mention both services, ports :8000 and :3000
      - Architecture: add frontend/ directory description, update main.py to "FastAPI JSON REST API routes with CORS"
      - Add "API Endpoints" section with table: /health GET, /api/generate POST, /api/jobs/{job_id} GET, /api/checkout/{job_id} POST, /webhook POST, /api/download/{job_id}/{format} GET
      - Running Tests: add "cd frontend && npm test" (note if TODO)
      - Deployment: mention frontend as separate service, nginx or Vercel/Netlify, set VITE_API_BASE_URL
      - Stripe Setup: add note that frontend doesn't need Stripe keys
      - Remove all Jinja2/HTMX references
      
      **Files**: README.md
      
      **Verify**: Read README.md, follow instructions to start both backend and frontend, verify they work

---

## Convergence & Review Loop

After all FEATs complete:

- [ ] 6. Integration verification & fixes
      - Run full backend tests: `cd backend && python -m pytest tests/ -v`
      - Build frontend: `cd frontend && npm run build`
      - Test Docker Compose: `docker-compose build && docker-compose up`
      - Manual E2E test: submit form → preview → checkout redirect → webhook simulation → downloads
      - Fix any integration issues between FEATs
      
      **Verify**: All tests pass, Docker Compose runs, E2E flow works

- [ ] 7. Code review & final polish
      - Review all changes for completeness
      - Verify no Jinja2/HTMX/template references remain
      - Verify CORS works from frontend origin
      - Verify Stripe placeholder keys don't crash app
      - Verify all files follow conventions
      - Create git commit with migration changes
      
      **Verify**: Code review complete, ready to commit

