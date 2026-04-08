def demand_agent(product: dict):
    """
    Evaluates the demand of a product based on its sales and stock.
    Returns demand_score, category, and reason.
    """
    try:
        sales = float(product.get('sales', 0))
        stock = float(product.get('stock', 1))
    except ValueError:
        sales = 0
        stock = 1
        
    if stock <= 0:
        return {"demand_score": 1.0, "category": "fast_moving", "reason": "Out of stock, pure demand"}
        
    sales_ratio = sales / stock
    
    if sales_ratio >= 0.8:
        demand_score = 0.9
        category = "fast_moving"
        reason = "High sales compared to current stock."
    elif sales_ratio >= 0.4:
        demand_score = 0.6
        category = "healthy"
        reason = "Moderate, steady demand."
    elif sales_ratio >= 0.1:
        demand_score = 0.3
        category = "slow_moving"
        reason = "Low sales volume."
    else:
        demand_score = 0.1
        category = "dead_stock"
        reason = "Extremely low or zero sales."
        
    return {
        "demand_score": demand_score,
        "category": category,
        "reason": reason
    }
