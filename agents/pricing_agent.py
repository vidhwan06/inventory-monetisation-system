import json
import logging
from typing import Dict

from agents.gemini_config import get_gemini_model

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PricingAgent")

# Gemini model (shared)
model = get_gemini_model()

# -----------------------------
# CONFIG
# -----------------------------

BASE_PRICE = 100.0
PRICE_FLOOR = 10.0
PRICE_CEILING = 300.0

# Discount ranges
DISCOUNT_RULES = {
    "dead_stock": (30, 50),
    "slow_moving": (10, 25),
    "fast_moving": (0, 5),
}


# -----------------------------
# HEURISTIC BASELINE
# -----------------------------

def heuristic_pricing(inventory_data: Dict):

    dead = set(inventory_data.get("dead_stock", []))
    fast = set(inventory_data.get("fast_moving", []))
    slow = set(inventory_data.get("slow_moving", []))
    stock_levels = inventory_data.get("stock_levels", {})

    all_items = dead | fast | slow | set(stock_levels.keys())

    prices = {}
    discounts = {}

    for item in all_items:

        price = BASE_PRICE
        stock = stock_levels.get(item, 50)

        # Discount band
        if item in dead:
            dmin, dmax = DISCOUNT_RULES["dead_stock"]
        elif item in slow:
            dmin, dmax = DISCOUNT_RULES["slow_moving"]
        else:
            dmin, dmax = DISCOUNT_RULES["fast_moving"]

        discount = (dmin + dmax) // 2

        # Adjust based on stock
        if item in fast and stock < 20:
            price *= 1.2
        elif item in (dead | slow) and stock > 100:
            price *= 0.8

        # Apply discount
        price = price * (1 - discount / 100)

        # Clamp values
        price = max(PRICE_FLOOR, min(price, PRICE_CEILING))

        prices[item] = round(price, 2)
        discounts[item] = discount

    return prices, discounts


# -----------------------------
# GEMINI REFINEMENT
# -----------------------------

def refine_with_gemini(inventory_data, prices, discounts):

    try:
        prompt = f"""
You are a revenue optimization AI.

Given inventory and baseline pricing, refine pricing for maximum revenue.

RULES:
- Dead stock → heavy discount (30–50%)
- Slow moving → moderate discount (10–25%)
- Fast moving → minimal discount or slight price increase
- Low stock + fast moving → increase price
- High stock + low demand → reduce price

Return ONLY JSON:

{{
  "recommended_prices": {{}},
  "discounts": {{}},
  "strategy_summary": ""
}}

INVENTORY:
{json.dumps(inventory_data)}

BASELINE:
{json.dumps({"prices": prices, "discounts": discounts})}
"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Clean markdown if exists
        if raw.startswith("```"):
            raw = "\n".join(line for line in raw.splitlines() if "```" not in line)

        parsed = json.loads(raw)

        # Safety checks
        parsed_prices = {
            k: round(max(PRICE_FLOOR, min(float(v), PRICE_CEILING)), 2)
            for k, v in parsed.get("recommended_prices", {}).items()
        }

        parsed_discounts = {
            k: int(str(v).replace("%", "").strip())
            for k, v in parsed.get("discounts", {}).items()
        }

        return {
            "recommended_prices": parsed_prices,
            "discounts": parsed_discounts,
            "strategy_summary": parsed.get("strategy_summary", "")
        }

    except Exception as e:
        logger.error(f"Gemini failed: {e}")
        return None


# -----------------------------
# MAIN AGENT
# -----------------------------

def pricing_agent(inventory_data: Dict) -> Dict:

    if not inventory_data:
        return {
            "recommended_prices": {},
            "discounts": {},
            "strategy_summary": "No data"
        }

    # Step 1: heuristic baseline
    prices, discounts = heuristic_pricing(inventory_data)

    # Step 2: Gemini refinement
    refined = refine_with_gemini(inventory_data, prices, discounts)

    if refined:
        return refined

    # Step 3: fallback
    logger.warning("Using fallback pricing")

    return {
        "recommended_prices": prices,
        "discounts": discounts,
        "strategy_summary": "Rule-based pricing applied"
    }