def analyze_inventory(df):
    
    slow_items = df[
        (df['sales'] < 10) | (df['last_sold_days'] > 30)
    ]
    
    return slow_items.to_dict(orient='records')