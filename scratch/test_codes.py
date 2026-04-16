import sys
import os
from classes.ConfigManager import tools as ConfigManager
from classes.Fetcher import tools as Fetcher

def test_fetch_codes():
    config = ConfigManager()
    fetcher = Fetcher(config)
    
    print("Testing fetchCodes(tickerOption=12) using vnstock 3.x...")
    codes = fetcher.fetchCodes(tickerOption=12)
    
    if codes:
        print(f"Successfully fetched {len(codes)} symbols!")
        print(f"First 10 symbols: {codes[:10]}")
    else:
        print("Failed to fetch symbols or returned empty list.")

if __name__ == "__main__":
    sys.path.append(os.path.join(os.getcwd(), 'src'))
    test_fetch_codes()
