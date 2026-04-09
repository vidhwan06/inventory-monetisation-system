def action_agent(demand: dict, risk: dict) -> dict:
    """
    Liquidation Strategy Agent.
    Combines demand and dead-stock risk into the final operational move.
    """
    demand_band = demand.get("demand_band")
    is_dead_stock = bool(risk.get("is_dead_stock"))
    risk_level = risk.get("level")

    if is_dead_stock:
        action = "liquidate"
        confidence = 0.95
        reason = "Dead stock should be cleared quickly to free capital and storage."
    elif demand_band == "high" and risk_level == "low":
        action = "increase_price"
        confidence = 0.88
        reason = "High demand with low risk supports a margin-focused price increase."
    elif demand_band == "medium":
        action = "hold"
        confidence = 0.82
        reason = "Medium demand and active movement support maintaining the current strategy."
    else:
        action = "promote"
        confidence = 0.8
        reason = "Low demand but active inventory should be promoted before liquidation."

    return {
        "action": action,
        "confidence": confidence,
        "reason": reason,
    }
