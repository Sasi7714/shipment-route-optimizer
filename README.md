# Shipment Route Optimization System

An explainable decision-support API for selecting a shipment route when cost, transit time, and operational risk conflict. It uses simulated data only; no route, carrier, or risk value represents a real logistics service.

## What is included

- 20 shipments and 60 synthetic route options in `data/shipments.csv`
- Weighted scoring with adjustable cost, time, and risk priorities
- A combined risk model: 50% delay probability, 30% congestion risk, 20% geopolitical risk
- Pareto analysis to surface non-dominated alternatives
- Plain-language recommendation that compares the winner with its runner-up
- FastAPI interactive documentation, automated tests, and a three-page technical report
- Sanitized request/error logs and consistent JSON error responses
- Environment-controlled feature flags for optimization and Pareto analysis

## Decision method

For each shipment, lower cost, transit time, and combined risk are better. Each metric is min-max normalized across the available routes and inverted to a benefit score. The default overall score is:

`0.40 * cost benefit + 0.30 * time benefit + 0.30 * risk benefit`

Users can supply any non-negative weights with a positive total; the service normalizes them proportionally. Pareto analysis is also returned, because a single weighted winner should not hide valid trade-off options.

## Run locally

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to use the interactive API documentation.

## React dashboard

The interactive React + TypeScript dashboard is in `frontend/`. It lets an operator select a shipment, change the relative importance of cost, speed, and reliability, then see the recommended route, explanation, full ranking, and Pareto alternatives.

Start the API in one terminal:

```powershell
uvicorn app.main:app --reload
```

Start the dashboard in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dashboard uses `http://127.0.0.1:8000` by default. To point it to another backend, copy `.env.example` to `.env` and set `VITE_API_URL`. The API permits the two local Vite origins by default; configure `ALLOWED_ORIGINS` for deployment.

## Useful endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/shipments` | List simulated shipments |
| GET | `/shipments/{shipment_id}/routes` | View all route alternatives |
| POST | `/optimize/{shipment_id}` | Rank routes using supplied priorities |
| GET | `/optimize/{shipment_id}/comparison` | Run the default 40/30/30 comparison |

Example cost/time/risk balance:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/optimize/SH001 `
  -ContentType 'application/json' `
  -Body '{"cost_weight":0.4,"time_weight":0.3,"risk_weight":0.3}'
```

For a cost-sensitive shipment, use `0.70`, `0.15`, and `0.15`. For an urgent shipment, increase `time_weight`. This provides a simple sensitivity check: the recommendation can change when business priorities change.

## Test and generate report

```powershell
pytest -q
python scripts/generate_report_pdf.py
```

The generated submission report is `technical_report.pdf`.

## Reliability, errors, and feature flags

All API errors use a consistent JSON shape: `{"error": {"code": "...", "message": "..."}}`. Invalid inputs return `422`, missing shipments return `404`, disabled functionality returns `503`, and unexpected errors return a generic `500` response with an opaque error ID. Internal exception details are never returned.

Application logs record only an opaque request ID, HTTP method, status, and duration. They intentionally exclude request bodies, headers, authorization values, client IPs, and database details.

Feature flags are read when the server starts. Restart Uvicorn after changing them:

```powershell
$env:ENABLE_OPTIMIZATION = "false"       # Makes /optimize endpoints return 503
$env:ENABLE_PARETO_ANALYSIS = "false"    # Returns weighted ranking without Pareto output
uvicorn app.main:app --reload
```

Set either flag to `true` (or remove it) to enable the feature again.

## Project structure

```text
app/                 FastAPI application, models, scoring, Pareto logic, explanations
data/shipments.csv   Synthetic route dataset
tests/               Unit and API tests
scripts/             Report generator
technical_report.pdf Submission report
```

## Limitations

The system uses static synthetic inputs. A production version should incorporate live carrier quotes, capacity, traffic, weather, port disruption, emissions constraints, calibrated risk estimates, access control, monitoring, and decision audit history.
