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
    
    return {
        "final_action": final_action,
        "final_price": suggested_price,
        "expected_profit": round(price_diff, 2),
        "expected_profit_change": round(expected_profit_change, 2),
        "confidence": action.get("confidence"),
        "explanation": final_explanation
    }
