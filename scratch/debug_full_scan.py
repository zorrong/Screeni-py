import os
import sys
import pandas as pd
import datetime
import pytz

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from classes.ConfigManager import tools as ConfigManagerTools
from classes.Fetcher import tools as FetcherTools
from classes.Screener import tools as ScreenerTools
from classes.CandlePatterns import CandlePatterns
from classes.Utility import tools as UtilityTools
from classes.ColorText import colorText

def debug_stock(stock_code):
    print(f"--- Debugging {stock_code} ---")
    configManager = ConfigManagerTools()
    # Force stage two off for debug
    configManager.onlyStageTwoStocks = False
    configManager.minPrice = 1.0
    configManager.volumeRatio = 0.1 # Very low to pass
    
    fetcher = FetcherTools(configManager)
    screener = ScreenerTools(configManager)
    candlePatterns = CandlePatterns()
    
    # 1. Fetch
    print("Step 1: Fetching data...")
    try:
        data, backtestReport = fetcher.fetchStockData(
            stock_code, 
            configManager.period, 
            configManager.duration, 
            None, 0, 0, 1, 
            tickerOption=12
        )
    except Exception as e:
        print(f"Fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return

    if data is None or data.empty:
        print("Data is empty!")
        return
    
    print(f"Data fetched: {len(data)} rows.")
    print(f"Columns: {data.columns.tolist()}")
    print(f"Sample data:\n{data.tail(3)}")
    
    # 2. Preprocess
    print("Step 2: Preprocessing...")
    try:
        # We need to simulate the reversal in Screener.py
        processedData = data[::-1]
        fullData, processedData = screener.preprocessData(processedData, configManager)
        print("Preprocessing done.")
        print(f"Processed columns: {processedData.columns.tolist()}")
    except Exception as e:
        print(f"Preprocessing failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Indicator Validation
    print("Step 3: Validating indicators...")
    try:
        screeningDictionary = {'Stock': stock_code, 'Consolidating': "",  'Breaking-Out': "",
                               'MA-Signal': "", 'Volume': "", 'LTP': 0, 'RSI': 0, 'Trend': "", 'Pattern': ""}
        saveDictionary = screeningDictionary.copy()
        
        isLtpValid, ltp = screener.validateLTP(processedData, screeningDictionary, saveDictionary, minPrice=configManager.minPrice, maxPrice=configManager.maxPrice)
        print(f"LTP Valid: {isLtpValid} (LTP: {ltp}, Min: {configManager.minPrice})")
        
        isVolumeHigh, volumeRatio = screener.validateVolume(processedData, screeningDictionary, saveDictionary, volumeRatio=configManager.volumeRatio)
        print(f"Volume High: {isVolumeHigh} (Ratio: {volumeRatio})")
        
        # Check patterns
        print("Step 4: Recognizing patterns...")
        pattern = candlePatterns.findPattern(fullData, screeningDictionary, saveDictionary)
        print(f"Pattern found: {pattern} -> {saveDictionary.get('Pattern')}")
        
    except Exception as e:
        print(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()

    print("--- Debug End ---")

if __name__ == "__main__":
    debug_stock("HPG")
