def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def demand_agent(product: dict) -> dict:
    """
    Demand Analysis Agent.
    Classifies demand from Units Sold (Last 30 Days) using explicit business thresholds.
    """
    sales = max(_to_int(product.get("sales", 0)), 0)

    if sales > 50:
        demand_score = 0.9
        demand_band = "high"
        category = "fast_moving"
        reason = f"High demand because Units Sold (Last 30 Days) is {sales}, above 50."
    elif sales >= 10:
        demand_score = 0.6
        demand_band = "medium"
        category = "healthy"
        reason = f"Medium demand because Units Sold (Last 30 Days) is {sales}, within 10 to 50."
    else:
        demand_score = 0.25
        demand_band = "low"
        category = "slow_moving"
        reason = f"Low demand because Units Sold (Last 30 Days) is {sales}, below 10."

    return {
        "demand_score": demand_score,
        "demand_band": demand_band,
        "category": category,
        "reason": reason,
    }
