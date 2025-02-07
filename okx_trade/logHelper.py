import time
import pandas as pd
import numpy as np
from okx.MarketData import MarketAPI

# OKX API 配置
API_KEY = 'your_api_key'
SECRET_KEY = 'your_secret_key'
PASSPHRASE = 'your_passphrase'
FLAG = '0'  # 0: 实盘, 1: 模拟盘