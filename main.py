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

os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

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


def category_label(category: str) -> str:
    return str(category or "healthy").replace("_", " ").title()


def currency(value: float) -> str:
    return f"Rs. {value:,.0f}"


def build_analytics_context(results: list[Dict[str, Any]]) -> Dict[str, Any]:
    total_products = len(results)
    if total_products == 0:
        return {
            "active_page": "analytics",
            "page_title": "AssetFlow | Analytics",
            "search_placeholder": "Search analytics...",
            "dashboard_title": "Analytics Dashboard",
            "dashboard_subtitle": "Upload a CSV from Inventory to generate live analytics.",
            "stats": [],
            "distribution_labels": [],
            "distribution_values": [],
            "action_labels": [],
            "action_values": [],
            "risk_rows": [],
            "insights": [],
            "analytics_drilldowns": {},
            "empty_state": True,
        }

    total_inventory_value = 0.0
    revenue_opportunity = 0.0
    confidence_total = 0.0

    category_counts = {
        "Fast Moving": 0,
        "Healthy": 0,
        "Slow Moving": 0,
        "Dead Stock": 0,
    }
    action_value_map: Dict[str, float] = {}
    risk_rows = []
    dead_stock_items = []
    fast_moving_items = []
    revenue_items = []
    inventory_value_items = []
    category_items_map: Dict[str, list[Dict[str, Any]]] = {label: [] for label in category_counts}
    action_items_map: Dict[str, list[Dict[str, Any]]] = {}

    for result in results:
        source = result.get("source", {})
        pricing = result.get("agents", {}).get("pricing_agent", {})
        demand = result.get("agents", {}).get("demand_agent", {})
        risk = result.get("agents", {}).get("risk_agent", {})
        decision = result.get("final_decision", {})

        stock = parse_numeric(source.get("stock"), default=0.0)
        price = parse_numeric(pricing.get("current_price", source.get("price")), default=0.0)
        inventory_value = stock * price
        total_inventory_value += inventory_value

        category = category_label(demand.get("category"))
        if category in category_counts:
            category_counts[category] += 1

        expected_change = parse_numeric(decision.get("expected_profit_change"), default=0.0)
        revenue_opportunity += max(expected_change, 0.0)

        confidence_total += parse_numeric(decision.get("confidence"), default=0.0)

        action = str(decision.get("action") or decision.get("final_action") or "HOLD")
        action_value_map[action] = action_value_map.get(action, 0.0) + max(expected_change, 0.0)

        row_summary = {
            "item": result.get("product", "Unknown"),
            "status": category,
            "risk_label": str(risk.get("level", "low")).title(),
            "risk_score": parse_numeric(risk.get("risk_score"), default=0.0),
            "action": action.replace("_", " ").title(),
            "inventory_value": inventory_value,
            "expected_change": expected_change,
        }
        category_items_map.setdefault(category, []).append(row_summary)
        action_items_map.setdefault(action.replace("_", " ").title(), []).append(row_summary)
        inventory_value_items.append(row_summary)

        if category == "Dead Stock":
            dead_stock_items.append(row_summary)
        if category == "Fast Moving":
            fast_moving_items.append(row_summary)
        if expected_change > 0:
            revenue_items.append(row_summary)

        risk_rows.append(
            {
                **row_summary,
            }
        )

    risk_rows.sort(key=lambda row: row["risk_score"], reverse=True)
    inventory_value_items.sort(key=lambda row: row["inventory_value"], reverse=True)
    dead_stock_items.sort(key=lambda row: row["risk_score"], reverse=True)
    fast_moving_items.sort(key=lambda row: row["inventory_value"], reverse=True)
    revenue_items.sort(key=lambda row: row["expected_change"], reverse=True)
    for items in category_items_map.values():
        items.sort(key=lambda row: row["risk_score"], reverse=True)
    for items in action_items_map.values():
        items.sort(key=lambda row: row["expected_change"], reverse=True)

    top_risk = risk_rows[0]["item"] if risk_rows else "No inventory loaded"
    dead_stock_ratio = (
        (category_counts["Dead Stock"] / total_products) if total_products else 0.0
    )
    average_confidence = confidence_total / total_products if total_products else 0.0

    chart_action_labels = list(action_value_map.keys()) or ["HOLD"]
    chart_action_values = [round(action_value_map[label], 2) for label in chart_action_labels] or [0]

    insights = [
        f"{category_counts['Dead Stock']} items are currently classed as dead stock, which is {dead_stock_ratio:.0%} of analyzed inventory.",
        f"Top holding-risk item: {top_risk}. Prioritize this item first in your next monetisation cycle.",
        f"Average decision confidence is {average_confidence:.0%}, giving the team a quick sense of recommendation quality.",
    ]

    def format_drilldown_items(items: list[Dict[str, Any]]) -> list[Dict[str, str]]:
        return [
            {
                "item": row["item"],
                "meta": f"{row['status']} | Risk {row['risk_label']} | Action {row['action']}",
                "value": currency(row["inventory_value"]),
                "value_label": "Inventory Value" if row["inventory_value"] > 0 else "Revenue Upside",
                "inventory_value": round(row["inventory_value"], 2),
                "expected_change": round(max(row["expected_change"], 0.0), 2),
                "risk_score": round(row["risk_score"], 4),
                "status": row["status"],
                "action": row["action"],
            }
            for row in items[:6]
        ]

    analytics_drilldowns = {
        "total_inventory_value": {
            "title": "Largest Inventory Value Exposure",
            "summary": "Products contributing the most to current inventory value based on stock and current price.",
            "items": format_drilldown_items(inventory_value_items),
        },
        "dead_stock_share": {
            "title": "Dead Stock Items",
            "summary": "These uploaded products are currently classified as dead stock and should be reviewed first.",
            "items": format_drilldown_items(dead_stock_items),
        },
        "fast_moving": {
            "title": "Fast Moving Products",
            "summary": "These products are moving quickly and are the best candidates for replenishment planning.",
            "items": format_drilldown_items(fast_moving_items),
        },
        "revenue_opportunity": {
            "title": "Top Revenue Opportunities",
            "summary": "Products with the strongest positive expected profit change from the recommended action.",
            "items": format_drilldown_items(revenue_items),
        },
    }

    for category_name, items in category_items_map.items():
        analytics_drilldowns[f"category::{category_name}"] = {
            "title": f"{category_name} Inventory",
            "summary": f"Products in the {category_name.lower()} segment from the uploaded CSV.",
            "items": format_drilldown_items(items),
        }

    for action_name, items in action_items_map.items():
        analytics_drilldowns[f"action::{action_name}"] = {
            "title": f"{action_name} Recommendations",
            "summary": f"Products currently mapped to the {action_name.lower()} action pattern.",
            "items": format_drilldown_items(items),
        }

    return {
        "active_page": "analytics",
        "page_title": "AssetFlow | Analytics",
        "search_placeholder": "Search analytics...",
        "dashboard_title": "Analytics Dashboard",
        "dashboard_subtitle": "Live metrics generated from the current inventory dataset.",
        "stats": [
            {
                "label": "Total Inventory Value",
                "value": currency(total_inventory_value),
                "tone": "text-on-surface",
            },
            {
                "label": "Dead Stock Share",
                "value": f"{dead_stock_ratio:.0%}",
                "tone": "text-red-600",
            },
            {
                "label": "Fast Moving",
                "value": str(category_counts["Fast Moving"]),
                "tone": "text-emerald-600",
            },
            {
                "label": "Revenue Opportunity",
                "value": currency(revenue_opportunity),
                "tone": "text-primary",
            },
        ],
        "distribution_labels": list(category_counts.keys()),
        "distribution_values": list(category_counts.values()),
        "action_labels": chart_action_labels,
        "action_values": chart_action_values,
        "risk_rows": risk_rows[:5],
        "insights": insights,
        "analytics_drilldowns": analytics_drilldowns,
        "empty_state": total_products == 0,
    }


