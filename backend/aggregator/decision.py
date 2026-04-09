def aggregate_decision(product: dict, demand: dict, risk: dict, pricing: dict, action: dict) -> dict:
    """
    Combines agent outputs into a final synthesized decision.
    """
    final_action = action.get("action", "hold").upper().replace("_", " ")

    try:
        current_price = float(pricing.get("current_price", 0.0))
        suggested_price = float(pricing.get("suggested_price", 0.0))
        sales_estimate = int(product.get("sales", 0))
    except (TypeError, ValueError):
        current_price = 0.0
        suggested_price = 0.0
        sales_estimate = 0

    price_diff = suggested_price - current_price
    if final_action in {"PROMOTE", "LIQUIDATE"}:
        sales_estimate = int(sales_estimate * 1.25)

    expected_profit_change = price_diff * sales_estimate
    demand_band = demand.get("demand_band", "unknown")
    days_since_last_sale = risk.get("days_since_last_sale")
    dead_stock_label = "dead stock" if risk.get("is_dead_stock") else "active inventory"

    final_explanation = (
        f"Demand is {demand_band} ({demand.get('reason')}) while the dead stock detector labels this item as "
        f"{dead_stock_label} ({risk.get('reason')}). Pricing strategy: {pricing.get('reason')} "
        f"Therefore, the recommended action is to {action.get('action', 'hold').replace('_', ' ')}."
    )

    enhanced_explanation = (
        f"Units sold in last 30 days: {product.get('sales', 0)}. "
        f"Days since last sale: {days_since_last_sale if days_since_last_sale is not None else 'unknown'}. "
        f"Demand band: {demand_band}. Risk level: {risk.get('level')}. "
        f"Recommended action: {final_action}. Estimated profit impact: Rs. {expected_profit_change:.0f}."
    )

    if risk.get("is_dead_stock"):
        urgency = "Immediate"
        timeline = "7 days"
    elif demand_band == "high":
        urgency = "Opportunity"
        timeline = "14 days"
    else:
        urgency = "Monitor"
        timeline = "21 days"

    alternatives = []
    if final_action == "INCREASE PRICE":
        alternatives = [
            {"action": "Hold", "impact": 0},
            {"action": "Bundle Offer", "impact": round(expected_profit_change * 0.5, 2)},
        ]
    elif final_action == "PROMOTE":
        alternatives = [
            {"action": "Discount", "impact": round(expected_profit_change * 0.8, 2)},
            {"action": "Bundle", "impact": round(expected_profit_change * 0.4, 2)},
        ]
    elif final_action == "LIQUIDATE":
        alternatives = [
            {"action": "Heavy Discount", "impact": round(expected_profit_change * 0.7, 2)},
            {"action": "Bundle Clearance", "impact": round(expected_profit_change * 0.45, 2)},
        ]

    return {
        "final_action": final_action,
        "action": final_action,
        "final_price": suggested_price,
        "expected_profit": round(price_diff, 2),
        "expected_profit_change": round(expected_profit_change, 2),
        "confidence": action.get("confidence"),
        "explanation": final_explanation,
        "enhanced_explanation": enhanced_explanation,
        "urgency": urgency,
        "timeline": timeline,
        "alternatives": alternatives,
    }
