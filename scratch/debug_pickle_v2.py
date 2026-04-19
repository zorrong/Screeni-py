
import sys
import os
import pickle
import datetime

# Setup path so we can import classes
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from classes.ConfigManager import tools as ConfigManager
from classes.Fetcher import tools as Fetcher
from classes.Screener import tools as Screener
from classes.CandlePatterns import CandlePatterns

cm = ConfigManager()
f = Fetcher(cm)
s = Screener(cm)
cp = CandlePatterns()

def test_pickle(name, obj):
    try:
        pickle.dumps(obj)
        print(f"[+] {name} is picklable")
    except Exception as e:
        print(f"[-] {name} is NOT picklable: {e}")
        if hasattr(obj, '__dict__'):
            for k, v in obj.__dict__.items():
                try:
                    pickle.dumps(v)
                except:
                    print(f"    - Attribute '{k}' ({type(v)}) is NOT picklable")
        elif isinstance(obj, tuple):
            for i, v in enumerate(obj):
                try:
                    pickle.dumps(v)
                except:
                    print(f"    - Element {i} ({type(v)}) is NOT picklable")
                    # If it's an object, dive deeper
                    if hasattr(v, '__dict__'):
                         for sub_k, sub_v in v.__dict__.items():
                             try:
                                 pickle.dumps(sub_v)
                             except:
                                 print(f"        - Sub-Attribute '{sub_k}' ({type(sub_v)}) is NOT picklable")

# Simulate the task tuple from screenipy.py
# (tickerOption, executeOption, reversalOption, maLength, daysForLowestVolume, minRSI, maxRSI, respChartPattern, insideBarToLookback, totalSymbols,
#                configManager, fetcher, screener, candlePatterns, stock, newlyListedOnly, downloadOnly, vectorSearch, isDevVersion, backtestDate, printCounter)

task = (18, 0, 0, 20, 30, 0, 100, 0, 0, 100,
        cm, f, s, cp, "BTC/USDT", False, False, None, False, datetime.date.today(), False)

test_pickle("Task Tuple", task)
