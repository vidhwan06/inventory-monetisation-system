def aggregate_decision(product: dict, demand: dict, risk: dict, pricing: dict, action: dict):
    """
    Combines outputs from all agents to form a final synthesized business decision.
    """
    final_action = action.get("action", "unknown").upper()
    final_price = pricing.get("suggested_price", product.get("price"))
    
    try:
        current_price = float(product.get("price", 0))
        stock = float(product.get("stock", 0))
    except ValueError:
        current_price = 0
        stock = 0

    # Simple expected profit change logic assuming half of the stock clears at the new price difference
    price_diff = final_price - current_price
    expected_profit_change = round(price_diff * stock * 0.5, 2)
    
    # Calculate a simple average confidence based on individual agent signals
    demand_score = demand.get("demand_score", 0.5)
    risk_inverse = 1.0 - risk.get("risk_score", 0.5)
    action_confidence = action.get("confidence", 0.5)
    avg_confidence = (demand_score + risk_inverse + action_confidence) / 3.0
    
    explanation = (
        f"Based on a '{demand.get('category', 'unknown')}' demand category and '{risk.get('level', 'unknown')}' risk profile, "
        f"the final recommendation is to {final_action}. "
        f"Pricing should be adjusted to ${final_price} (includes {pricing.get('discount', 0)}% discount). "
        f"Reasoning summary - Demand: {demand.get('reason')} | Risk: {risk.get('reason')} | "
        f"Pricing: {pricing.get('reason')} | Action: {action.get('reason')}"
    )
    
    return {
        "final_action": final_action,
        "final_price": final_price,
        "expected_profit_change": expected_profit_change,
        "confidence": round(avg_confidence, 2),
        "explanation": explanation
    }
