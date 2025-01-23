import settings as settings
import logging
import okx.MarketData as MarketData
import datetime as dt
import requests
import time
import hashlib
import hmac
import base64
import okx.Account as Account
import okx.Funding as Funding
import okx.MarketData as Market
import okx.PublicData as Public
import okx.Trade as Trade
import okx.TradingData as TradingData
import okx.Status as Status
import json



flag = "0"  # live trading = 0, demo trading = 1
day = dt.datetime.now().strftime("%Y%m%d") # format = 20241013
logger = None

# 获取某个币实时行情价格
def GetInsPrice(ccy:str):
    marketDataAPI = MarketData.MarketAPI(api_key=settings.API_KEY, api_secret_key=settings.SECRET_KEY, passphrase=settings.API_PASSPHRASE,flag = flag)
    ticker_info = marketDataAPI.get_ticker(instId="BTC-USDT-SWAP") # 获取行情
    if ticker_info["code"] != "0":
        print(f"获取{ccy}合约实时行情失败")
        return
    ticker_price = float.parse(ticker_info["data"]["last"])
    
    # publicAPI = Public.PublicAPI(api_key = settings.API_KEY, api_secret_key=settings.SECRET_KEY, passphrase=settings.API_PASSPHRASE, flag=flag)
    # accountAPI = Account.AccountAPI(settings.API_KEY, settings.SECRET_KEY, settings.API_PASSPHRASE, False, flag=flag)
    # fundingAPI = Funding.FundingAPI(settings.API_KEY, settings.SECRET_KEY, settings.API_PASSPHRASE, False, flag=flag)
    # trading_pair = publicAPI.get_instruments(instId='BTC-USDT-SWAP',instType='SWAP') # SWAP = 永续合约， 获取交易品种信息
    # balance = accountAPI.get_account_balance(ccy='BTC,ETH,DOGE,SOL,BNB,USDT') # 交易账户的可用金额
    print("END")

def loggerInit(filename:str,loglevel:logging._Level)->logging.Logger:
    logging.basicConfig(filename=filename,
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=loglevel)
    logger = logging.getLogger()
    return logger


if __name__ == "__main__":
    logger = loggerInit(filename=f"logs/{day}.log", loglevel=logging.INFO)
    GetInsPrice()

def newFunc():
    