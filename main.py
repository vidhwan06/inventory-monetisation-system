from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import pandas as pd
from dotenv import load_dotenv

from agents.orchestrator import run_multi_agent_system

# Load environment variables
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Create static dir if not exists
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# -----------------------------
# CORS (important for frontend)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# ROUTES (Frontend Pages)
# -----------------------------
@app.get("/")
def home():
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))

@app.get("/login")
def serve_login():
    return FileResponse(os.path.join(TEMPLATES_DIR, "login.html"))

@app.get("/orchestration")
def serve_orchestration():
    return FileResponse(os.path.join(TEMPLATES_DIR, "orchestration.html"))

@app.get("/inventory")
def serve_inventory():
    return FileResponse(os.path.join(TEMPLATES_DIR, "inventory_view.html"))

@app.get("/monetization")
def serve_monetization():
    return FileResponse(os.path.join(TEMPLATES_DIR, "monetization.html"))

@app.get("/settings")
def serve_settings():
    return FileResponse(os.path.join(TEMPLATES_DIR, "settings.html"))

# -----------------------------
# MAIN ANALYSIS API
# -----------------------------
@app.post("/analyze/")
async def analyze(file: UploadFile = File(...)):

    try:
        # Read CSV
        df = pd.read_csv(file.file)
        
        # Clean column names
        df.columns = df.columns.str.strip()

        if "item_name" not in df.columns:
            return {"error": "Invalid CSV: Must contain 'item_name' column (case-sensitive, trimmed)."}

        # 🔥 Run full multi-agent system
        result = run_multi_agent_system(df)

        return result

    except Exception as e:
        return {"error": str(e)}