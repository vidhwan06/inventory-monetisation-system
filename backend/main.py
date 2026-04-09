import csv
import os
import re
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd
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

_DATA_DIR = Path(__file__).parent / "data"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")

LATEST_ANALYSIS_RESULTS: list[Dict[str, Any]] = []
LATEST_ANALYSIS_FILENAME: str | None = None

FIELD_ALIASES = {
    "name": {"name", "product", "productname", "product_name", "item", "item_name", "productname"},
    "price": {
        "price",
        "productprice",
        "product_price",
        "mrp",
        "sellingprice",
        "selling_price",
        "unitprice",
        "unit_price",
        "saleprice",
        "sale_price",
        "retailprice",
        "retail_price",
    },
    "discount": {"discount", "discountpercent", "discount_percentage", "discount_pct"},
    "sales": {
        "sales",
        "sale",
        "unitssold",
        "units_sold",
        "unitssoldlast30days",
        "units_sold_last_30_days",
        "units_sold_last30days",
        "last30daysales",
        "saleslast30days",
        "sales_last_30_days",
        "monthlysales",
        "monthly_sales",
        "salesvolume",
        "sales_volume",
        "soldqty",
        "sold_qty",
        "quantitysold",
        "quantity_sold",
        "qtysold",
        "qty_sold",
    },
    "stock": {
        "stock",
        "stockquantity",
        "stock_quantity",
        "inventory",
        "quantity",
        "availablequantity",
        "available_quantity",
        "currentstock",
        "current_stock",
        "onhand",
        "on_hand",
        "stockonhand",
        "stock_on_hand",
        "inventoryonhand",
        "inventory_on_hand",
        "availablestock",
        "available_stock",
    },
    "last_sold_date": {
        "lastsolddate",
        "last_sold_date",
        "lastsold",
        "recent_sale_date",
        "last_sale_date",
        "dateoflastsale",
        "date_of_last_sale",
        "lastsoldon",
        "last_sold_on",
        "lastsale",
        "last_sale",
    },
}

FIELD_TOKEN_HINTS = {
    "name": [{"name"}, {"product"}, {"item"}],
    "price": [{"price"}, {"mrp"}, {"selling", "price"}, {"unit", "price"}, {"retail", "price"}],
    "discount": [{"discount"}],
    "sales": [
        {"sales"},
        {"sold"},
        {"units", "sold"},
        {"quantity", "sold"},
        {"qty", "sold"},
        {"monthly", "sales"},
        {"30", "days", "sales"},
        {"30", "days", "sold"},
    ],
    "stock": [
        {"stock"},
        {"inventory"},
        {"quantity"},
        {"available", "quantity"},
        {"available", "stock"},
        {"on", "hand"},
    ],
    "last_sold_date": [
        {"last", "sold", "date"},
        {"last", "sale", "date"},
        {"recent", "sale", "date"},
        {"date", "last", "sale"},
    ],
}


def normalize_header(header: Any) -> str:
    text = str(header or "").strip().lower().replace("-", "_")
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


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


def find_matching_column(columns: Iterable[str], aliases: set[str]) -> str | None:
    for column in columns:
        comparable = normalize_header(column).replace("_", "")
        if column in aliases or comparable in aliases:
            return column
    return None


def find_matching_column_for_field(columns: Iterable[str], field_name: str, aliases: set[str]) -> str | None:
    matched_column = find_matching_column(columns, aliases)
    if matched_column:
        return matched_column

    token_hints = FIELD_TOKEN_HINTS.get(field_name, [])
    for column in columns:
        column_tokens = set(normalize_header(column).split("_"))
        if any(token_hint.issubset(column_tokens) for token_hint in token_hints):
            return column
    return None


