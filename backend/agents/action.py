def action_agent(demand: dict, risk: dict) -> dict:
    """
    Decide the high-level action from the demand category.
    Returns action, confidence, and reason.
    """
    demand_cat = demand.get("category")

    if demand_cat == "fast_moving":
        action = "increase_price"
        confidence = 0.90
        reason = "Fast-moving demand supports a price increase to improve margin."
    elif demand_cat == "healthy":
        action = "hold"
        confidence = 0.80
        reason = "Healthy demand supports maintaining the current inventory strategy."
    elif demand_cat == "slow_moving":
        action = "promote"
        confidence = 0.85
        reason = "Slow-moving demand benefits from promotion to increase sell-through."
    else:
        action = "liquidate"
        confidence = 0.95 if risk.get("level") == "high" else 0.90
        reason = "Dead stock should be liquidated to free capital and storage capacity."

    return {
        "action": action,
        "confidence": confidence,
        "reason": reason,
    }
