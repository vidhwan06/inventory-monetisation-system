def generate_strategy(item):
    
    # Pricing logic
    if item['sales'] < 5:
        discount = "40%"
    elif item['sales'] < 10:
        discount = "20%"
    else:
        discount = "10%"
    
    # Basic strategy
    return {
        "discount": discount,
        "bundle": "Bundle with popular items",
        "target": "Online customers",
        "platform": "Amazon / Flipkart"
    }