def build_clean_inventory_dataframe(rows: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    raw_df = pd.DataFrame(list(rows))
    if raw_df.empty:
        return pd.DataFrame(
            columns=[
                "name",
                "price",
                "discount",
                "sales",
                "stock",
                "last_sold_date",
                "reference_date",
                "days_since_last_sale",
            ]
        )

    raw_df.columns = [normalize_header(column) for column in raw_df.columns]
    matched_columns: dict[str, str | None] = {}

    cleaned_df = pd.DataFrame(index=raw_df.index)
    for target_key, aliases in FIELD_ALIASES.items():
        matched_column = find_matching_column_for_field(raw_df.columns, target_key, aliases)
        matched_columns[target_key] = matched_column
        cleaned_df[target_key] = raw_df[matched_column] if matched_column else None

    cleaned_df["name"] = cleaned_df["name"].fillna("Unknown").astype(str).str.strip()
    cleaned_df.loc[cleaned_df["name"] == "", "name"] = "Unknown"

    cleaned_df["price"] = cleaned_df["price"].apply(lambda value: parse_numeric(value, default=0.0))
    cleaned_df["discount"] = cleaned_df["discount"].apply(normalize_discount)
    cleaned_df["sales"] = cleaned_df["sales"].apply(lambda value: int(parse_numeric(value, default=0.0)))
    cleaned_df["stock"] = cleaned_df["stock"].apply(lambda value: parse_numeric(value, default=0.0))
    cleaned_df["last_sold_date"] = pd.to_datetime(cleaned_df["last_sold_date"], errors="coerce")

    reference_date = cleaned_df["last_sold_date"].dropna().max()
    cleaned_df["reference_date"] = reference_date

    if pd.isna(reference_date):
        cleaned_df["days_since_last_sale"] = None
    else:
        day_deltas = (reference_date - cleaned_df["last_sold_date"]).dt.days
        cleaned_df["days_since_last_sale"] = day_deltas.where(cleaned_df["last_sold_date"].notna(), other=None)

    cleaned_df["sales_data_present"] = matched_columns["sales"] is not None
    cleaned_df["stock_data_present"] = matched_columns["stock"] is not None
    cleaned_df["last_sold_date_present"] = matched_columns["last_sold_date"] is not None

    return cleaned_df


def normalize_product_row(product: Dict[str, Any]) -> Dict[str, Any]:
    days_since_last_sale = product.get("days_since_last_sale")
    if pd.isna(days_since_last_sale):
        days_since_last_sale = None
    elif days_since_last_sale is not None:
        days_since_last_sale = int(days_since_last_sale)

    last_sold_date = product.get("last_sold_date")
    if pd.notna(last_sold_date):
        last_sold_date = pd.Timestamp(last_sold_date).date().isoformat()
    else:
        last_sold_date = None

    reference_date = product.get("reference_date")
    if pd.notna(reference_date):
        reference_date = pd.Timestamp(reference_date).date().isoformat()
    else:
        reference_date = None

    return {
        "name": str(product.get("name") or "Unknown").strip() or "Unknown",
        "price": parse_numeric(product.get("price"), default=0.0),
        "discount": normalize_discount(product.get("discount")),
        "sales": int(parse_numeric(product.get("sales"), default=0.0)),
        "stock": parse_numeric(product.get("stock"), default=0.0),
        "last_sold_date": last_sold_date,
        "reference_date": reference_date,
        "days_since_last_sale": days_since_last_sale,
        "sales_data_present": bool(product.get("sales_data_present", False)),
        "stock_data_present": bool(product.get("stock_data_present", False)),
        "last_sold_date_present": bool(product.get("last_sold_date_present", False)),
    }


def load_products_from_rows(rows: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    cleaned_df = build_clean_inventory_dataframe(rows)
    return [normalize_product_row(product) for product in cleaned_df.to_dict(orient="records")]


def load_products(filepath: str) -> list[Dict[str, Any]]:
    if not os.path.exists(filepath):
        return []

    with open(filepath, mode="r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        return load_products_from_rows(reader)


def process_product(product: Dict[str, Any]) -> Dict[str, Any]:
    cleaned_product = normalize_product_row(product)
    demand_result = demand_agent(cleaned_product)
    risk_result = risk_agent(cleaned_product)
    pricing_result = pricing_agent(cleaned_product)
    action_result = action_agent(demand_result, risk_result)

    final_decision = aggregate_decision(
        product=cleaned_product,
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
        "product": cleaned_product.get("name", "Unknown"),
        "source": cleaned_product,
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
    return RedirectResponse(url=f"{FRONTEND_URL}/index.html", status_code=302)


@app.get("/login")
def login():
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

        demand_analysis = {
            "high_demand": [],
            "medium_demand": [],
            "low_demand": [],
            "fast_moving": [],
            "healthy": [],
            "slow_moving": [],
            "dead_stock": [],
        }
        dead_stock_results = []
        rec_prices = {}
        discounts = {}
        decisions_list = []

        for result in results:
            name = result["product"]
            demand_agent_result = result["agents"]["demand_agent"]
            risk_agent_result = result["agents"]["risk_agent"]

            demand_band = demand_agent_result["demand_band"]
            if demand_band == "high":
                demand_analysis["high_demand"].append(name)
                demand_analysis["fast_moving"].append(name)
            elif demand_band == "medium":
                demand_analysis["medium_demand"].append(name)
                demand_analysis["healthy"].append(name)
            else:
                demand_analysis["low_demand"].append(name)
                if not risk_agent_result["is_dead_stock"]:
                    demand_analysis["slow_moving"].append(name)

            if risk_agent_result["is_dead_stock"]:
                demand_analysis["dead_stock"].append(name)

            dead_stock_results.append(
                {
                    "product_name": name,
                    "is_dead_stock": risk_agent_result["is_dead_stock"],
                    "inventory_status": risk_agent_result["inventory_status"],
                    "risk_score": risk_agent_result["risk_score"],
                    "days_since_last_sale": risk_agent_result["days_since_last_sale"],
                    "last_sold_date": risk_agent_result["last_sold_date"],
                    "reference_date": risk_agent_result["reference_date"],
                    "reason": risk_agent_result["reason"],
                }
            )

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
            "pipeline": {
                "steps": [
                    "CSV upload parsed into a shared cleaned inventory dataframe",
                    "Column aliases normalized for name, stock, sales, price, and last sold date",
                    "Reference date set to the maximum Last Sold Date found in the uploaded dataset",
                    "Dead stock, demand, pricing, and liquidation agents run independently on each cleaned product record",
                    "Agent outputs aggregated into final recommendations",
                ]
            },
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
