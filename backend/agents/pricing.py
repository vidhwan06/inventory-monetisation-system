def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def pricing_agent(product: dict) -> dict:
    """
    Revenue Optimization Agent.
    Recommends price actions from cleaned sales and recency signals without mutating the input record.
    """
    current_price = max(_to_float(product.get("price", 0.0)), 0.0)
    sales = max(_to_int(product.get("sales", 0)), 0)
    days_since_last_sale = product.get("days_since_last_sale")

    stale_inventory = isinstance(days_since_last_sale, int) and days_since_last_sale > 60

    if sales > 50 and (days_since_last_sale is None or days_since_last_sale <= 14):
        suggested_price = current_price * 1.08
        discount = 0.0
        reason = "High recent demand supports an 8% price increase to improve margin."
    elif sales >= 10 and not stale_inventory:
        suggested_price = current_price
        discount = 0.0
        reason = "Steady demand supports holding the current price."
    elif stale_inventory or sales == 0:
        suggested_price = current_price * 0.75
        discount = 25.0
        reason = "Dead stock needs a deeper 25% markdown to recover cash faster."
    else:
        suggested_price = current_price * 0.9
        discount = 10.0
        reason = "Low-demand inventory benefits from a 10% discount to improve sell-through."

    return {
        "current_price": round(current_price, 2),
        "suggested_price": round(suggested_price, 2),
        "discount": round(discount, 2),
        "reason": reason,
    }
