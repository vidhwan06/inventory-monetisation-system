import csv
import os
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from agents.action import action_agent
from agents.demand import demand_agent
from agents.pricing import pricing_agent
from agents.risk import risk_agent
from aggregator.decision import aggregate_decision

app = FastAPI(title="Inventory Monetisation Multi-Agent System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve the data directory relative to this file so it works from any cwd
_DATA_DIR = Path(__file__).parent / "data"

# Frontend URL â€” used for redirects back to the SPA.
# Override with FRONTEND_URL env var when deploying to Render + Vercel.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")

LATEST_ANALYSIS_RESULTS: list[Dict[str, Any]] = []
LATEST_ANALYSIS_FILENAME: str | None = None

FIELD_ALIASES = {
    "name": {"name", "product", "productname", "product_name", "item", "item_name"},
    "price": {"price", "productprice", "product_price"},
    "discount": {"discount", "discountpercent", "discount_percentage", "discount_pct"},
    "sales": {"sales", "sale", "unitssold", "units_sold"},
    "stock": {"stock", "stockquantity", "stock_quantity", "inventory", "quantity"},
}


def normalize_header(header: Any) -> str:
    return str(header or "").strip().lower().replace(" ", "").replace("-", "_")


def parse_numeric(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return default

    cleaned = text.replace(",", "").replace("%", "")
    try:
        return float(cleaned)
    except ValueError:
        return default


def normalize_discount(value: Any) -> float:
    discount = parse_numeric(value, default=0.0)
    if 0 < discount <= 1:
        discount *= 100
    return round(discount, 2)


def normalize_product_row(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized_row = {
        normalize_header(key): value.strip() if isinstance(value, str) else value
        for key, value in row.items()
        if key is not None
    }

    canonical_product: Dict[str, Any] = {}
    for target_key, aliases in FIELD_ALIASES.items():
        for key, value in normalized_row.items():
            comparable_key = key.replace("_", "")
            if key == target_key or key in aliases or comparable_key in aliases:
                canonical_product[target_key] = value
                break

    product_name = canonical_product.get("name")
    if isinstance(product_name, str):
        product_name = product_name.strip()

    return {
        "name": product_name or "Unknown",
        "price": parse_numeric(canonical_product.get("price"), default=0.0),
        "discount": normalize_discount(canonical_product.get("discount")),
        "sales": parse_numeric(canonical_product.get("sales"), default=0.0),
        "stock": parse_numeric(canonical_product.get("stock"), default=0.0),
    }


def load_products_from_rows(rows: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [normalize_product_row(row) for row in rows]


def load_products(filepath: str) -> list[Dict[str, Any]]:
    if not os.path.exists(filepath):
        return []

    with open(filepath, mode="r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        return load_products_from_rows(reader)


def process_product(product: Dict[str, Any]) -> Dict[str, Any]:
    normalized_product = normalize_product_row(product)
    demand_result = demand_agent(normalized_product)
    risk_result = risk_agent(normalized_product)
    pricing_result = pricing_agent(normalized_product)
    action_result = action_agent(demand_result, risk_result)

    final_decision = aggregate_decision(
        product=normalized_product,
        demand=demand_result,
        risk=risk_result,
        pricing=pricing_result,
        action=action_result,
    )

    final_decision.setdefault(
        "action",
        final_decision.get(
            "final_action",
            action_result.get("action", "hold").upper().replace("_", " "),
        ),
    )

    return {
        "product": normalized_product.get("name", "Unknown"),
        "source": normalized_product,
        "agents": {
            "demand_agent": demand_result,
            "risk_agent": risk_result,
            "pricing_agent": pricing_result,
            "action_agent": action_result,
        },
        "final_decision": final_decision,
    }


def compute_results(products: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [process_product(product) for product in products]


@app.get("/")
def home():
    return {"message": "API is running"}


@app.get("/inventory")
def inventory():
    """Redirect to the frontend inventory page (index.html)."""
    return RedirectResponse(url=f"{FRONTEND_URL}/index.html", status_code=302)


@app.get("/login")
def login():
    """Redirect to the frontend login page."""
    return RedirectResponse(url=f"{FRONTEND_URL}/login.html", status_code=302)


@app.get("/analyze_all")
def analyze_all():
    filepath = str(_DATA_DIR / "products.csv")
    products = load_products(filepath)
    results = compute_results(products)
    return {"status": "success", "results": results}


@app.post("/analyze/")
async def analyze_csv(file: UploadFile = File(...)):
    global LATEST_ANALYSIS_RESULTS, LATEST_ANALYSIS_FILENAME
    try:
        contents = await file.read()
        csv_string = contents.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(csv_string))

        products = load_products_from_rows(reader)
        results = compute_results(products)

        demand_analysis = {"fast_moving": [], "slow_moving": [], "dead_stock": []}
        dead_stock_results = []
        rec_prices = {}
        discounts = {}
        decisions_list = []

        for result in results:
            name = result["product"]
            demand_cat = result["agents"]["demand_agent"]["category"]
            if demand_cat == "fast_moving":
                demand_analysis["fast_moving"].append(name)
            elif demand_cat == "slow_moving":
                demand_analysis["slow_moving"].append(name)
            elif demand_cat == "dead_stock":
                demand_analysis["dead_stock"].append(name)

            risk_score = result["agents"]["risk_agent"]["risk_score"]
            dead_stock_results.append({"product_name": name, "risk_score": risk_score})

            rec_prices[name] = result["agents"]["pricing_agent"]["suggested_price"]
            discounts[name] = result["agents"]["pricing_agent"]["discount"]

            decisions_list.append(
                {
                    "item": name,
                    "action": result["final_decision"]["action"],
                    "reason": result["final_decision"]["explanation"],
                }
            )

        response_payload = {
            "demand_analysis": demand_analysis,
            "dead_stock_analysis": {"results": dead_stock_results},
            "pricing": {"recommended_prices": rec_prices, "discounts": discounts},
            "decisions": {"decisions": decisions_list},
            "results": results,
        }

        LATEST_ANALYSIS_RESULTS = results
        LATEST_ANALYSIS_FILENAME = file.filename

        return JSONResponse(content=response_payload)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})


@app.get("/latest-analysis")
def latest_analysis():
    return {
        "filename": LATEST_ANALYSIS_FILENAME,
        "results": LATEST_ANALYSIS_RESULTS,
        "has_results": bool(LATEST_ANALYSIS_RESULTS),
    }


