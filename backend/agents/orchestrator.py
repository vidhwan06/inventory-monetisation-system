import pandas as pd
from typing import Dict

from agents.demand_agent import demand_agent
from agents.dead_stock_agent import DeadStockDetectionAgent
from agents.pricing_agent import pricing_agent
from agents.decision_agent import decision_agent


# -----------------------------
# HELPER: Convert DF → Product List
# -----------------------------

def prepare_products(df: pd.DataFrame):

    products = []

    for _, row in df.iterrows():
        products.append({
            "product_name": row["item_name"],
            "stock_quantity": int(row["stock"]),
            "units_sold": int(row["sales"]),
            "product_price": float(row["price"]),
            "days_in_stock": int(row["last_sold_days"])
        })

    return products


# -----------------------------
# MAIN ORCHESTRATOR (BRAIN)
# -----------------------------

def run_multi_agent_system(df: pd.DataFrame) -> Dict:

    if df is None or df.empty:
        return {
            "error": "No data provided"
        }

    # 🔹 STEP 0: Limit rows (IMPORTANT for Gemini)
    df = df.head(10)

    # -----------------------------
    # STEP 1: DEMAND ANALYSIS
    # -----------------------------
    demand_output = demand_agent(df)

    # -----------------------------
    # STEP 2: DEAD STOCK ANALYSIS
    # -----------------------------
    products = prepare_products(df)

    dead_agent = DeadStockDetectionAgent()
    dead_stock_output = dead_agent.analyze_inventory(products)

    # -----------------------------
    # STEP 3: PRICING OPTIMIZATION
    # -----------------------------
    pricing_output = pricing_agent(demand_output)

    # -----------------------------
    # STEP 4: DECISION MAKING
    # -----------------------------
    decision_output = decision_agent(demand_output, pricing_output)

    # -----------------------------
    # FINAL UNIFIED OUTPUT
    # -----------------------------
    return {
        "demand_analysis": demand_output,
        "dead_stock_analysis": dead_stock_output,
        "pricing": pricing_output,
        "decisions": decision_output
    }