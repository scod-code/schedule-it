# Schedule-it

**Clash-free league fixture schedules in seconds.**

Enter your teams, venues, and time slots → get a complete season schedule back as PDF, CSV, and per-team calendar files (.ics). A free preview shows the first 3 fixtures; a one-off £9 payment unlocks the full download.

---

## Tech stack

| Layer | Technology |
|---|---|
| Solver | Google OR-Tools CP-SAT |
| Backend | FastAPI + Jinja2 + HTMX |
| Exports | ReportLab (PDF), stdlib csv, icalendar |
| Payments | Stripe Checkout |
| Storage | File-based JSON (swap for Redis/Postgres later) |
| Deployment | Docker + Docker Compose |

---

## Project structure

```
Schedule-it/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── main.py          # FastAPI routes
│   │   ├── models.py        # Pydantic input/output models
│   │   ├── solver.py        # CP-SAT scheduler
│   │   ├── exporter.py      # PDF, CSV, ICS generation
│   │   ├── payments.py      # Stripe helpers
│   │   └── storage.py       # File-based job persistence
│   ├── templates/           # Jinja2 HTML templates
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/
│   ├── tests/
│   │   ├── test_solver.py   # 20 property/unit tests
│   │   └── test_api.py      # API integration tests
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
└── docker-compose.yml
```

---

## Local development

### Prerequisites

- Python 3.12+
- pip

### Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables
cp .env.example .env
# Edit .env: fill in STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID

# Run the development server
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

### Running tests

```bash
# From the backend/ directory (with venv active)
pytest tests/ -v
```

---

## Docker deployment

```bash
# Build and start
docker compose up --build -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

The app will be available on port 8000. Put Nginx or Caddy in front for HTTPS.

---

## Stripe setup

1. Create a Stripe account at [stripe.com](https://stripe.com).
2. Create a product ("Full fixture schedule") with a one-time price of £9.
3. Copy the **Price ID** (starts with `price_`) into `.env` as `STRIPE_PRICE_ID`.
4. Copy your **Secret Key** (`sk_test_...` for test mode) as `STRIPE_SECRET_KEY`.
5. Set up a webhook in the Stripe dashboard pointing to `https://your-domain.com/webhook`.
   - Listen for: `checkout.session.completed`
   - Copy the **Signing secret** (`whsec_...`) into `.env` as `STRIPE_WEBHOOK_SECRET`.
6. For local webhook testing, use the [Stripe CLI](https://stripe.com/docs/stripe-cli):
   ```bash
   stripe listen --forward-to localhost:8000/webhook
   ```

---

## Hard constraints enforced by the solver

1. Every required match is scheduled exactly once.
2. No team plays more than once per time slot.
3. No venue hosts more matches per slot than its capacity.
4. Team blackout dates are fully respected.

## Soft constraints (minimised)

5. Home/away balance — each team hosts approximately half its games.
6. Consecutive home/away streak limit.

If the constraints are impossible to satisfy (e.g. not enough slots), the site displays a
clear explanation and does **not** charge the user.

---

## Extending to other niches

The solver is generic. New niches need only:
- A new landing page (`templates/`) with prefilled examples.
- A sitemap entry.

Potential niches: tutor timetables, staff rotas, exam invigilation, volunteer rosters.

---

## Legal

- Register as a sole trader with HMRC once income passes the trading allowance.
- Confirm your visa permits self-employment before taking payments.
- Only publish numbers you have measured; don't claim optimality unless CP-SAT proved it.

---

## Contributing

Open-source contributions to the solver core are welcome. The rest of the application is
source-available for portfolio and learning purposes.
