import pandas as pd
import requests
import time
import datetime as dt
from classes.CandlePatterns import CandlePatterns
from classes.Fetcher import tools as FetcherTools

# Mock config
class MockConfig:
    period = "300d"
    duration = "1d"
    getPeriodNumeric = lambda x: 300

fetcher = FetcherTools(MockConfig())
start_ts = int(time.time() - 365*24*3600)
end_ts = int(time.time())
url = f"https://api.dnse.com.vn/chart-api/v2/ohlcs/stock?from={start_ts}&to={end_ts}&symbol=HPG&resolution=1D"
res = requests.get(url).json()

data = pd.DataFrame({
    'Date': res['t'],
    'Open': res['o'],
    'High': res['h'],
    'Low': res['l'],
    'Close': res['c'],
    'Volume': res['v']
})
data['Date'] = pd.to_datetime(data['Date'], unit='s')
data['Adj Close'] = data['Close']
data.set_index('Date', inplace=True)

# Preprocess like Screener does
fullData = data[::-1] # Newest first

cp = CandlePatterns()
screeningDict = {}
saveDict = {}
patternFound = cp.findPattern(fullData, screeningDict, saveDict)

print(f"Pattern Found: {patternFound}")
print(f"Pattern Name: {saveDict.get('Pattern')}")
print(f"Recent Data:\n{data.tail(5)}")
