import os
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from io import StringIO
import csv
from typing import Any, Dict, Iterable

from agents.demand import demand_agent
from agents.risk import risk_agent
from agents.pricing import pricing_agent
from agents.action import action_agent
from aggregator.decision import aggregate_decision

app = FastAPI(title="Inventory Monetisation Multi-Agent System")

# Ensure templates and static directories exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

FIELD_ALIASES = {
    "name": {"name", "product", "productname", "product_name", "item", "item_name"},
    "price": {"price", "productprice", "product_price"},
    "discount": {"discount", "discountpercent", "discount_percentage", "discount_pct"},
    "sales": {"sales", "sale", "unitssold", "units_sold"},
    "stock": {"stock", "stockquantity", "stock_quantity", "inventory", "quantity"},
}

import csv
import os
from io import StringIO
from typing import Any, Dict, Iterable

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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

# Ensure templates and static directories exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

FIELD_ALIASES = {
    "name": {"name", "product", "productname", "product_name", "item", "item_name"},
    "price": {"price", "productprice", "product_price"},
    "discount": {"discount", "discountpercent", "discount_percentage", "discount_pct"},
    "sales": {"sales", "sale", "unitssold", "units_sold"},
    "stock": {"stock", "stockquantity", "stock_quantity", "inventory", "quantity"},
}


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

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

def process_product(product: dict):
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
        action=action_result
    )
    
    return {
        "product": normalized_product.get("name", "Unknown"),
        "agents": {
            "demand_agent": demand_result,
            "risk_agent": risk_result,
            "pricing_agent": pricing_result,
            "action_agent": action_result
        },
        "final_decision": final_decision
    }

def load_products(filepath: str):
    products = []
    if not os.path.exists(filepath):
        return products
    with open(filepath, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return load_products_from_rows(reader)

@app.get("/analyze_all")
def analyze_all():
    filepath = os.path.join("data", "products.csv")
    products = load_products(filepath)
    results = [process_product(p) for p in products]
    return {"status": "success", "results": results}


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


def process_product(product: dict):
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

    if "action" not in final_decision:
        final_decision["action"] = final_decision.get(
            "final_action",
            action_result.get("action", "hold").upper().replace("_", " "),
        )

    return {
        "product": normalized_product.get("name", "Unknown"),
        "agents": {
            "demand_agent": demand_result,
            "risk_agent": risk_result,
            "pricing_agent": pricing_result,
            "action_agent": action_result,
        },
        "final_decision": final_decision,
    }


def load_products(filepath: str):
    products = []
    if not os.path.exists(filepath):
        return products

    with open(filepath, mode="r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        return load_products_from_rows(reader)


@app.get("/analyze_all")
def analyze_all():
    filepath = os.path.join("data", "products.csv")
    products = load_products(filepath)
    results = [process_product(product) for product in products]
    return {"status": "success", "results": results}


@app.post("/analyze/")
async def analyze_csv(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        csv_string = contents.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(csv_string))
        
        products = load_products_from_rows(reader)
        results = [process_product(p) for p in products]
        
        # We return the format but the frontend index.html expects the old structure
        # Let's map our results to the expected format so the UI works seamlessly!
        
        # Build structure for old UI:

        products = load_products_from_rows(reader)
        results = [process_product(product) for product in products]

        demand_analysis = {"fast_moving": [], "slow_moving": [], "dead_stock": []}
        dead_stock_results = []
        rec_prices = {}
        discounts = {}
        decisions_list = []
        
        for r in results:
            name = r["product"]
            demand_cat = r["agents"]["demand_agent"]["category"]
            if demand_cat == "fast_moving": demand_analysis["fast_moving"].append(name)
            elif demand_cat == "slow_moving": demand_analysis["slow_moving"].append(name)
            elif demand_cat == "dead_stock": demand_analysis["dead_stock"].append(name)
            
            risk_score = r["agents"]["risk_agent"]["risk_score"]
            dead_stock_results.append({"product_name": name, "risk_score": risk_score})
            
            rec_prices[name] = r["agents"]["pricing_agent"]["suggested_price"]
            discounts[name] = r["agents"]["pricing_agent"]["discount"]
            
            decisions_list.append({"item": name, "action": r["final_decision"]["final_action"], "reason": r["final_decision"]["explanation"]})

        old_format_response = {

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
            "results": results
        }
        
        return JSONResponse(content=old_format_response)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
            "results": results,
        }

        return JSONResponse(content=response_payload)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})


@app.get("/analytics", response_class=HTMLResponse)
def analytics():
    filepath = os.path.join("data", "products.csv")
    products = load_products(filepath)
    results = [process_product(product) for product in products]

    total_products = len(results)
    fast_moving = sum(
        1 for result in results if result["agents"]["demand_agent"]["category"] == "fast_moving"
    )
    slow_moving = sum(
        1 for result in results if result["agents"]["demand_agent"]["category"] == "slow_moving"
    )
    dead_stock = sum(
        1 for result in results if result["agents"]["demand_agent"]["category"] == "dead_stock"
    )
    average_confidence = (
        sum(result["final_decision"].get("confidence", 0.0) or 0.0 for result in results) / total_products
        if total_products
        else 0.0
    )

    return f"""
    <html>
        <head>
            <title>Inventory Analytics</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 40px;
                    background: #f8fafc;
                    color: #0f172a;
                }}
                .grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 16px;
                    max-width: 960px;
                }}
                .card {{
                    background: white;
                    border-radius: 16px;
                    padding: 20px;
                    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
                }}
                h1 {{
                    margin-bottom: 24px;
                }}
                .label {{
                    font-size: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    color: #64748b;
                }}
                .value {{
                    font-size: 32px;
                    font-weight: 700;
                    margin-top: 8px;
                }}
            </style>
        </head>
        <body>
            <h1>Inventory Analytics</h1>
            <div class="grid">
                <div class="card">
                    <div class="label">Total Products</div>
                    <div class="value">{total_products}</div>
                </div>
                <div class="card">
                    <div class="label">Fast Moving</div>
                    <div class="value">{fast_moving}</div>
                </div>
                <div class="card">
                    <div class="label">Slow Moving</div>
                    <div class="value">{slow_moving}</div>
                </div>
                <div class="card">
                    <div class="label">Dead Stock</div>
                    <div class="value">{dead_stock}</div>
                </div>
                <div class="card">
                    <div class="label">Avg Confidence</div>
                    <div class="value">{average_confidence:.0%}</div>
                </div>
            </div>
        </body>
    </html>
    """


@app.get("/{page_name}")
def get_page(request: Request, page_name: str):
    if os.path.exists(f"templates/{page_name}.html"):
        return templates.TemplateResponse(request=request, name=f"{page_name}.html")
    if os.path.exists(f"templates/{page_name}"):
        return templates.TemplateResponse(request=request, name=page_name)
    
    # Let FastAPI return 404 for missing APIs or pages
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="Page not found")
