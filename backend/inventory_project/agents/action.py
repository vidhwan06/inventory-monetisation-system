def action_agent(demand: dict, risk: dict):
    """
    Determines the overarching action plan based on demand and risk context.
    Returns action, confidence, and reason.
    """
    demand_category = demand.get("category")
    risk_level = risk.get("level")
    
    if demand_category == "fast_moving" and risk_level == "low":
        action = "increase_price"
        confidence = 0.90
        reason = "Product is moving fast with low risk, prime for margin expansion."
    elif demand_category == "healthy":
        action = "hold"
        confidence = 0.85
        reason = "Normal operations, no immediate action required."
    elif demand_category == "slow_moving" or risk_level == "medium":
        action = "promote"
        confidence = 0.75
        reason = "Sales are lagging or risk is elevated; marketing promotion is needed."
    else: # dead_stock or high risk
        action = "liquidate"
        confidence = 0.95
        reason = "High-risk dead stock; must extract remaining value immediately."

    return {
        "action": action,
        "confidence": confidence,
        "reason": reason
    }
