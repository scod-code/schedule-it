# Schedule-it

A pay-per-use fixture scheduling tool. Enter your teams, venues, and time slots — get a complete, clash-free season schedule back in seconds. Download it as PDF, CSV, and per-team calendar files after a one-off payment.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Option A: Local Development (Recommended)](#option-a-local-development-recommended)
   - [Option B: Docker](#option-b-docker)
5. [Environment Variables](#environment-variables)
6. [Stripe Payments Setup](#stripe-payments-setup)
7. [Running Tests](#running-tests)
8. [API Reference](#api-reference)
9. [Scheduling Constraints](#scheduling-constraints)
10. [Architecture](#architecture)
11. [Deployment](#deployment)

---

## How It Works

1. User fills in the form — teams, venues, time slots, blackout dates
2. The solver generates a clash-free fixture schedule using Google OR-Tools CP-SAT
3. A free preview shows the first 5 rounds
4. A one-off £9 payment unlocks the full schedule
5. User downloads PDF, CSV, and a `.ics` calendar file per team

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, React Hook Form |
| Backend | FastAPI, Python 3.11+ |
| Solver | Google OR-Tools CP-SAT |
| Exports | ReportLab (PDF), icalendar (.ics) |
| Payments | Stripe Checkout |
| Deployment | Docker, Docker Compose, nginx |

---

## Project Structure

```
Schedule-it/
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── api/                # Axios API client
│   │   ├── components/         # Reusable UI components
│   │   └── pages/              # Route-level page components
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── backend/                    # FastAPI REST API
│   ├── app/
│   │   ├── config.py           # Environment settings
│   │   ├── models.py           # Pydantic data models
│   │   ├── solver.py           # CP-SAT scheduling engine
│   │   ├── storage.py          # In-memory job store (30-day expiry)
│   │   ├── exporter.py         # PDF, CSV, ICS generation
│   │   ├── payments.py         # Stripe checkout + webhook
│   │   └── main.py             # FastAPI routes (REST API)
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker-compose.yml
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **Node.js 20+** — [nodejs.org](https://nodejs.org/)
- **Docker Desktop** *(only for the Docker option)* — [docker.com](https://www.docker.com/products/docker-desktop/)

---

### Option A: Local Development (Recommended)

Fastest startup, with hot reload on both frontend and backend.

**Step 1 — Backend**

```powershell
cd backend

# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Open .env and fill in your values (see Environment Variables section)

# Start the backend
uvicorn app.main:app --reload
```

Backend runs at **http://localhost:8000**
Interactive API docs at **http://localhost:8000/docs**

**Step 2 — Frontend** (in a new terminal)

```powershell
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# VITE_API_BASE_URL is already set to http://localhost:8000 by default

# Start the frontend
npm run dev
```

Frontend runs at **http://localhost:5173**

---

### Option B: Docker

Good for testing the production setup, or if you don't want to install Python/Node locally.

```powershell
# First, set up your backend environment file
cp backend/.env.example backend/.env
# Open backend/.env and fill in your values

# Build images (takes 2-3 minutes the first time)
docker-compose build

# Start both services
docker-compose up
```

- Frontend at **http://localhost:3000**
- Backend at **http://localhost:8000**

**Subsequent starts are much faster** — Docker caches the build layers:

```powershell
# Normal start (fast, <5 seconds)
docker-compose up

# After code changes — no rebuild needed, just restart
docker-compose restart

# Only rebuild when you change requirements.txt or package.json
docker-compose up --build
```

---

## Environment Variables

### Backend (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Description |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe secret key — starts with `sk_test_` or `sk_live_` |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key — starts with `pk_test_` or `pk_live_` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret — starts with `whsec_` |
| `STRIPE_PRICE_ID` | Your £9 product price ID — starts with `price_` |
| `BASE_URL` | Your app's public URL (e.g. `http://localhost:8000` locally) |
| `APP_ENV` | `development` or `production` |

### Frontend (`frontend/.env`)

Copy `frontend/.env.example` to `frontend/.env`:

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | URL of the backend API (default: `http://localhost:8000`) |

---

## Stripe Payments Setup

> You can build and test everything locally without Stripe keys. The app handles missing keys gracefully — the payment button just won't work until keys are added.

When you're ready to enable payments:

1. Create a Stripe account at [stripe.com](https://stripe.com)
2. Go to **Products** → **Add product** — name it "Full fixture schedule", price £9, one-time
3. Copy the **Price ID** (starts with `price_`) → paste into `STRIPE_PRICE_ID` in `.env`
4. Go to **Developers** → **API keys** → copy your keys into `.env`
5. For local webhook testing, install the [Stripe CLI](https://stripe.com/docs/stripe-cli) and run:

```powershell
stripe listen --forward-to localhost:8000/webhook
```

Copy the webhook signing secret it prints → paste into `STRIPE_WEBHOOK_SECRET` in `.env`

**When going live:** swap all `sk_test_` / `pk_test_` keys for `sk_live_` / `pk_live_` keys, and update `BASE_URL` to your production domain.

---

## Running Tests

```powershell
cd backend
.\venv\Scripts\activate
python -m pytest tests/ -v
```

Expected output: **21 passed, 2 xfailed** (the xfails are intentional — they document soft-constraint behaviour).

---

## API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/generate` | Run solver, return preview + job_id |
| `GET` | `/api/jobs/{job_id}` | Get job metadata and paid status |
| `POST` | `/api/checkout/{job_id}` | Create Stripe checkout session |
| `POST` | `/webhook` | Stripe webhook (signature-verified) |
| `GET` | `/api/download/{job_id}/pdf` | Download full PDF (paid only) |
| `GET` | `/api/download/{job_id}/csv` | Download CSV (paid only) |
| `GET` | `/api/download/{job_id}/ics/{team}` | Download team calendar file (paid only) |

Full interactive docs available at **http://localhost:8000/docs** when the backend is running.

---

## Scheduling Constraints

The solver enforces these **hard constraints** (always satisfied — no exceptions):

- Each pair of teams plays exactly once (single) or twice (double round-robin)
- No team plays more than once per time slot
- No venue hosts more than one match per time slot
- No matches on blackout dates

These **soft constraints** are optimised (minimised as penalties):

- Home/away balance — teams alternate home and away as fairly as possible
- Max consecutive home games (default: 3)
- Max consecutive away games (default: 3)
- Derby pair separation — rival teams kept apart in the first N rounds

If the constraints are impossible to satisfy (e.g. too few time slots), the solver returns an explanation instead of a schedule — and no payment is taken.

---

## Architecture

```
Browser (React)
     │
     │  JSON over HTTP
     ▼
FastAPI (main.py)
     │
     ├── solver.py      CP-SAT solver (Google OR-Tools)
     ├── storage.py     In-memory job store, 30-day TTL
     ├── exporter.py    PDF / CSV / ICS generation
     └── payments.py    Stripe Checkout + webhook verification
```

**Key design decisions:**

- **No database** — jobs are stored in memory with a 30-day expiry. Simple, zero infrastructure.
- **No user accounts** — one job, one payment, one download link. No login, no session management.
- **CP-SAT for hard constraints** — proves a schedule is valid or impossible (a greedy algorithm can't do this).
- **Penalty minimisation for soft constraints** — home/away balance and derby separation are objective terms, not hard rules, so the solver always finds *something* even when perfect balance isn't achievable.
- **Payment gate is server-side** — download endpoints check `job.paid` before serving files. The Stripe webhook (signature-verified) is the only way to mark a job as paid.

---

## Deployment

The app runs as two Docker containers — backend and frontend — behind nginx.

**Recommended hosts** (cheapest options as of 2026):
- [Render](https://render.com) — free tier available, easy Docker deploy
- [Fly.io](https://fly.io) — good free tier, fast global edge
- [Railway](https://railway.app) — simple, usage-based pricing

**Steps:**

1. Push the repo to GitHub
2. Connect to your chosen host
3. Set all environment variables from the [Environment Variables](#environment-variables) section
4. Set `BASE_URL` to your production domain (e.g. `https://schedule-it.com`)
5. Add your production domain to the CORS list in `backend/app/main.py`
6. Switch Stripe keys from `sk_test_` to `sk_live_`
7. Update the Stripe webhook endpoint URL in your Stripe dashboard to `https://yourdomain.com/webhook`
