import okx.MarketData as MarketData
import requests
import time
import pandas as pd
import numpy as np
import talib
from okx_api_async import OKXAPI_Async_Wrapper 

import asyncio

import okx.Account as Account
import okx.Funding as Funding
import okx.PublicData as Public
import okx.Trade as Trade
import okx.TradingData as TradingData
import okx.Status as Status
import json
from common_helper import Logger
from common_helper import Util


class market_monitor:
    def __init__(self, inst_id:str, interval:str, bias:float, bb_length:int = 20, multipier:int = 2):
        self.inst_id = inst_id
        self.interval = interval
        self.bias = bias
        self.bb_length = bb_length
        self.multipier = multipier
        self.logger = Logger(__name__).get_logger()

    # 提醒方式（这里以打印到控制台为例，你可以替换为邮件或Telegram通知）
    def _send_price_alert(self, message):
        Util.send_email_outlook(message)  # 替换为你的提醒逻辑，例如发送邮件或Telegram消息


    async def price_triggered(self):
        df = await self._get_candles(self.inst_id, self.interval)
        if df is not None:
            # 使用 TA-Lib 计算布林带
            df = self._calculate_bollinger_bands(df, self.bb_length, self.multipier)
            # 监控价格突破
            triggered, dir, curr_price, band_price = self._monitor_breakout(df)
            return triggered, dir, curr_price, band_price

    # 获取K线数据
    async def _get_candles(self, limit=30):
        # response = market_data_api.get_candlesticks(instId=INST_ID, bar=interval, limit=limit)
        response = await OKXAPI_Async_Wrapper.get_candlesticks_async(instId=self.inst_id, interval=self.interval, limit=limit)
        if response['code'] == '0':
            data = response['data']
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
            df['close'] = df['close'].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(np.int64), unit='ms')
            return df
        else:
            # print("Failed to fetch data:", response['msg'])
            return None


    # 使用 TA-Lib 计算布林带
    def _calculate_bollinger_bands(df, length, multiplier):
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
    def _monitor_breakout(self, df):
        latest_close = df['close'].iloc[0]  # 最新收盘价
        upper_band = df['upper'].iloc[0]  # 最新上轨
        lower_band = df['lower'].iloc[0]  # 最新下轨
        middle_band = df['middle'].iloc[0]  # 最新中轨
        triggerd = False
        delta = (upper_band - lower_band) / 4 * self.bias
        if latest_close > (upper_band + delta):
            msg = f"{self.inst_id} 价格突破{self.interval} 布林带上轨! 最新价: {round(latest_close,1)}, 上轨: {round(upper_band,1)}"
            triggerd = True
            self.logger.info(msg)
            self._send_price_alert(msg)
            return triggerd, "up", latest_close, upper_band
        elif latest_close < (lower_band - delta):
            msg = f"{self.inst_id} 价格跌破{self.interval} 布林带下轨! 最新价: {round(latest_close,1)}, 下轨: {round(lower_band,1)}"
            triggerd = True
            self._send_price_alert()
            return triggerd, "down", latest_close, lower_band