def build_monetization_context(results: list[Dict[str, Any]]) -> Dict[str, Any]:
    total_products = len(results)
    if total_products == 0:
        return {
            "active_page": "monetization",
            "page_title": "Monetization Suggestions | AssetFlow",
            "search_placeholder": "Search monetization actions...",
            "empty_state": True,
            "headline_value": currency(0),
            "headline_label": "Estimated Potential Gain",
            "hero": None,
            "liquidation_alert": None,
            "health_summary": [],
            "action_cards": [],
            "recommendations": [],
        }

    enriched = []
    positive_gain = 0.0
    capital_at_risk = 0.0
    action_counts: Dict[str, int] = {}

    for result in results:
        source = result.get("source", {})
        pricing = result.get("agents", {}).get("pricing_agent", {})
        risk = result.get("agents", {}).get("risk_agent", {})
        demand = result.get("agents", {}).get("demand_agent", {})
        decision = result.get("final_decision", {})

        stock = parse_numeric(source.get("stock"), default=0.0)
        current_price = parse_numeric(pricing.get("current_price", source.get("price")), default=0.0)
        suggested_price = parse_numeric(pricing.get("suggested_price", current_price), default=current_price)
        expected_change = parse_numeric(decision.get("expected_profit_change"), default=0.0)
        expected_profit = parse_numeric(decision.get("expected_profit"), default=0.0)
        risk_score = parse_numeric(risk.get("risk_score"), default=0.0)
        inventory_value = stock * current_price
        action = str(decision.get("action") or decision.get("final_action") or "HOLD").replace("_", " ").title()
        category = category_label(demand.get("category"))
        discount = parse_numeric(pricing.get("discount"), default=0.0)
        confidence = parse_numeric(decision.get("confidence"), default=0.0)

        if expected_change > 0:
            positive_gain += expected_change
        if str(risk.get("level", "low")).lower() == "high":
            capital_at_risk += inventory_value
        action_counts[action] = action_counts.get(action, 0) + 1

        enriched.append(
            {
                "product": result.get("product", "Unknown"),
                "action": action,
                "category": category,
                "risk_label": str(risk.get("level", "low")).title(),
                "risk_score": risk_score,
                "confidence": confidence,
                "inventory_value": inventory_value,
                "current_price": current_price,
                "suggested_price": suggested_price,
                "discount": discount,
                "expected_change": expected_change,
                "expected_profit": expected_profit,
                "explanation": decision.get("explanation") or "No explanation available.",
            }
        )

    enriched.sort(key=lambda item: item["expected_change"], reverse=True)
    highest_gain = enriched[0]
    liquidation_candidate = max(
        enriched,
        key=lambda item: (
            1 if item["category"] == "Dead Stock" else 0,
            1 if item["risk_label"] == "High" else 0,
            item["risk_score"],
            item["inventory_value"],
        ),
    )

    def format_money(value: float) -> str:
        return currency(value)

    action_styles = {
        "Increase Price": {
            "icon": "trending_up",
            "label": "Margin Expansion",
            "accent": "bg-secondary-container text-on-secondary-container",
            "cta": "Review Price Move",
        },
        "Promote": {
            "icon": "sell",
            "label": "Inventory Aging",
            "accent": "bg-primary-fixed text-on-primary-fixed-variant",
            "cta": "Plan Promotion",
        },
        "Hold": {
            "icon": "verified",
            "label": "Protect Margin",
            "accent": "bg-surface-container-high text-on-surface",
            "cta": "Review Hold Logic",
        },
        "Liquidate": {
            "icon": "local_offer",
            "label": "Recovery Move",
            "accent": "bg-error-container text-on-error-container",
            "cta": "Prepare Liquidation",
        },
    }

    spotlight_actions = []
    seen_actions = set()
    for item in enriched:
        action = item["action"]
        if action in seen_actions:
            continue
        seen_actions.add(action)
        spotlight_actions.append(item)
        if len(spotlight_actions) == 3:
            break

    action_cards = []
    for item in spotlight_actions:
        style = action_styles.get(
            item["action"],
            {
                "icon": "insights",
                "label": "Action Opportunity",
                "accent": "bg-surface-container-high text-on-surface",
                "cta": "Review Recommendation",
            },
        )
        price_change_pct = (
            ((item["suggested_price"] - item["current_price"]) / item["current_price"]) * 100
            if item["current_price"]
            else 0.0
        )
        action_cards.append(
            {
                "title": item["action"],
                "tagline": style["label"],
                "product": item["product"],
                "description": item["explanation"],
                "metric_label": "Projected impact",
                "metric_value": format_money(item["expected_change"]),
                "secondary_label": "Price move",
                "secondary_value": f"{price_change_pct:+.0f}%",
                "icon": style["icon"],
                "accent": style["accent"],
                "cta": style["cta"],
            }
        )

    health_summary = [
        {
            "label": "Positive Opportunities",
            "value": str(sum(1 for item in enriched if item["expected_change"] > 0)),
            "meta": f"{format_money(positive_gain)} total upside",
        },
        {
            "label": "High-Risk Capital",
            "value": format_money(capital_at_risk),
            "meta": f"{sum(1 for item in enriched if item['risk_label'] == 'High')} items flagged",
        },
        {
            "label": "Top Action Pattern",
            "value": max(action_counts.items(), key=lambda entry: entry[1])[0],
            "meta": f"{total_products} products analyzed",
        },
    ]

    recommendations = [
        {
            "product": item["product"],
            "action": item["action"],
            "category": item["category"],
            "risk_label": item["risk_label"],
            "confidence": f"{item['confidence']:.0%}",
            "impact": format_money(item["expected_change"]),
            "inventory_value": format_money(item["inventory_value"]),
            "price_change": format_money(item["suggested_price"]),
            "explanation": item["explanation"],
        }
        for item in enriched[:8]
    ]

    return {
        "active_page": "monetization",
        "page_title": "Monetization Suggestions | AssetFlow",
        "search_placeholder": "Search monetization actions...",
        "empty_state": False,
        "headline_value": format_money(positive_gain),
        "headline_label": "Estimated Potential Gain",
        "hero": {
            "product": highest_gain["product"],
            "action": highest_gain["action"],
            "impact": format_money(highest_gain["expected_change"]),
            "confidence": f"{highest_gain['confidence']:.0%}",
            "explanation": highest_gain["explanation"],
            "supporting": f"{highest_gain['category']} | Risk {highest_gain['risk_label']} | Inventory {format_money(highest_gain['inventory_value'])}",
        },
        "liquidation_alert": {
            "product": liquidation_candidate["product"],
            "summary": f"{liquidation_candidate['category']} inventory with {liquidation_candidate['risk_label'].lower()} risk is tying up {format_money(liquidation_candidate['inventory_value'])}.",
            "action": liquidation_candidate["action"],
            "impact": format_money(liquidation_candidate["expected_change"]),
        },
        "health_summary": health_summary,
        "action_cards": action_cards,
        "recommendations": recommendations,
    }


