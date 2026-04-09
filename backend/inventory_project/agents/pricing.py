def pricing_agent(product: dict):
    """
    Determines suggested pricing and discount based on product velocity.
    Returns current_price, suggested_price, discount, and reason.
    """
    try:
        current_price = float(product.get('price', 0))
        sales = float(product.get('sales', 0))
        stock = float(product.get('stock', 1))
    except ValueError:
        current_price = 0
        sales = 0
        stock = 1
        
    safe_stock = max(stock, 1)
    sales_ratio = sales / safe_stock

    if sales_ratio >= 0.8:
        suggested_price = current_price * 1.05
        discount = 0.0
        reason = "High product demand allows for a 5% margin increase."
    elif sales_ratio >= 0.4:
        suggested_price = current_price
        discount = 0.0
        reason = "Healthy demand, maintain current pricing."
    elif sales_ratio >= 0.1:
        suggested_price = current_price * 0.9
        discount = 10.0
        reason = "Slow movement suggests a 10% discount to stimulate sales."
    else:
        suggested_price = current_price * 0.8
        discount = 20.0
        reason = "Dead stock needs aggressive 20% discount."

    return {
        "current_price": current_price,
        "suggested_price": round(suggested_price, 2),
        "discount": discount,
        "reason": reason
    }
