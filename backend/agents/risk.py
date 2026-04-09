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


def risk_agent(product: dict) -> dict:
    """
    Dead Stock Detection Agent.
    Uses the dataset reference date and the product's last sold date to identify dead stock.
    """
    sales = max(_to_int(product.get("sales", 0)), 0)
    stock = max(_to_float(product.get("stock", 0.0)), 0.0)
    price = max(_to_float(product.get("price", 0.0)), 0.0)
    days_since_last_sale = product.get("days_since_last_sale")
    reference_date = product.get("reference_date")
    last_sold_date = product.get("last_sold_date")
    sales_data_present = bool(product.get("sales_data_present", False))

    has_stale_sale = isinstance(days_since_last_sale, int) and days_since_last_sale > 60
    is_dead_stock = has_stale_sale or (sales_data_present and sales == 0)
    inventory_value = round(stock * price, 2)

    if is_dead_stock:
        risk_score = 0.95 if stock > 0 else 0.8
        level = "high"
        inventory_status = "dead_stock"
        if sales_data_present and sales == 0:
            reason = (
                "Marked as dead stock because Units Sold (Last 30 Days) is 0. "
                f"Inventory exposure is Rs. {inventory_value:.2f}."
            )
        else:
            reason = (
                f"Marked as dead stock because the item has not sold for {days_since_last_sale} days, "
                "which is beyond the 60-day threshold."
            )
    elif sales < 10 or stock > max(sales * 6, 1):
        risk_score = 0.55
        level = "medium"
        inventory_status = "active"
        if sales_data_present:
            reason = (
                f"Active item with low recent movement: {sales} units sold in 30 days and "
                f"{stock:.0f} units still in stock."
            )
        else:
            reason = (
                "Active item with incomplete sales history in the uploaded CSV. "
                "It was not marked as dead stock because no explicit zero-sales signal was provided."
            )
    else:
        risk_score = 0.2
        level = "low"
        inventory_status = "active"
        reason = (
            f"Active item with healthy recent movement: {sales} units sold in 30 days and "
            f"{stock:.0f} units in stock."
        )

    return {
        "risk_score": round(risk_score, 2),
        "level": level,
        "inventory_status": inventory_status,
        "is_dead_stock": is_dead_stock,
        "days_since_last_sale": days_since_last_sale,
        "last_sold_date": last_sold_date,
        "reference_date": reference_date,
        "reason": reason,
    }
