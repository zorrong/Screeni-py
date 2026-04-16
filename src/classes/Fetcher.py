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

# Exception class if yfinance stock delisted


class StockDataEmptyException(Exception):
    pass

# This Class Handles Fetching of Stock Data over the internet


class tools:

    def __init__(self, configManager):
        self.configManager = configManager
        pass

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
        if tickerOption == 12: # ALL Vietnam Stocks
            try:
                # Use local JSON list saved from DNSE/vnstock previously
                with open(os.path.join(os.path.dirname(__file__), 'vietnam_stocks.json'), 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading vietnam_stocks.json: {e}")
                return []
        if tickerOption == 16:
            return self.getAllNiftyIndices()
        if tickerOption == 18:
            try:
                # ccxt - binance top pairs
                exchange = ccxt.binance()
                markets = exchange.load_markets()
                symbols = [symbol for symbol in markets if symbol.endswith('/USDT')]
                return symbols
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
        with SuppressOutput(suppress_stdout=True, suppress_stderr=True):
            # Default to DNSE for individual stocks (unless it's Crypto or sectoral indices)
            if tickerOption != 18 and tickerOption != 16:
                try:
                    dates = self._getBacktestDate(backtest=backtestDate)
                    start_ts = int(dates[0].timestamp())
                    end_ts = int(dates[1].timestamp())
                    url = f"https://api.dnse.com.vn/chart-api/v2/ohlcs/stock?from={start_ts}&to={end_ts}&symbol={stockCode}&resolution=1D"
                    res = requests.get(url, timeout=10)
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
                        data['Date'] = pd.to_datetime(data['Date'], unit='s')
                        data['Adj Close'] = data['Close']
                        data.set_index('Date', inplace=True)
                    else:
                        data = pd.DataFrame()
                except Exception as e:
                    print(f"Error fetching DNSE data for {stockCode}: {e}")
                    data = pd.DataFrame()

            elif tickerOption == 18:
                try:
                    exchange = ccxt.binance()
                    timeframe = '1d'
                    if 'm' in duration: timeframe = duration
                    elif 'h' in duration: timeframe = duration
                    
                    ohlcv = exchange.fetch_ohlcv(stockCode, timeframe, limit=1000)
                    data = pd.DataFrame(ohlcv, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
                    data['Date'] = pd.to_datetime(data['Date'], unit='ms')
                    data['Adj Close'] = data['Close']
                    data.set_index('Date', inplace=True)
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
            if backtestDate != datetime.date.today():
                dateDict = self._getDatesForBacktestReport(backtest=backtestDate)
                backtestData = yf.download(
                    tickers=stockCode,
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
        tickers = ["^VNINDEX", "GC=F", "CL=F"] # VNINDEX, Gold, Crude
        data = yf.download(
                auto_adjust=False,
                tickers=tickers,
                period='5d',
                interval='1d',
                progress=False,
                timeout=10
            )
        data = self.makeDataBackwardCompatible(data)
        # Handle prefixing if needed, but yf.download with multiple tickers returns nested columns
        # Simplification: just return VNINDEX
        return data

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
        if isinstance(data.columns, pd.MultiIndex):
            data = data.droplevel(level=1, axis=1)
        data = data.rename_axis(None, axis=1)
        column_prefix = '' if column_prefix is None else column_prefix
        data = data[
            [
                f'{column_prefix}Open', 
                f'{column_prefix}High', 
                f'{column_prefix}Low', 
                f'{column_prefix}Close', 
                f'{column_prefix}Adj Close', 
                f'{column_prefix}Volume'
            ]
        ]
        return data