def build_orchestration_context(
    results: list[Dict[str, Any]],
    source_filename: str | None = None,
) -> Dict[str, Any]:
    total_products = len(results)
    if total_products == 0:
        return {
            "active_page": "agents",
            "page_title": "AI Agents Orchestration | AssetFlow",
            "search_placeholder": "Search agents or workflows...",
            "empty_state": True,
            "source_filename": source_filename,
            "agent_cards": [],
            "workflow_steps": [],
            "workflow_details": {},
            "explanations": [],
            "top_summary": "Upload a CSV from Inventory to see the agent pipeline run on your live data.",
        }

    demand_counts = {"fast_moving": 0, "healthy": 0, "slow_moving": 0, "dead_stock": 0}
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    action_counts: Dict[str, int] = {}
    price_updates = 0

    for result in results:
        demand = result.get("agents", {}).get("demand_agent", {})
        risk = result.get("agents", {}).get("risk_agent", {})
        pricing = result.get("agents", {}).get("pricing_agent", {})
        final_decision = result.get("final_decision", {})

        demand_category = str(demand.get("category", "healthy"))
        if demand_category in demand_counts:
            demand_counts[demand_category] += 1

        risk_level = str(risk.get("level", "low"))
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1

        current_price = parse_numeric(pricing.get("current_price"), default=0.0)
        suggested_price = parse_numeric(pricing.get("suggested_price"), default=0.0)
        if round(current_price, 2) != round(suggested_price, 2):
            price_updates += 1

        action = str(final_decision.get("final_action") or final_decision.get("action") or "HOLD")
        action_counts[action] = action_counts.get(action, 0) + 1

    top_action = max(action_counts.items(), key=lambda item: item[1])[0] if action_counts else "HOLD"
    highest_risk = max(
        results,
        key=lambda item: parse_numeric(item.get("agents", {}).get("risk_agent", {}).get("risk_score"), default=-1),
    )
    strongest_demand = max(
        results,
        key=lambda item: parse_numeric(item.get("agents", {}).get("demand_agent", {}).get("demand_score"), default=-1),
    )

    workflow_steps = [
        {
            "key": "upload",
            "title": "Upload CSV",
            "subtitle": source_filename or f"{total_products} inventory rows received",
            "state": "complete",
        },
        {
            "key": "demand",
            "title": "Demand Agent",
            "subtitle": f"{demand_counts['fast_moving']} fast, {demand_counts['slow_moving']} slow, {demand_counts['dead_stock']} dead",
            "state": "complete",
        },
        {
            "key": "risk_pricing",
            "title": "Risk + Pricing",
            "subtitle": f"{risk_counts['high']} high-risk items, {price_updates} price updates suggested",
            "state": "complete",
        },
        {
            "key": "final_actions",
            "title": "Final Actions",
            "subtitle": f"Top recommendation pattern: {top_action.replace('_', ' ').title()}",
            "state": "complete",
        },
    ]

    sorted_by_demand = sorted(
        results,
        key=lambda item: parse_numeric(item.get("agents", {}).get("demand_agent", {}).get("demand_score"), default=-1),
        reverse=True,
    )
    sorted_by_risk = sorted(
        results,
        key=lambda item: parse_numeric(item.get("agents", {}).get("risk_agent", {}).get("risk_score"), default=-1),
        reverse=True,
    )
    sorted_by_confidence = sorted(
        results,
        key=lambda item: parse_numeric(item.get("final_decision", {}).get("confidence"), default=-1),
        reverse=True,
    )

    workflow_details = {
        "upload": {
            "title": "Uploaded Inventory Snapshot",
            "summary": f"{total_products} rows were received from {source_filename or 'the latest CSV upload'} and normalized for all four agents.",
            "items": [
                {
                    "label": result.get("product", "Unknown"),
                    "value": f"Price Rs. {parse_numeric(result.get('source', {}).get('price'), 0.0):,.0f} | Sales {parse_numeric(result.get('source', {}).get('sales'), 0.0):.0f} | Stock {parse_numeric(result.get('source', {}).get('stock'), 0.0):.0f}",
                }
                for result in results[:3]
            ],
        },
        "demand": {
            "title": "Demand Agent Output",
            "summary": "The demand agent classified movement patterns from sales-to-stock ratios and identified the strongest movers plus slow and dead stock.",
            "items": [
                {
                    "label": result.get("product", "Unknown"),
                    "value": f"{str(result.get('agents', {}).get('demand_agent', {}).get('category', 'healthy')).replace('_', ' ').title()} | Score {parse_numeric(result.get('agents', {}).get('demand_agent', {}).get('demand_score'), 0.0):.2f}",
                }
                for result in sorted_by_demand[:4]
            ],
        },
        "risk_pricing": {
            "title": "Risk and Pricing Output",
            "summary": "These items have the highest holding risk or the clearest pricing adjustments suggested by the project agents.",
            "items": [
                {
                    "label": result.get("product", "Unknown"),
                    "value": f"Risk {parse_numeric(result.get('agents', {}).get('risk_agent', {}).get('risk_score'), 0.0):.2f} | Suggested Rs. {parse_numeric(result.get('agents', {}).get('pricing_agent', {}).get('suggested_price'), 0.0):,.2f}",
                }
                for result in sorted_by_risk[:4]
            ],
        },
        "final_actions": {
            "title": "Final Recommended Actions",
            "summary": "The action layer combines demand, risk, and pricing into the final operational recommendation for each inventory item.",
            "items": [
                {
                    "label": result.get("product", "Unknown"),
                    "value": f"{str(result.get('final_decision', {}).get('final_action') or result.get('final_decision', {}).get('action') or 'HOLD').replace('_', ' ').title()} | Confidence {parse_numeric(result.get('final_decision', {}).get('confidence'), 0.0):.0%}",
                }
                for result in sorted_by_confidence[:4]
            ],
        },
    }

    explanations = [
        {
            "title": f"Highest Risk: {highest_risk.get('product', 'Unknown')}",
            "body": highest_risk.get("final_decision", {}).get("explanation")
            or highest_risk.get("agents", {}).get("risk_agent", {}).get("reason")
            or "No explanation available.",
            "from_label": "Risk to action",
            "to_label": str(
                highest_risk.get("final_decision", {}).get("final_action")
                or highest_risk.get("final_decision", {}).get("action")
                or "HOLD"
            ).replace("_", " ").title(),
        },
        {
            "title": f"Strongest Demand: {strongest_demand.get('product', 'Unknown')}",
            "body": strongest_demand.get("agents", {}).get("pricing_agent", {}).get("reason")
            or strongest_demand.get("agents", {}).get("demand_agent", {}).get("reason")
            or "No explanation available.",
            "from_label": str(strongest_demand.get("agents", {}).get("demand_agent", {}).get("category", "healthy")).replace("_", " ").title(),
            "to_label": str(
                strongest_demand.get("final_decision", {}).get("final_action")
                or strongest_demand.get("final_decision", {}).get("action")
                or "HOLD"
            ).replace("_", " ").title(),
        },
    ]

    agent_cards = [
        {
            "name": "Demand Agent",
            "icon": "analytics",
            "status_label": "Active",
            "status_tone": "success",
            "description": "Classifies inventory movement from the uploaded CSV using sales-to-stock demand ratios.",
            "input": f"{total_products} uploaded items",
            "output": f"{demand_counts['fast_moving']} fast moving, {demand_counts['dead_stock']} dead stock",
        },
        {
            "name": "Risk Agent",
            "icon": "warning",
            "status_label": "Active",
            "status_tone": "warning",
            "description": "Scores holding risk from current stock, sales momentum, and inventory exposure.",
            "input": "Demand categories and inventory exposure",
            "output": f"{risk_counts['high']} high-risk items flagged",
        },
        {
            "name": "Pricing Agent",
            "icon": "sell",
            "status_label": "Active",
            "status_tone": "neutral",
            "description": "Recommends price changes directly from the uploaded inventory performance signals.",
            "input": "Current price, stock, and sales",
            "output": f"{price_updates} suggested price changes",
        },
        {
            "name": "Action Agent",
            "icon": "recommend",
            "status_label": "Complete",
            "status_tone": "success",
            "description": "Turns the agent signals into a final recommended action for each uploaded product.",
            "input": "Demand, risk, and pricing outputs",
            "output": f"Top action: {top_action.replace('_', ' ').title()}",
        },
    ]

    return {
        "active_page": "agents",
        "page_title": "AI Agents Orchestration | AssetFlow",
        "search_placeholder": "Search agents or workflows...",
        "empty_state": False,
        "source_filename": source_filename,
        "agent_cards": agent_cards,
        "workflow_steps": workflow_steps,
        "workflow_details": workflow_details,
        "explanations": explanations,
        "top_summary": f"{total_products} items from {source_filename or 'the latest upload'} were analyzed through all four agents.",
    }


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/inventory", response_class=HTMLResponse)
def inventory(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/analyze_all")
def analyze_all():
    filepath = os.path.join("data", "products.csv")
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


@app.get("/analytics", response_class=HTMLResponse)
def analytics(request: Request):
    if LATEST_ANALYSIS_RESULTS:
        results = LATEST_ANALYSIS_RESULTS
        source_label = LATEST_ANALYSIS_FILENAME or "latest uploaded CSV"
    else:
        results = []
        source_label = None
    context = build_analytics_context(results)
    context["dashboard_subtitle"] = (
        f"Live metrics generated from {source_label}."
        if source_label
        else "Upload a CSV from Inventory to generate live analytics."
    )
    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context=context,
    )


