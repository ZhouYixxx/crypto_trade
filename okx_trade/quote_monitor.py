import settings as settings
import okx.MarketData as MarketData
import requests
import time
import pandas as pd
import numpy as np
import talib
import okx_api_async

import asyncio

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import okx.Account as Account
import okx.Funding as Funding
import okx.PublicData as Public
import okx.Trade as Trade
import okx.TradingData as TradingData
import okx.Status as Status
import json

# FLAG = "0"  # live trading: 0, demo trading: 1
# # 布林带参数
# LENGTH = 20  # 布林带周期
# MULTIPLIER = 2  # 布林带倍数
# INST_ID = 'BTS-USDT-SWAP'  # 交易对
# INTERVAL = '4H'  # K线周期，例如 4小时
Bias = 0.5 # 偏置，理解为价格突破上轨后，还要再上涨0.5个标准差才能触发

# Auth_163 = "YMbXMY87PuJmFbZ2"

# # 初始化 MarketAPI
# market_data_api = MarketData.MarketAPI(api_key=settings.API_KEY, api_secret_key=settings.SECRET_KEY, passphrase=settings.API_PASSPHRASE,flag = FLAG)

# 提醒方式（这里以打印到控制台为例，你可以替换为邮件或Telegram通知）
def send_alert(message):
    print(message)  # 替换为你的提醒逻辑，例如发送邮件或Telegram消息

    

# 获取K线数据
async def get_candles(instId, interval, limit=30):
    # response = market_data_api.get_candlesticks(instId=INST_ID, bar=interval, limit=limit)
    response = await okx_api_async.OKXAPI_Async_Wrapper.get_candlesticks_async(instId=instId, interval=interval, limit=limit)
    if response['code'] == '0':
        data = response['data']
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
        df['close'] = df['close'].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(np.int64), unit='ms')
        return df
    else:
        print("Failed to fetch data:", response['msg'])
        return None


# 使用 TA-Lib 计算布林带
def calculate_bollinger_bands(df, length, multiplier):
    close_prices = df['close'].values
    upper, middle, lower = talib.BBANDS(
        close_prices[::-1],  # 收盘价数据
        timeperiod=length,  # 布林带周期
        nbdevup=multiplier,  # 上轨倍数
        nbdevdn=multiplier,  # 下轨倍数
        matype=talib.MA_Type.SMA  # 使用简单移动平均线
    )
    df['upper'] = upper[::-1] # 返回的结果以时间降序排列，即arr[0] 为最新价格，arr[-1]为最老价格
    df['middle'] = middle[::-1]
    df['lower'] = lower[::-1]
    return df


# 监控价格突破
def monitor_breakout(instid, interval, df):
    latest_close = df['close'].iloc[0]  # 最新收盘价
    upper_band = df['upper'].iloc[0]  # 最新上轨
    lower_band = df['lower'].iloc[0]  # 最新下轨
    middle_band = df['middle'].iloc[0]  # 最新中轨
    delta = (upper_band - lower_band) / 4 * Bias
    if latest_close > (upper_band + delta):
        send_alert(f"🚀 {instid} 价格突破{interval}K线上轨! 最新价: {round(latest_close,1)}, 上轨: {round(upper_band,1)}")
    elif latest_close < (lower_band - delta):
        send_alert(f"🔻 {instid} 价格跌破{interval}K线下轨! 最新价: {round(latest_close,1)}, 下轨: {round(lower_band,1)}")


# 发送邮件
def send_email_outlook(sender_email, sender_password, receiver_emails, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = ','.join(receiver_emails)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.163.com", 465) as server:
            # server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_emails, msg.as_string())
            print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")