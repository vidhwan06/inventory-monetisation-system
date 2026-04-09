def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def risk_agent(product: dict) -> dict:
    """
    Analyze holding risk as the inverse of the sales-to-stock demand ratio.
    Returns risk_score, level, and reason.
    """
    sales = max(_to_float(product.get("sales", 0.0)), 0.0)
    stock = max(_to_float(product.get("stock", 0.0)), 0.0)
    price = max(_to_float(product.get("price", 0.0)), 0.0)

    if stock <= 0:
        demand_ratio = 1.0 if sales > 0 else 0.0
    else:
        demand_ratio = sales / stock

    demand_ratio = max(0.0, min(demand_ratio, 1.0))
    risk_score = round(1 - demand_ratio, 2)
    inventory_value = round(stock * price, 2)

    if risk_score > 0.7:
        level = "high"
        reason = (
            f"Risk is high because demand ratio is {demand_ratio:.2f}, leaving a risk score of "
            f"{risk_score}. Inventory exposure is ${inventory_value}."
        )
    elif risk_score >= 0.4:
        level = "medium"
        reason = (
            f"Risk is medium because demand ratio is {demand_ratio:.2f}, producing a risk score of "
            f"{risk_score}. Inventory exposure is ${inventory_value}."
        )
    else:
        level = "low"
        reason = (
            f"Risk is low because demand ratio is {demand_ratio:.2f}, producing a risk score of "
            f"{risk_score}. Inventory exposure is ${inventory_value}."
        )

    return {
        "risk_score": risk_score,
        "level": level,
        "reason": reason,
    }
