def aggregate_decision(product: dict, demand: dict, risk: dict, pricing: dict, action: dict) -> dict:
    """
    Combines agent outputs into a final synthesized decision.
    """
    final_action = action.get("action", "hold").upper().replace("_", " ")
    
    try:
        current_price = float(pricing.get("current_price", 0.0))
        suggested_price = float(pricing.get("suggested_price", 0.0))
        sales_estimate = int(product.get("sales", 0))
    except ValueError:
        current_price = 0.0
        suggested_price = 0.0
        sales_estimate = 0
        
    price_diff = suggested_price - current_price
    
    # Adjust sales estimate based on action
    if final_action == "PROMOTE" or final_action == "LIQUIDATE":
        sales_estimate = int(sales_estimate * 1.5)
    
    expected_profit_change = price_diff * sales_estimate
    
    final_explanation = (
        f"Demand is {demand.get('category')} ({demand.get('reason')}) "
        f"Risk is {risk.get('level')} ({risk.get('reason')}) "
        f"Pricing strategy: {pricing.get('reason')} "
        f"Therefore, the recommended action is to {action.get('action', 'hold').replace('_', ' ')}."
    )

    # ===================== ✅ NEW ADDITIONS START =====================

    # 🔥 Better structured explanation
    demand_score = demand.get("demand_score", 0)
    risk_score = risk.get("risk_score", 0)
    stock = product.get("stock", 0)
    sales = product.get("sales", 0)

    enhanced_explanation = f"""
Demand category: {demand.get('category')} (score: {demand_score:.2f}) based on sales {sales} and stock {stock}.
Risk level: {risk.get('level')} (score: {risk_score:.2f}).

Recommended action: {final_action}.

Estimated profit impact: Rs. {expected_profit_change:.0f}.
"""

    # Add reasoning based on action
    if final_action == "INCREASE PRICE":
        enhanced_explanation += "Strong demand allows a safe price increase to maximize margins."
    elif final_action == "PROMOTE":
        enhanced_explanation += "Lower demand suggests promotions to improve sales velocity."
    elif final_action == "LIQUIDATE":
        enhanced_explanation += "High risk and low demand indicate immediate clearance is required."
    elif final_action == "HOLD":
        enhanced_explanation += "Balanced demand and risk suggest maintaining current pricing."

    enhanced_explanation = enhanced_explanation.strip()

    # 🔥 Urgency logic
    if risk.get("level") == "high":
        urgency = "Immediate"
    elif demand.get("category") == "fast_moving":
        urgency = "Opportunity"
    else:
        urgency = "Monitor"

    # 🔥 Timeline
    timeline = "7 days" if urgency == "Immediate" else "14 days"

    # 🔥 Alternatives (multi-strategy)
    alternatives = []

    if final_action == "INCREASE PRICE":
        alternatives = [
            {"action": "Bundle Offer", "impact": round(expected_profit_change * 0.6, 2)},
            {"action": "Hold", "impact": 0}
        ]
    elif final_action == "PROMOTE":
        alternatives = [
            {"action": "Discount", "impact": round(expected_profit_change * 0.8, 2)},
            {"action": "Bundle", "impact": round(expected_profit_change * 0.5, 2)}
        ]
    elif final_action == "LIQUIDATE":
        alternatives = [
            {"action": "Heavy Discount", "impact": round(expected_profit_change * 0.7, 2)},
            {"action": "Bundle Clearance", "impact": round(expected_profit_change * 0.5, 2)}
        ]

    # ===================== ✅ NEW ADDITIONS END =====================

    return {
        "final_action": final_action,
        "final_price": suggested_price,
        "expected_profit": round(price_diff, 2),
        "expected_profit_change": round(expected_profit_change, 2),
        "confidence": action.get("confidence"),
        "explanation": final_explanation,

        # ✅ NEW FIELDS
        "enhanced_explanation": enhanced_explanation,
        "urgency": urgency,
        "timeline": timeline,
        "alternatives": alternatives
    }