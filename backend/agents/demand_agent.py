import json
import logging
from typing import Dict

from agents.gemini_config import get_gemini_model

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DemandAgent")

# Shared Gemini model
model = get_gemini_model()

# -----------------------------
# CONFIG
# -----------------------------

FAST_THRESHOLD = 15
SLOW_THRESHOLD = 5
LOW_STOCK_THRESHOLD = 20


# -----------------------------
# RULE-BASED ANALYSIS
# -----------------------------

def analyze_demand_rule_based(df):

    fast_moving = []
    slow_moving = []
    dead_stock = []
    stock_levels = {}

    for _, row in df.iterrows():

        item = row["item_name"]
        sales = int(row["sales"])
        stock = int(row["stock"])

        stock_levels[item] = stock

        if sales == 0:
            dead_stock.append(item)
        elif sales >= FAST_THRESHOLD:
            fast_moving.append(item)
        elif sales <= SLOW_THRESHOLD:
            slow_moving.append(item)

    return {
        "dead_stock": dead_stock,
        "fast_moving": fast_moving,
        "slow_moving": slow_moving,
        "stock_levels": stock_levels
    }


# -----------------------------
# GEMINI ANALYSIS
# -----------------------------

def refine_with_gemini(df, base_output):

    try:
        data_sample = df.head(10).to_dict(orient="records")

        prompt = f"""
You are a demand analysis AI.

Analyze the inventory data and refine classification.

Return ONLY JSON in this format:
{{
  "dead_stock": [],
  "fast_moving": [],
  "slow_moving": [],
  "observations": []
}}

DATA:
{json.dumps(data_sample)}

BASE CLASSIFICATION:
{json.dumps(base_output)}

Rules:
- Dead stock = no sales
- Fast moving = high demand
- Slow moving = low demand
- Add short business observations
"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Clean markdown if exists
        if raw.startswith("```"):
            raw = "\n".join(line for line in raw.splitlines() if "```" not in line)

        parsed = json.loads(raw)

        return parsed

    except Exception as e:
        logger.error(f"Gemini failed: {e}")
        return None


# -----------------------------
# MAIN AGENT FUNCTION
# -----------------------------

def demand_agent(df) -> Dict:

    if df is None or df.empty:
        return {
            "dead_stock": [],
            "fast_moving": [],
            "slow_moving": [],
            "stock_levels": {},
            "observations": ["No data available"]
        }

    # Step 1: rule-based
    base_output = analyze_demand_rule_based(df)

    # Step 2: Gemini refinement
    refined = refine_with_gemini(df, base_output)

    if refined:
        return {
            "dead_stock": refined.get("dead_stock", base_output["dead_stock"]),
            "fast_moving": refined.get("fast_moving", base_output["fast_moving"]),
            "slow_moving": refined.get("slow_moving", base_output["slow_moving"]),
            "stock_levels": base_output["stock_levels"],
            "observations": refined.get("observations", [])
        }

    # Step 3: fallback
    logger.warning("Using fallback demand analysis")

    return {
        **base_output,
        "observations": ["Rule-based demand classification applied"]
    }