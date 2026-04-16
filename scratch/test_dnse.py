import requests
import datetime
import pandas as pd

def test_dnse(symbol):
    end_date = datetime.date.today() + datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=300)
    
    start_ts = int(datetime.datetime.combine(start_date, datetime.time.min).timestamp())
    end_ts = int(datetime.datetime.combine(end_date, datetime.time.min).timestamp())
    
    url = f"https://api.dnse.com.vn/chart-api/v2/ohlcs/stock?from={start_ts}&to={end_ts}&symbol={symbol}&resolution=1D"
    print(f"URL: {url}")
    
    res = requests.get(url, timeout=10)
    print(f"Status: {res.status_code}")
    json_data = res.json()
    
    if json_data.get('s') == 'ok':
        data = pd.DataFrame({
            'Date': json_data['t'],
            'Open': json_data['o'],
            'High': json_data['h'],
            'Low': json_data['l'],
            'Close': json_data['c'],
            'Volume': json_data['v']
        })
        print(f"Fetched {len(data)} rows")
        print(data.head())
    else:
        print(f"Error: {json_data}")

if __name__ == "__main__":
    test_dnse("HPG")
