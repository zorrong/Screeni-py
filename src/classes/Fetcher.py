'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   28/04/2021
 *  Description         :   Class for handling networking for fetching stock codes and data
'''

import sys
import urllib.request
import csv
import requests
import random
import os
import datetime
import yfinance as yf
import pandas as pd
import ccxt
import json
from classes.ColorText import colorText
from classes.SuppressOutput import SuppressOutput
from classes.Utility import isDocker
import asyncio
# Add pnfTradingAPI_Py to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pnfTradingAPI_Py'))

# Suppress SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Exception class if yfinance stock delisted


class StockDataEmptyException(Exception):
    pass

# This Class Handles Fetching of Stock Data over the internet


class tools:

    def __init__(self, configManager):
        self.configManager = configManager
        self._loadAdapters()

    def _loadAdapters(self):
        try:
             # Just check if path exists or we can find the package
            adapter_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pnfTradingAPI_Py', 'adapters')
            if os.path.exists(adapter_path):
                self.multiSourceAvailable = True
            else:
                self.multiSourceAvailable = False
        except Exception:
            self.multiSourceAvailable = False

    def _fetchFromAdapter(self, adapter_type, symbol, **kwargs):
        try:
            # Dynamic import inside the method to avoid pickling issues in multiprocessing
            sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pnfTradingAPI_Py'))
            from adapters import dnse, ssi, vci, binance, bybit, okx
            
            adapters = {
                'dnse': dnse,
                'ssi': ssi,
                'vci': vci,
                'binance': binance,
                'bybit': bybit,
                'okx': okx
            }
            adapter = adapters.get(adapter_type)
            if not adapter:
                return []

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if adapter_type == 'dnse':
                res = loop.run_until_complete(adapter.fetch_dnse_ohlcv(symbol, **kwargs))
            elif adapter_type == 'ssi':
                res = loop.run_until_complete(adapter.fetch_ssi_daily_ohlcv(symbol, **kwargs))
            elif adapter_type == 'vci':
                res = loop.run_until_complete(adapter.fetch_vci_ohlcv(symbol, **kwargs))
            elif adapter_type == 'binance':
                res = loop.run_until_complete(adapter.fetch_binance_ohlcv(symbol, **kwargs))
            elif adapter_type == 'bybit':
                res = loop.run_until_complete(adapter.fetch_bybit_ohlcv(symbol, **kwargs))
            elif adapter_type == 'okx':
                # OKX usually needs BASE-QUOTE
                s = symbol.replace("/", "-")
                res = loop.run_until_complete(adapter.fetch_okx_ohlcv(s, **kwargs))
            else:
                res = []
                
            loop.close()
            return res
        except Exception as e:
            # print(f"Error fetching from adapter {adapter_type}: {e}")
            return []

    def fetchMultiSourceData(self, symbol, source='dnse', period='300d', duration='1d', backtestDate=None):
        if not self.multiSourceAvailable:
            return pd.DataFrame()
            
        data_list = []
        if source == 'dnse':
            data_list = self._fetchFromAdapter('dnse', symbol, resolution="1D", days=1000)
        elif source == 'ssi':
            data_list = self._fetchFromAdapter('ssi', symbol)
        elif source == 'vci':
            data_list = self._fetchFromAdapter('vci', symbol)
        elif source == 'binance':
            # Convert BTC/USDT to BTCUSDT
            s = symbol.replace("/", "").upper()
            data_list = self._fetchFromAdapter('binance', s, interval='1d', limit=1000)
        elif source == 'bybit':
            s = symbol.replace("/", "").upper()
            data_list = self._fetchFromAdapter('bybit', s, interval='1d', limit=1000)
        elif source == 'okx':
            s = symbol.replace("/", "-").upper()
            data_list = self._fetchFromAdapter('okx', s, interval='1d', limit=300)
            
        if not data_list:
            return pd.DataFrame()
            
        df = pd.DataFrame(data_list)
        df['Date'] = pd.to_datetime(df['time'])
        df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        df['Adj Close'] = df['Close']
        df.set_index('Date', inplace=True)
        df.drop(columns=['time'], inplace=True)
        
        if backtestDate:
            df = df[df.index.date <= backtestDate]
            
        return df

    def getAllNiftyIndices(self) -> dict:
        return {
            "VNINDEX": "VN Index",
            "VN30": "VN30 Index",
            "HNXIndex": "HNX Index",
            "UpcomIndex": "Upcom Index",
        }

    def _getBacktestDate(self, backtest):
        try:
            end = backtest + datetime.timedelta(days=1)
            if "d" in self.configManager.period:
                delta = datetime.timedelta(days = self.configManager.getPeriodNumeric())
            elif "wk" in self.configManager.period:
                delta = datetime.timedelta(days = self.configManager.getPeriodNumeric() * 7)
            elif "m" in self.configManager.period:
                delta = datetime.timedelta(minutes = self.configManager.getPeriodNumeric())
            elif "h" in self.configManager.period:
                delta = datetime.timedelta(hours = self.configManager.getPeriodNumeric())
            start = end - delta
            return [start, end]
        except:
            return [None, None]
        
    def _getDatesForBacktestReport(self, backtest):
        dateDict = {}
        try:
            today = datetime.date.today()
            dateDict['T+1d'] = backtest + datetime.timedelta(days=1) if backtest + datetime.timedelta(days=1) < today else None
            dateDict['T+1wk'] = backtest + datetime.timedelta(weeks=1) if backtest + datetime.timedelta(weeks=1) < today else None
            dateDict['T+1mo'] = backtest + datetime.timedelta(days=30) if backtest + datetime.timedelta(days=30) < today else None
            dateDict['T+6mo'] = backtest + datetime.timedelta(days=180) if backtest + datetime.timedelta(days=180) < today else None
            dateDict['T+1y'] = backtest + datetime.timedelta(days=365) if backtest + datetime.timedelta(days=365) < today else None
            for key, val in dateDict.copy().items():
                if val is not None:
                    if val.weekday() == 5:  # 5 is Saturday, 6 is Sunday
                        adjusted_date = val + datetime.timedelta(days=2)
                        dateDict[key] = adjusted_date
                    elif val.weekday() == 6: 
                        adjusted_date = val + datetime.timedelta(days=1)
                        dateDict[key] = adjusted_date
        except:
            pass
        return dateDict

    def fetchCodes(self, tickerOption,proxyServer=None):
        listStockCodes = []
        if tickerOption in [12, 13, 14]: # Vietnam Stocks
            try:
                # Primary: Try to fetch fresh list if it's SSI/VCI and multiSource is available
                if tickerOption == 13 and self.multiSourceAvailable:
                     # Dynamic import for fetcher
                     sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pnfTradingAPI_Py'))
                     from adapters import ssi
                     loop = asyncio.new_event_loop()
                     asyncio.set_event_loop(loop)
                     res = loop.run_until_complete(ssi.fetch_ssi_securities_list())
                     loop.close()
                     if res:
                         return [r.get('Symbol') for r in res if r.get('Symbol')]
                
                # Fallback to local JSON list
                with open(os.path.join(os.path.dirname(__file__), 'vietnam_stocks.json'), 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading stocks list: {e}")
                return []
        if tickerOption == 16:
            return self.getAllNiftyIndices()
        if tickerOption in [18, 19, 20]:
            try:
                # Use multi-source adapter if available
                if self.multiSourceAvailable:
                    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pnfTradingAPI_Py'))
                    from adapters import binance, bybit, okx
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    if tickerOption == 18:
                        res = loop.run_until_complete(binance.fetch_binance_symbols())
                    elif tickerOption == 19:
                        res = loop.run_until_complete(bybit.fetch_bybit_symbols())
                    elif tickerOption == 20:
                        res = loop.run_until_complete(okx.fetch_okx_symbols())
                    loop.close()
                    if res:
                        # Convert BASE-QUOTE to BASE/QUOTE for general CCXT compatibility if needed
                        return [r.replace("-", "/") for r in res if "USDT" in r]
                
                # Fallback to ccxt - binance top pairs for option 18
                if tickerOption == 18:
                    exchange = ccxt.binance()
                    markets = exchange.load_markets()
                    symbols = [symbol for symbol in markets if symbol.endswith('/USDT')]
                    return symbols
                return []
            except Exception as e:
                print(e)
                return []
        
        return listStockCodes

    # Fetch all stock codes from NSE
    def fetchStockCodes(self, tickerOption, proxyServer=None):
        listStockCodes = []
        if tickerOption == 0:
            stockCode = None
            while stockCode == None or stockCode == "":
                stockCode = str(input(colorText.BOLD + colorText.BLUE +
                                      "[+] Enter Stock Code(s) for screening (Multiple codes should be seperated by ,): ")).upper()
            stockCode = stockCode.replace(" ", "")
            listStockCodes = stockCode.split(',')
        else:
            print(colorText.BOLD +
                  "[+] Getting Stock Codes From Vietnam Market... ", end='')
            listStockCodes = self.fetchCodes(tickerOption,proxyServer=proxyServer)
            if type(listStockCodes) == dict:
                listStockCodes = list(listStockCodes.keys())
            if len(listStockCodes) > 10:
                print(colorText.GREEN + ("=> Done! Fetched %d stock codes." %
                                         len(listStockCodes)) + colorText.END)
                if self.configManager.shuffleEnabled:
                    random.shuffle(listStockCodes)
                    print(colorText.BLUE +
                          "[+] Stock shuffling is active." + colorText.END)
                else:
                    print(colorText.FAIL +
                          "[+] Stock shuffling is inactive." + colorText.END)
                if self.configManager.stageTwo:
                    print(
                        colorText.BLUE + "[+] Screening only for the stocks in Stage-2! Edit User Config to change this." + colorText.END)
                else:
                    print(
                        colorText.FAIL + "[+] Screening only for the stocks in all Stages! Edit User Config to change this." + colorText.END)

            else:
                input(
                    colorText.FAIL + "=> Error getting stock codes! Press any key to exit!" + colorText.END)
                sys.exit("Exiting script..")

        return listStockCodes

    def fetchStockData(self, stockCode, period, duration, proxyServer, screenResultsCounter, screenCounter, totalSymbols, backtestDate=None, printCounter=False, tickerOption=None):
        dateDict = None
        # Default to DNSE/SSI/VCI for individual stocks
        if tickerOption in [12, 13, 14, 16]:
            source_map = {12: 'dnse', 13: 'ssi', 14: 'vci', 16: 'dnse'} # sectoral index 16 also DNSE
            source = source_map.get(tickerOption, 'dnse')
            
            try:
                # Try new multi-source first if available
                if self.multiSourceAvailable:
                    data = self.fetchMultiSourceData(stockCode, source=source, backtestDate=backtestDate)
                    if not data.empty:
                        return data
                
                # Legacy fallback for DNSE if option 12 or 16
                if tickerOption == 12 or tickerOption == 16:
                    import datetime as dt
                    if backtestDate is None:
                            backtestDate = dt.date.today()
                    
                    dates = self._getBacktestDate(backtest=backtestDate)
                    if backtestDate == dt.date.today():
                            start_dt = dt.datetime.now() - dt.timedelta(days=400) # Get plenty of data
                            end_dt = dt.datetime.now()
                    else:
                            start_dt = dt.datetime.combine(dates[0], dt.time.min)
                            end_dt = dt.datetime.combine(dates[1], dt.time.max)
                    
                    start_ts = int(start_dt.timestamp())
                    end_ts = int(dt.datetime.now().timestamp() - 86400) # Subtract 24 hours
                    market_type = "index" if tickerOption == 16 else "stock"
                    url = f"https://api.dnse.com.vn/chart-api/v2/ohlcs/{market_type}?from={start_ts}&to={end_ts}&symbol={stockCode}&resolution=1D"
                    
                    session = requests.Session()
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'application/json, text/plain, */*',
                        'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
                        'Origin': 'https://banggia.dnse.com.vn',
                        'Referer': 'https://banggia.dnse.com.vn/',
                        'Connection': 'keep-alive'
                    }
                    res = session.get(url, headers=headers, timeout=15, verify=False)
                    json_data = res.json()
                    
                    if isinstance(json_data, dict) and 't' in json_data and len(json_data['t']) > 0:
                        data = pd.DataFrame({
                            'Date': json_data['t'],
                            'Open': json_data['o'],
                            'High': json_data['h'],
                            'Low': json_data['l'],
                            'Close': json_data['c'],
                            'Volume': json_data['v']
                        })
                        data['Date'] = pd.to_datetime(data['Date'], unit='s')
                        data['Adj Close'] = data['Close']
                        data.set_index('Date', inplace=True)
                        data.dropna(subset=['Close'], inplace=True)
                        if backtestDate != dt.date.today():
                            data = data[data.index.date <= backtestDate]
                    else:
                        data = pd.DataFrame()
                else:
                    data = pd.DataFrame()
            except Exception as e:
                data = pd.DataFrame()

        elif tickerOption in [18, 19, 20]:
            source_map = {18: 'binance', 19: 'bybit', 20: 'okx'}
            source = source_map.get(tickerOption, 'binance')
            try:
                # Try new multi-source first
                if self.multiSourceAvailable:
                    data = self.fetchMultiSourceData(stockCode, source=source, backtestDate=backtestDate)
                    if not data.empty:
                        return data
                
                # Fallback to ccxt for Binance (option 18)
                if tickerOption == 18:
                    exchange = ccxt.binance()
                    timeframe = '1d'
                    if 'm' in duration: timeframe = duration
                    elif 'h' in duration: timeframe = duration
                    
                    ohlcv = exchange.fetch_ohlcv(stockCode, timeframe, limit=1000)
                    data = pd.DataFrame(ohlcv, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
                    data['Date'] = pd.to_datetime(data['Date'], unit='ms')
                    data['Adj Close'] = data['Close']
                    data.set_index('Date', inplace=True)
                else:
                    data = pd.DataFrame()
            except Exception as e:
                data = pd.DataFrame()

        else:
            data = yf.download(
                tickers=stockCode,
                period=period,
                interval=duration,
                progress=False,
                timeout=10,
                start=self._getBacktestDate(backtest=backtestDate)[0],
                end=self._getBacktestDate(backtest=backtestDate)[1],
                auto_adjust=False
            )
            # For df backward compatibility towards yfinance 0.2.32
            data = self.makeDataBackwardCompatible(data)
            # end
            if backtestDate is None:
                backtestDate = datetime.date.today()
                
            if backtestDate != datetime.date.today():
                dateDict = self._getDatesForBacktestReport(backtest=backtestDate)
                backtestData = yf.download(
                    tickers=stockCode + ".VN" if tickerOption == 12 else stockCode,
                    interval='1d',
                    progress=False,
                    timeout=10,
                    start=backtestDate - datetime.timedelta(days=1),
                    end=backtestDate + datetime.timedelta(days=370)
                )
                for key, value in dateDict.copy().items():
                    if value is not None:
                        try:
                            dateDict[key] = backtestData.loc[pd.Timestamp(value)]['Close']
                        except KeyError:
                            continue
                dateDict['T+52wkH'] = backtestData['High'].max()
                dateDict['T+52wkL'] = backtestData['Low'].min()
        if printCounter:
            sys.stdout.write("\r\033[K")
            try:
                print(colorText.BOLD + colorText.GREEN + ("[%d%%] Screened %d, Found %d. Fetching data & Analyzing %s..." % (
                    int((screenCounter.value/totalSymbols)*100), screenCounter.value, screenResultsCounter.value, stockCode)) + colorText.END, end='')
            except ZeroDivisionError:
                pass
            if len(data) == 0:
                print(colorText.BOLD + colorText.FAIL +
                      "=> Failed to fetch!" + colorText.END, end='\r', flush=True)
                raise StockDataEmptyException
                return None
            print(colorText.BOLD + colorText.GREEN + "=> Done!" +
                  colorText.END, end='\r', flush=True)
        return data, dateDict

    # Get Daily VNINDEX:
    def fetchLatestNiftyDaily(self, proxyServer=None):
        import datetime as dt
        # 1. Fetch VNINDEX from DNSE (OHLC)
        df_vn = pd.DataFrame()
        try:
            end_ts = int(dt.datetime.now().timestamp())
            start_ts = end_ts - (86400 * 40) # 40 days
            url = f"https://api.dnse.com.vn/chart-api/v2/ohlcs/stock?from={start_ts}&to={end_ts}&symbol=VNI&resolution=1D"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=10, verify=False)
            if res.status_code == 200:
                json_data = res.json()
                print(f"[DEBUG] DNSE Response Keys: {json_data.keys()}")
                if 't' in json_data and len(json_data['t']) > 0:
                    df_vn = pd.DataFrame({
                        'Date': json_data['t'],
                        'Open': json_data['o'],
                        'High': json_data['h'],
                        'Low': json_data['l'],
                        'Close': json_data['c'],
                        'Adj Close': json_data['c'],
                        'Volume': json_data['v']
                    })
                    df_vn['Date'] = pd.to_datetime(df_vn['Date'], unit='s').dt.date
                    df_vn.set_index('Date', inplace=True)
                    print(f"[DEBUG] VNINDEX Data Loaded: {len(df_vn)} rows")
                else:
                    print(colorText.BOLD + colorText.FAIL + "[!] DNSE returned no data for VNI!" + colorText.END)
        except Exception as e:
            print(f"Error fetching VNINDEX from DNSE: {e}")

        # 2. Fetch Gold and Crude from Yahoo
        df_gold = pd.DataFrame()
        df_crude = pd.DataFrame()
        try:
            df_commodities = yf.download(["GC=F", "CL=F"], period='40d', interval='1d', progress=False)
            if not df_commodities.empty:
                # Force flatten multiindex if exists
                if isinstance(df_commodities.columns, pd.MultiIndex):
                    # Extract Close values safely
                    try:
                        g_data = df_commodities.xs('GC=F', level=1, axis=1)['Close']
                        df_gold = pd.DataFrame({'gold_Close': g_data})
                    except: pass
                    try:
                        c_data = df_commodities.xs('CL=F', level=1, axis=1)['Close']
                        df_crude = pd.DataFrame({'crude_Close': c_data})
                    except: pass
                else:
                    # Single ticker or unusual structure
                    if 'Close' in df_commodities.columns:
                        df_gold = df_commodities[['Close']].rename(columns={'Close': 'gold_Close'})
                
                if not df_gold.empty: df_gold.index = df_gold.index.date
                if not df_crude.empty: df_crude.index = df_crude.index.date
        except Exception as e:
            pass

        # 3. Merge and Ensure Columns
        if not df_vn.empty:
            final_df = df_vn.copy()
            # Ensure index is not a MultiIndex and has no name conflicts
            final_df.index.name = 'Date'
            
            if not df_gold.empty:
                final_df = final_df.merge(df_gold, left_index=True, right_index=True, how='left')
            if not df_crude.empty:
                final_df = final_df.merge(df_crude, left_index=True, right_index=True, how='left')
            
            # Ensure all string column names
            final_df.columns = [str(c) for c in final_df.columns]
            
            # Ensure AI-required columns exist (Standard Nifty model needs these)
            required = ['Open', 'High', 'Low', 'Close', 'gold_Close', 'crude_Close']
            for col in required:
                if col not in final_df.columns:
                    final_df[col] = final_df['Close'] if 'Close' in final_df.columns else 0.0
                
            final_df.ffill(inplace=True)
            final_df.bfill(inplace=True)
            return final_df
        
        return pd.DataFrame()

    # Get Data for Five EMA strategy (Placeholder for Vietnam)
    def fetchFiveEmaData(self, proxyServer=None):
        return None, None, None, None

    # Load stockCodes from the watchlist.xlsx
    def fetchWatchlist(self):
        createTemplate = False
        data = pd.DataFrame()
        try:
            data = pd.read_excel('watchlist.xlsx')
        except FileNotFoundError:
            print(colorText.BOLD + colorText.FAIL +
                  f'[+] watchlist.xlsx not found in f{os.getcwd()}' + colorText.END)
            createTemplate = True
        try:
            if not createTemplate:
                data = data['Stock Code'].values.tolist()
        except KeyError:
            print(colorText.BOLD + colorText.FAIL +
                  '[+] Bad Watchlist Format: First Column (A1) should have Header named "Stock Code"' + colorText.END)
            createTemplate = True
        if createTemplate:
            if isDocker():
                print(colorText.BOLD + colorText.FAIL +
                  f'[+] This feature is not available with dockerized application. Try downloading .exe/.bin file to use this!' + colorText.END)
                return None
            sample = {'Stock Code': ['SBIN', 'INFY', 'TATAMOTORS', 'ITC']}
            sample_data = pd.DataFrame(sample, columns=['Stock Code'])
            sample_data.to_excel('watchlist_template.xlsx',
                                 index=False, header=True)
            print(colorText.BOLD + colorText.BLUE +
                  f'[+] watchlist_template.xlsx created in {os.getcwd()} as a referance template.' + colorText.END)
            return None
        return data
    
    def makeDataBackwardCompatible(self, data:pd.DataFrame, column_prefix:str=None) -> pd.DataFrame:
        if data is None or data.empty:
            return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'])
            
        if isinstance(data.columns, pd.MultiIndex):
            data = data.droplevel(level=1, axis=1)
        data = data.rename_axis(None, axis=1)
        
        column_prefix = '' if column_prefix is None else column_prefix
        
        # Ensure columns exist with prefix
        required = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        for col in required:
            col_name = f'{column_prefix}{col}'
            if col_name not in data.columns:
                if col == 'Adj Close' and f'{column_prefix}Close' in data.columns:
                    data[col_name] = data[f'{column_prefix}Close']
                else:
                    data[col_name] = 0.0
                    
        return data[[f'{column_prefix}{col}' for col in required]]
