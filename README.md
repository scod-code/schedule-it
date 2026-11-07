# Schedule-it

A pay-per-use clash-free fixture scheduling tool. Enter teams, venues, and time slots — get a complete season schedule as PDF, CSV, and per-team .ics calendar files. Pay once to download.

## Tech Stack

- **Backend**: FastAPI + Jinja2 + HTMX
- **Solver**: Google OR-Tools CP-SAT (hard constraints)
- **Exports**: ReportLab (PDF), icalendar (.ics)
- **Payments**: Stripe Checkout
- **Deployment**: Docker + Docker Compose

## Local Development Setup

### Prerequisites

- Python 3.11+
- pip

### Install and run

```bash
cd backend
pip install -r requirements.txt
# Copy and fill in your Stripe keys
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Docker Setup

```bash
# Copy and fill in your env file
cp backend/.env.example backend/.env
docker-compose up --build
```

## Stripe Setup

1. Create a Stripe account at stripe.com
2. Go to Products → Create a product ("Full fixture schedule") with price £9
3. Copy the Price ID (starts with `price_`) into `.env` as `STRIPE_PRICE_ID`
4. Copy your API keys into `.env`
5. For webhooks locally, use the Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:8000/webhook
   ```
   Copy the webhook signing secret into `.env` as `STRIPE_WEBHOOK_SECRET`

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Architecture

- `app/config.py` — Pydantic settings from environment
- `app/models.py` — Pydantic data models (ScheduleRequest, ScheduleResult, Match, etc.)
- `app/solver.py` — CP-SAT scheduling engine with soft-constraint optimisation
- `app/storage.py` — In-memory job store with 30-day expiry
- `app/exporter.py` — PDF, CSV, and .ics generation
- `app/payments.py` — Stripe Checkout session creation and webhook verification
- `app/main.py` — FastAPI routes and form handling

## Constraints Supported

- One match per team per time slot
- One match per venue per time slot
- Blackout dates
- Max consecutive home/away games
- Derby pair separation (first N rounds)
- Single or double round-robin
- Home/away balance optimisation

## Deployment

Deploy to any Docker-compatible host (Fly.io, Render, Railway, DigitalOcean). Set `BASE_URL` to your production URL and switch Stripe to live mode keys.
