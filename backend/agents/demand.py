def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def demand_agent(product: dict) -> dict:
    """
    Analyze demand from the actual sales-to-stock ratio.
    Returns demand_score, category, and reason.
    """
    sales = max(_to_float(product.get("sales", 0.0)), 0.0)
    stock = max(_to_float(product.get("stock", 0.0)), 0.0)

    if stock <= 0:
        demand_score = 1.0 if sales > 0 else 0.0
    else:
        demand_score = sales / stock

    demand_score = round(demand_score, 2)

    if demand_score > 0.7:
        category = "fast_moving"
        reason = (
            f"Demand ratio is {demand_score} from sales {sales:.2f} and stock {stock:.2f}, "
            "indicating strong inventory turnover."
        )
    elif demand_score >= 0.3:
        category = "healthy"
        reason = (
            f"Demand ratio is {demand_score} from sales {sales:.2f} and stock {stock:.2f}, "
            "showing balanced movement."
        )
    elif demand_score >= 0.1:
        category = "slow_moving"
        reason = (
            f"Demand ratio is {demand_score} from sales {sales:.2f} and stock {stock:.2f}, "
            "which suggests slower sell-through."
        )
    else:
        category = "dead_stock"
        reason = (
            f"Demand ratio is {demand_score} from sales {sales:.2f} and stock {stock:.2f}, "
            "showing very weak movement."
        )

    return {
        "demand_score": demand_score,
        "category": category,
        "reason": reason,
    }
