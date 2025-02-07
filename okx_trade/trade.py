import settings as settings
import okx.MarketData as MarketData
import requests
import time
import pandas as pd
import numpy as np
import talib 

import okx.Account as Account
import okx.Funding as Funding
import okx.MarketData as Market
import okx.PublicData as Public
import okx.Trade as Trade
import okx.TradingData as TradingData
import okx.Status as Status
import json

FLAG = "0"  # live trading: 0, demo trading: 1
# 布林带参数
LENGTH = 20  # 布林带周期
MULTIPLIER = 2  # 布林带倍数
SYMBOL = 'BTC-USDT-SWAP'  # 交易对
INTERVAL = '1H'  # K线周期，例如 1小时

# 初始化 MarketAPI
market_data_api = MarketData.MarketAPI(api_key=settings.API_KEY, api_secret_key=settings.SECRET_KEY, passphrase=settings.API_PASSPHRASE,flag = FLAG)

# 获取某个币实时价格
def GetInsPrice(ccy:str):
    marketDataAPI = MarketData.MarketAPI(api_key=settings.API_KEY, api_secret_key=settings.SECRET_KEY, passphrase=settings.API_PASSPHRASE,flag = FLAG)
    ticker_info = marketDataAPI.get_ticker(instId="BTC-USDT-SWAP") # 获取行情
    if ticker_info["code"] != "0":
        print("获取BTC合约实时行情失败")
        return
    ticker_price = float(ticker_info["data"]["last"])
    return ticker_price

# 提醒方式（这里以打印到控制台为例，你可以替换为邮件或Telegram通知）
def send_alert(message):
    print(message)  # 替换为你的提醒逻辑，例如发送邮件或Telegram消息


# 获取K线数据
def get_candles(symbol, interval, limit=100):
    response = market_data_api.get_candlesticks(instId=symbol, bar=interval, limit=limit)
    if response['code'] == '0':
        data = response['data']
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy'])
        df['close'] = df['close'].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
        return df
    else:
        print("Failed to fetch data:", response['msg'])
        return None


# 使用 TA-Lib 计算布林带
def calculate_bollinger_bands(df, length, multiplier):
    close_prices = df['close'].values
    upper, middle, lower = talib.BBANDS(
        close_prices,  # 收盘价数据
        timeperiod=length,  # 布林带周期
        nbdevup=multiplier,  # 上轨倍数
        nbdevdn=multiplier,  # 下轨倍数
        matype=talib.MA_Type.SMA  # 使用简单移动平均线
    )
    df['upper'] = upper
    df['middle'] = middle
    df['lower'] = lower
    return df


# 监控价格突破
def monitor_breakout(df):
    latest_close = df['close'].iloc[-1]  # 最新收盘价
    upper_band = df['upper'].iloc[-1]  # 最新上轨
    lower_band = df['lower'].iloc[-1]  # 最新下轨

    if latest_close > upper_band:
        send_alert(f"🚀 Price broke above the upper Bollinger Band! Price: {latest_close}, Upper Band: {upper_band}")
    elif latest_close < lower_band:
        send_alert(f"🔻 Price broke below the lower Bollinger Band! Price: {latest_close}, Lower Band: {lower_band}")


# 主函数
def main():
    while True:
        # 获取K线数据
        df = get_candles(SYMBOL, INTERVAL)
        if df is not None:
            # 使用 TA-Lib 计算布林带
            df = calculate_bollinger_bands(df, LENGTH, MULTIPLIER)
            # 监控价格突破
            monitor_breakout(df)
        # 每隔一段时间运行一次（例如每5分钟）
        time.sleep(300)  # 300秒 = 5分钟


if __name__ == "__main__":
    main()