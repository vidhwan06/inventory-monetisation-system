def risk_agent(product: dict):
    """
    Evaluates the risk of holding a product based on stock and sales numbers.
    Returns risk_score, level, and reason.
    """
    try:
        stock = float(product.get('stock', 0))
        sales = float(product.get('sales', 0))
    except ValueError:
        stock = 0
        sales = 0
    
    if stock > 500 and sales < 50:
        risk_score = 0.9
        level = "high"
        reason = "Massive overstock with poor sales."
    elif stock > 100 and sales < 20:
        risk_score = 0.7
        level = "high"
        reason = "Significant stock sitting idle."
    elif stock > 50 and sales < 50:
        risk_score = 0.4
        level = "medium"
        reason = "Moderate risk of inventory aging."
    else:
        risk_score = 0.1
        level = "low"
        reason = "Stock levels are well managed compared to sales."
        
    return {
        "risk_score": risk_score,
        "level": level,
        "reason": reason
    }
