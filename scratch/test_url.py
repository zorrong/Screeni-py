import requests
import time
import pandas as pd
start_ts = int(time.time() - 365*24*3600)
end_ts = int(time.time())
symbol = "HPG"
url = f"https://api.dnse.com.vn/chart-api/v2/ohlcs/stock?from={start_ts}&to={end_ts}&symbol={symbol}&resolution=1D"
print(f"URL: {url}")
res = requests.get(url)
print(f"Status: {res.status_code}")
print(f"Response: {res.text[:200]}...")
