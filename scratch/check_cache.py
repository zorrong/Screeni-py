import pickle
import os
import pandas as pd

cache_file = '/home/zorrong/Screeni-py/actions-data-download/stock_data_140823.pkl'

if not os.path.exists(cache_file):
    print(f"File {cache_file} does not exist!")
else:
    size = os.path.getsize(cache_file)
    print(f"File size: {size / (1024*1024):.2f} MB")
    
    try:
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        
        print(f"Type of data: {type(data)}")
        if isinstance(data, dict):
            print(f"Number of stocks in cache: {len(data)}")
            if len(data) > 0:
                first_stock = list(data.keys())[0]
                print(f"Sample stock: {first_stock}")
                # print(data[first_stock])
        else:
            print("Data is not a dictionary!")
    except Exception as e:
        print(f"Error reading cache: {e}")
