def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pricing_agent(product: dict) -> dict:
    """
    Adjust price dynamically from the sales-to-stock demand ratio.
    Returns current_price, suggested_price, discount, and reason.
    """
    current_price = max(_to_float(product.get("price", 0.0)), 0.0)
    sales = max(_to_float(product.get("sales", 0.0)), 0.0)
    stock = max(_to_float(product.get("stock", 0.0)), 0.0)

    if stock <= 0:
        demand_ratio = 1.0 if sales > 0 else 0.0
    else:
        demand_ratio = sales / stock

    if demand_ratio > 0.7:
        suggested_price = current_price * 1.10
        discount = 0.0
        reason = (
            f"Demand ratio is {demand_ratio:.2f}, so price increases by 10% from "
            f"{current_price:.2f} to strengthen margin."
        )
    elif demand_ratio < 0.3:
        suggested_price = current_price * 0.80
        discount = 20.0
        reason = (
            f"Demand ratio is {demand_ratio:.2f}, so price decreases by 20% from "
            f"{current_price:.2f} to improve movement."
        )
    else:
        suggested_price = current_price
        discount = 0.0
        reason = (
            f"Demand ratio is {demand_ratio:.2f}, so current pricing remains appropriate."
        )

    return {
        "current_price": round(current_price, 2),
        "suggested_price": round(suggested_price, 2),
        "discount": round(discount, 2),
        "reason": reason,
    }
