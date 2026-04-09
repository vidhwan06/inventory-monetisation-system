from fastapi import FastAPI
import csv
import os

from agents.demand import demand_agent
from agents.risk import risk_agent
from agents.pricing import pricing_agent
from agents.action import action_agent
from aggregator.decision import aggregate_decision

app = FastAPI(title="Multi-Agent Inventory Monetisation System")

def load_products():
    """Helper function to load products from CSV data file."""
    products = []
    filepath = os.path.join(os.path.dirname(__file__), "data", "products.csv")
    if not os.path.exists(filepath):
        return products
        
    with open(filepath, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            products.append(row)
    return products

@app.get("/analyze_all")
def analyze_all():
    """
    Endpoint that fetches all products, processes them through the multi-agent system,
    and returns a comprehensive aggregated decision output.
    """
    products = load_products()
    results = []
    
    for product in products:
        # 1. Individual Agents process the data
        demand_output = demand_agent(product)
        risk_output = risk_agent(product)
        pricing_output = pricing_agent(product)
        action_output = action_agent(demand_output, risk_output)
        
        # 2. Aggregator synthesizes the individual insights
        decision_output = aggregate_decision(product, demand_output, risk_output, pricing_output, action_output)
        
        # 3. Structure the exact response format
        results.append({
            "product": product.get("name", "Unknown"),
            "agents": {
                "demand_agent": demand_output,
                "risk_agent": risk_output,
                "pricing_agent": pricing_output,
                "action_agent": action_output
            },
            "final_decision": decision_output
        })
        
    return results

if __name__ == "__main__":
    import uvicorn
    # Make it runnable directly from the CLI via `python main.py` or `uvicorn main:app --reload`
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
