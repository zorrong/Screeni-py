import sys
import os
import datetime
import pandas as pd
from classes.ConfigManager import tools as ConfigManager
from classes.Fetcher import tools as Fetcher

def debug_fetch():
    config = ConfigManager()
    fetcher = Fetcher(config)
    
    stockCode = "HPG"
    print(f"Fetching data for {stockCode}...")
    
    # We need to mock a few things maybe, but let's try calling it directly
    # totalSymbols, screenResultsCounter, screenCounter are just for progress bars
    class MockCounter:
        def __init__(self): self.value = 0
        def get_lock(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass

    data, dateDict = fetcher.fetchStockData(
        stockCode=stockCode,
        period="300d",
        duration="1d",
        proxyServer=None,
        screenResultsCounter=MockCounter(),
        screenCounter=MockCounter(),
        totalSymbols=1,
        tickerOption=12 # Should use DNSE
    )
    
    if data is not None:
        print("Data fetched successfully!")
        print(f"Shape: {data.shape}")
        print(data.head())
        print(data.columns)
    else:
        print("Failed to fetch data.")

if __name__ == "__main__":
    # Add src to path
    sys.path.append(os.path.join(os.getcwd(), 'src'))
    debug_fetch()
