# AssetFlow — Inventory Monetisation System

A multi-agent AI system for inventory analysis and monetisation strategy, built with FastAPI (backend) and plain HTML/JS (frontend).

## Project Structure

```
Inventory monetisation system/
├── backend/                    ← FastAPI API server
│   ├── main.py                 ← App entry point + all routes
│   ├── requirements.txt        ← Python dependencies
│   ├── agents/                 ← AI agent modules
│   │   ├── __init__.py
│   │   ├── action.py
│   │   ├── demand.py
│   │   ├── pricing.py
│   │   ├── risk.py
│   │   └── gemini_config.py
│   ├── aggregator/             ← Decision aggregation
│   │   ├── __init__.py
│   │   └── decision.py
│   ├── templates/              ← Jinja2 server-rendered pages
│   │   ├── base.html
│   │   ├── analytics.html
│   │   ├── monetization.html
│   │   ├── orchestration.html
│   │   └── settings.html
│   ├── data/
│   │   └── products.csv        ← Sample product data
│   └── inventory.csv
│
├── frontend/                   ← Static frontend pages
│   ├── index.html              ← Main inventory dashboard (open in browser)
│   ├── login.html              ← Login page (open in browser)
│   └── static/
│       └── app.js              ← Shared API helpers + utilities
│
├── .env                        ← Environment variables (not committed)
├── .gitignore
└── requirements.txt            ← Root requirements (mirrors backend/)
```

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Health check → `{"message": "API is running"}` |
| GET | `/inventory` | Redirect to frontend index.html |
| GET | `/login` | Redirect to frontend login.html |
| POST | `/analyze/` | Upload CSV → run multi-agent analysis |
| GET | `/latest-analysis` | Get last analysis results (JSON) |
| GET | `/analyze_all` | Analyze built-in `data/products.csv` |
| GET | `/analytics` | Server-rendered analytics dashboard |
| GET | `/monetization` | Server-rendered monetization suggestions |
| GET | `/orchestration` | Server-rendered agent orchestration view |
| GET | `/settings` | Server-rendered settings page |

## Running Locally

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend will be available at: **http://127.0.0.1:8000**

### 2. Frontend

Open `frontend/index.html` directly in your browser, or serve it with any static server:

```bash
# Using Python (from project root)
python -m http.server 5500 --directory frontend
```

Frontend will be available at: **http://127.0.0.1:5500**

### 3. Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
GEMINI_API_KEY=your_google_generative_ai_key
FRONTEND_URL=http://127.0.0.1:5500
```

## Deployment

### Frontend → Vercel
- Deploy the `frontend/` folder
- Set environment variable or update `app.js` `API_BASE` to your Render backend URL

### Backend → Render
- Deploy the `backend/` folder
- Set `GEMINI_API_KEY` and `FRONTEND_URL` in Render environment variables
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
