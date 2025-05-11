import traceback
from typing import List
import numpy as np
import pandas as pd
import talib
import matplotlib.pyplot as plt
import warnings
from common_helper import Util
import dataclass
from okx_api_async import OKXAPI_Async_Wrapper
import datetime as dt
from common_helper import Logger

warnings.filterwarnings('ignore')

class rumi:
    def __init__(self, inst_id):
        self.inst_id = inst_id
        self.last_signal_time:dt.datetime = None # 上次信号触发时间
        self.logger = Logger(__name__).get_logger()


    def SignalRaise(self, df_list: List[pd.DataFrame]) -> dataclass.SignalMessage:
        try:
            # data = tushare.get_k_data(code='hs300', start = '2018-01-01', end = '2023-11-18', ktype = 'D')
            if self.last_signal_time is not None and ((dt.datetime.now() - self.last_signal_time) < dt.timedelta(hours=1)):
                return None  # 如果上次信号触发时间在1小时内，则不再触发新的信号
            df = [df for df in df_list if df.name == "1H"][0]
            df = df.sort_values('timestamp').reset_index(drop=True)
            df.index = pd.to_datetime(df.index)
            df = df[['open','close','high','low']]
            df['pct'] = df['close'].shift(-1)/df['close']-1 #计算每日收益率
            
            #计算rumi
            df['fast'] = talib.SMA(df['close'].values, timeperiod = 3)
            df['slow'] = talib.WMA(df['close'].values, timeperiod = 50)
            df['diff'] = df['fast']-df['slow']
            df['rumi'] = talib.SMA(df['diff'].values, timeperiod = 30)
            df = df.dropna()
            if df['rumi'].iloc[-1] > 0:
                return dataclass.SignalMessage(
                    triggerd=True,
                    instId=self.inst_id,
                    sender='rumi',
                    direction=1,
                    price=df['close'].iloc[-1],
                    content=f"RUMI策略触发做多信号, {self.inst_id}当前价格: {Util.price2str(df['close'].iloc[-1])}, RUMI值: {df['rumi'].iloc[-1]}, 方向: 做多",
                )
            if df['rumi'].iloc[-1] < 0:
                return dataclass.SignalMessage(
                    triggerd=True,
                    instId=self.inst_id,
                    sender='rumi',
                    direction=1,
                    price=df['close'].iloc[-1],
                    content=f"RUMI策略触发做空信号, {self.inst_id}当前价格: {Util.price2str(df['close'].iloc[-1])}, RUMI值: {df['rumi'].iloc[-1]}, 方向: 做空",
                )
        except Exception:
            self.logger.error(f"Error: {traceback.format_exc()}")
            return None