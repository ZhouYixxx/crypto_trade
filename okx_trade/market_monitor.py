import pandas as pd
import numpy as np
import talib
from okx_api_async import OKXAPI_Async_Wrapper 
import datetime as dt
from common_helper import Logger
from common_helper import Util

# FLAG = "0"  # live trading: 0, demo trading: 1
# # 布林带参数
# LENGTH = 20  # 布林带周期
# MULTIPLIER = 2  # 布林带倍数
# INST_ID = 'BTC-USDT-SWAP'  # 交易对
# INTERVAL = '4H'  # K线周期，例如 4小时
# Bias = 0.5 # 偏置，理解为价格突破上轨后，还要再上涨0.5个标准差才能触发下单或邮件通知

class market_data_monitor:
    """监控价格是否超出布林带"""
    def __init__(self, inst_id:str, interval:str, bias:float, bb_length:int = 20, multipier:int = 2):
        self.inst_id = inst_id
        self.interval = interval
        self.bias = bias
        self.inst_ticker_his = None # 记录当前币种过去半年历史价位
        self.trade_date =  dt.datetime.today().strftime('%Y-%m-%d')
        self.bb_length = bb_length
        self.multipier = multipier
        self.logger = Logger(__name__).get_logger()


    async def price_triggered(self):
        # await self._update_ticker_his()
        
        df = await self._get_candles()
        if df is not None:
            # 使用 TA-Lib 计算布林带
            df = self._calculate_bollinger_bands(df, self.bb_length, self.multipier)
            # 监控价格突破
            return self._monitor_breakout(df)
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
    def _calculate_bollinger_bands(self, df, length, multiplier):
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
            msg = f"{self.inst_id} 价格突破{self.interval} 布林带上轨 {self.bias}倍标准差! 最新价: {Util.price2str(latest_close)}, 上轨: {Util.price2str(upper_band)}"
            triggerd = True
            self.logger.info(msg)
            return triggerd, "up", latest_close, upper_band, msg
        elif latest_close < (lower_band - delta):
            msg = f"{self.inst_id} 价格跌破{self.interval} 布林带下轨 {self.bias}倍标准差! 最新价: {Util.price2str(latest_close)}, 下轨: {Util.price2str(lower_band)}"
            triggerd = True
            return triggerd, "down", latest_close, lower_band, msg
        return False, "", 0,0, ""

    # 获取历史K线数据，每日执行一次
    async def _update_ticker_his(self):
        need_update =  self.inst_ticker_his is None or self.trade_date != dt.datetime.today().strftime('%Y-%m-%d')
        if need_update != True:
            return
        response = await OKXAPI_Async_Wrapper.get_candlesticks_async(instId=self.inst_id, interval="1D", limit=180)
        if response is None or response['code'] != '0':
            self.logger.warning("Failed to get history ticker data ...")
            return
        data = response['data']
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
        df['close'] = df['close'].astype(float)
        # curr_price = df['close'].values[0]
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(np.int64), unit='ms')
        df = df.sort_values(['close', 'timestamp'], ascending=[True, False]) #按收盘价升序排列，后按时间降序排列
        self.inst_ticker_his = df
        # ticker = df.loc[df['close'] >= some_value]
