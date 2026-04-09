import json
import logging
from typing import Dict

from agents.gemini_config import get_gemini_model

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DecisionAgent")

# Shared Gemini model
model = get_gemini_model()

# -----------------------------
# RULE-BASED DECISION LOGIC
# -----------------------------

def rule_based_decision(inventory_data: Dict, pricing_data: Dict):

    decisions = []

    dead = set(inventory_data.get("dead_stock", []))
    slow = set(inventory_data.get("slow_moving", []))
    fast = set(inventory_data.get("fast_moving", []))

    discounts = pricing_data.get("discounts", {})

    all_items = dead | slow | fast

    for item in all_items:

        discount = discounts.get(item, 0)

        if item in dead:
            action = "LIQUIDATE"
            reason = "Dead stock with no demand"
        elif item in slow:
            if discount >= 30:
                action = "CLEAR STOCK"
                reason = "High discount applied to slow-moving item"
            else:
                action = "PROMOTE"
                reason = "Increase visibility and moderate discounts"
        elif item in fast:
            if discount <= 5:
                action = "INCREASE PRICE"
                reason = "High demand with low discount"
            else:
                action = "OPTIMIZE PRICE"
                reason = "Adjust pricing carefully for revenue"
        else:
            action = "HOLD"
            reason = "Stable inventory"

        decisions.append({
            "item": item,
            "action": action,
            "reason": reason
        })

    return decisions


# -----------------------------
# GEMINI REFINEMENT
# -----------------------------

def refine_with_gemini(inventory_data, pricing_data, base_decisions):

    try:
        prompt = f"""
You are a business decision AI.

Given inventory data, pricing strategy, and initial decisions,
refine and improve the final decisions.

Return ONLY JSON in this format:

{{
  "decisions": [
    {{
      "item": "",
      "action": "",
      "reason": ""
    }}
  ],
  "summary": ""
}}

RULES:
- Dead stock → LIQUIDATE
- Slow moving → PROMOTE or CLEAR STOCK
- Fast moving → INCREASE PRICE or OPTIMIZE
- Keep reasoning short and business-focused

INVENTORY:
{json.dumps(inventory_data)}

PRICING:
{json.dumps(pricing_data)}

BASE DECISIONS:
{json.dumps(base_decisions)}
"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Remove markdown if present
        if raw.startswith("```"):
            raw = "\n".join(line for line in raw.splitlines() if "```" not in line)

        parsed = json.loads(raw)

        return parsed

    except Exception as e:
        logger.error(f"Gemini failed: {e}")
        return None


# -----------------------------
# MAIN AGENT
# -----------------------------

def decision_agent(inventory_data: Dict, pricing_data: Dict) -> Dict:

    if not inventory_data:
        return {
            "decisions": [],
            "summary": "No data available"
        }

    # Step 1: rule-based decisions
    base_decisions = rule_based_decision(inventory_data, pricing_data)

    # Step 2: Gemini refinement
    refined = refine_with_gemini(inventory_data, pricing_data, base_decisions)

    if refined:
        return {
            "decisions": refined.get("decisions", base_decisions),
            "summary": refined.get("summary", "AI-enhanced decision making")
        }

    # Step 3: fallback
    logger.warning("Using fallback decisions")

    return {
        "decisions": base_decisions,
        "summary": "Rule-based decisions applied"
    }