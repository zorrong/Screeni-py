
import sys
import os
import pickle

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
        # Try to find which attribute is failing
        if hasattr(obj, '__dict__'):
            for k, v in obj.__dict__.items():
                try:
                    pickle.dumps(v)
                except:
                    print(f"    - Attribute '{k}' ({type(v)}) is NOT picklable")

test_pickle("ConfigManager", cm)
test_pickle("Fetcher", f)
test_pickle("Screener", s)
test_pickle("CandlePatterns", cp)
