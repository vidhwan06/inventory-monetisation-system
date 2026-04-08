from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Backend is working!"}

from fastapi import File, UploadFile
import pandas as pd
from analyzer import analyze_inventory
from strategy import generate_strategy

@app.post("/analyze/")
async def analyze(file: UploadFile = File(...)):
    
    df = pd.read_csv(file.file)
    
    slow_items = analyze_inventory(df)
    
    results = []
    
    for item in slow_items:
        strategy = generate_strategy(item)
        
        # merge both
        item.update(strategy)
        
        results.append(item)
    
    return {
        "results": results
    }