import logging
from dataclasses import asdict, dataclass
from typing import Optional, List, Dict

from agents.gemini_config import get_gemini_model

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DeadStockAgent")

# Gemini model (shared)
model = get_gemini_model()

# -----------------------------
# DATA MODELS
# -----------------------------

@dataclass
class ProductInput:
    product_name: str
    stock_quantity: int
    units_sold: int
    product_price: float
    days_in_stock: int


@dataclass
class ProductResult:
    product_name: str
    stock_quantity: int
    units_sold: int
    days_in_stock: int
    sell_through_rate: float
    blocked_capital: float
    inventory_status: str
    risk_score: float
    gemini_insight: str


# -----------------------------
# AGENT
# -----------------------------

class DeadStockDetectionAgent:

    def __init__(self, slow_threshold: float = 0.2, dead_days: int = 90):
        self.slow_threshold = slow_threshold
        self.dead_days = dead_days

    # -----------------------------
    # MAIN FUNCTION
    # -----------------------------
    def analyze_inventory(self, products: List[Dict]) -> Dict:

        results = []

        total_blocked = 0

        # First pass: compute metrics
        for p in products:

            stock = p["stock_quantity"]
            sold = p["units_sold"]
            price = p["product_price"]
            days = p["days_in_stock"]

            # Sell-through rate
            if stock + sold == 0:
                str_rate = 0
            else:
                str_rate = sold / (stock + sold)

            blocked = stock * price
            total_blocked += blocked

            # Classification
            if sold == 0 and stock > 0:
                status = "DEAD STOCK"
            elif str_rate < self.slow_threshold:
                status = "SLOW MOVING"
            else:
                status = "HEALTHY"

            # Risk score
            base = {"DEAD STOCK": 0.7, "SLOW MOVING": 0.4, "HEALTHY": 0.1}[status]
            age_penalty = min(days / self.dead_days, 1) * 0.2
            risk = min(base + age_penalty, 1.0)

            # Gemini Insight
            insight = self.generate_insight(p, str_rate, blocked, status)

            results.append({
                "product_name": p["product_name"],
                "stock_quantity": stock,
                "units_sold": sold,
                "days_in_stock": days,
                "sell_through_rate": round(str_rate, 3),
                "blocked_capital": round(blocked, 2),
                "inventory_status": status,
                "risk_score": round(risk, 2),
                "gemini_insight": insight
            })

        # Summary
        summary = {
            "total_products": len(results),
            "dead_stock": sum(1 for r in results if r["inventory_status"] == "DEAD STOCK"),
            "slow_moving": sum(1 for r in results if r["inventory_status"] == "SLOW MOVING"),
            "healthy": sum(1 for r in results if r["inventory_status"] == "HEALTHY"),
            "total_blocked_capital": round(total_blocked, 2)
        }

        return {
            "results": results,
            "summary": summary
        }

    # -----------------------------
    # GEMINI INSIGHT
    # -----------------------------
    def generate_insight(self, product, str_rate, blocked, status):

        try:
            prompt = f"""
You are an inventory analysis AI.

Analyze the product below and explain its inventory health.

Product: {product['product_name']}
Stock: {product['stock_quantity']}
Sales: {product['units_sold']}
Days in stock: {product['days_in_stock']}
Sell-through rate: {round(str_rate*100,1)}%
Blocked capital: ${blocked}
Status: {status}

Explain in 2-3 concise sentences:
- Why this product is in this state
- Risk level
- Key issue

NO strategies. Only analysis.
"""

            response = model.generate_content(prompt)

            return response.text.strip()

        except Exception as e:
            logger.error(f"Gemini failed: {e}")
            return f"{status} item with {blocked} blocked capital."