@app.get("/monetization", response_class=HTMLResponse)
def monetization(request: Request):
    if LATEST_ANALYSIS_RESULTS:
        results = LATEST_ANALYSIS_RESULTS
        source_label = LATEST_ANALYSIS_FILENAME or "latest uploaded CSV"
    else:
        results = []
        source_label = None

    context = build_monetization_context(results)
    context["headline_label"] = (
        f"Estimated Potential Gain from {source_label}"
        if source_label
        else "Upload CSV to unlock recommendations"
    )
    return templates.TemplateResponse(
        request=request,
        name="monetization.html",
        context=context,
    )


@app.get("/orchestration", response_class=HTMLResponse)
def orchestration(request: Request):
    context = build_orchestration_context(LATEST_ANALYSIS_RESULTS, LATEST_ANALYSIS_FILENAME)
    return templates.TemplateResponse(
        request=request,
        name="orchestration.html",
        context=context,
    )


@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "active_page": "settings",
            "page_title": "Settings | AssetFlow",
            "search_placeholder": "Search settings...",
        },
    )


@app.get("/{page_name}")
def get_page(request: Request, page_name: str):
    if os.path.exists(f"templates/{page_name}.html"):
        return templates.TemplateResponse(
            request=request,
            name=f"{page_name}.html",
        )
    if os.path.exists(f"templates/{page_name}"):
        return templates.TemplateResponse(
            request=request,
            name=page_name,
        )

    raise HTTPException(status_code=404, detail="Page not found")
