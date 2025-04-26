import random
import pandas as pd
import numpy as np
import talib
import dataclass
from okx_api_async import OKXAPI_Async_Wrapper 
import datetime as dt
from common_helper import Logger
from common_helper import Util
from typing import List, Dict, Tuple
from strategies import strategy_base

# FLAG = "0"  # live trading: 0, demo trading: 1
# # 布林带参数
# LENGTH = 20  # 布林带周期
# MULTIPLIER = 2  # 布林带倍数
# INST_ID = 'BTC-USDT-SWAP'  # 交易对
# INTERVAL = '4H'  # K线周期，例如 4小时
# Bias = 0.5 # 偏置，理解为价格突破上轨后，还要再上涨0.5个标准差才能触发下单或通知

class bbands_rsi_strategy():
    """监控价格是否超出布林带"""
    def __init__(self, inst_id:str, bb_interval:str = "1D", bias:float = 1.5, bb_length:int = 20, multipier:int = 2, 
                 rsi1:int = 3, rsi2:int = 12, rsi_interval:str = "4H"):
        self.name = "bbands_rsi_strategy"
        self.inst_id = inst_id
        self.bb_interval = bb_interval
        self.bias = bias
        # self.trade_date =  dt.datetime.today().strftime('%Y-%m-%d')
        self.bb_length = bb_length
        self.multipier = multipier
        self.logger = Logger(__name__).get_logger()
        self.rsi1 = rsi1
        self.rsi2 = rsi2
        self.rsi_interval = rsi_interval
        self.last_signal_time:dt.datetime = None # 上次信号触发时间

    def SignalRaise(self, df_list: List[pd.DataFrame]) -> dataclass.SignalMessage:
        """ 日线：价格突破布林带, 4小时K线: RSI金叉或死叉 \n
        Returns: dataclass.SignalMessage: 
            如果触发信号, 则返回信号消息且triggerd = True, 否则返回None
        """
        df_4h = [df for df in df_list if df.name == "4H"][0]  # 4小时K线数据
        df_1D = [df for df in df_list if df.name == "1D"][0]  # 1DK线数据
        # 计算RSI
        df_4h = self.__calculate_rsi(df_4h, self.rsi1, self.rsi2)
        # 计算布林带
        df_1D = self._calculate_bollinger_bands(df_1D, self.bb_length, self.multipier)
        # 监控价格突破
        signal_msg = self._monitor_breakout(df_1D, df_4h)
        return signal_msg


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


    # 使用 TA-Lib 计算RSI
    def __calculate_rsi(self, df:pd.DataFrame, n1:int = 3, n2:int = 12):
        close_prices = df['close'].values[::-1]
        rsi1 = talib.RSI(
            close_prices,
            timeperiod=n1,
        )
        rsi2 = talib.RSI(
            close_prices,
            timeperiod=n2,
        )
        df[f'rsi_{n1}'] = rsi1[::-1]
        df[f'rsi_{n2}'] = rsi2[::-1]
        return df

    def _monitor_breakout(self, df_1D, df_4H)-> dataclass.SignalMessage:
        """ 日线：价格突破布林带, 4小时K线: RSI金叉或死叉 \n
        Returns: dataclass.SignalMessage: 
            如果触发信号, 则返回信号消息且triggerd = True, 否则返回None
        """
        if self.last_signal_time is not None and ((dt.datetime.now() - self.last_signal_time) < dt.timedelta(hours=1)):
            return None  # 如果上次信号触发时间在1小时内，则不再触发新的信号

        # 条件1：突破布林通道指标
        latest_close = df_1D['close'].iloc[0]  # 最新收盘价
        upper_band = df_1D['upper'].iloc[0]  # 最新上轨
        lower_band = df_1D['lower'].iloc[0]  # 最新下轨
        middle_band = df_1D['middle'].iloc[0]  # 最新中轨
        triggerd = False
        delta = (upper_band - lower_band) / 4 * self.bias
        if latest_close < (upper_band + delta) and latest_close > (lower_band - delta):
            rand = random.randint(0,100) # 随机数， 偶数则 logging, 降低logging频率
            if rand & 1 == 0:
                msg = f"{self.inst_id} 价格在{self.bb_interval} 布林带上轨和下轨之间, 当前价 = {Util.price2str(latest_close)}, 当前上轨 = {Util.price2str(upper_band)}, 上涨临界价格={Util.price2str(upper_band + delta)}, 当前下轨 = {Util.price2str(lower_band)}, 下跌临界价格={Util.price2str(lower_band - delta)}, bias={self.bias}"
                self.logger.info(msg)
            return None 
        
        # 上涨突破高位，准备做空
        if latest_close >= (upper_band + delta):
            direction = 1  # 上涨
            # 条件2：RSI指标
            rsi1_cur = df_4H[f'rsi_{self.rsi1}'].iloc[0]
            rsi2_cur = df_4H[f'rsi_{self.rsi2}'].iloc[0]
            rsi1_prev = df_4H[f'rsi_{self.rsi1}'].iloc[-1]
            rsi2_prev = df_4H[f'rsi_{self.rsi2}'].iloc[-1]
            if rsi1_cur <= rsi2_cur and rsi1_prev > rsi2_prev and rsi1_prev >= 90 and abs(rsi1_cur - rsi1_prev) >= 7:
                msg += f"\n RSI死叉触发: 当前RSI{self.rsi1}: {rsi1_cur}, 当前RSI{rsi2_cur}: {rsi2_cur}, 上一RSI{self.rsi2}: {rsi1_prev}, 上一RSI{self.rsi2}: {rsi2_prev}"
                msg += f"\n 信号触发！！ {self.inst_id}当前价格={latest_close}, 上涨突破布林通道且RSI高位死叉, 建议方向：做空！"
                triggerd = True
                self.logger.critical(msg)
                msg = f"\n 信号触发！！ {self.inst_id}当前价格={latest_close}, 日线上涨突破布林通道上轨(={upper_band}){self.bias}倍标准差, 且4小时K线RSI高位死叉, 建议方向：做空！"
                #self.last_signal_time = dt.datetime.now()  # 更新上次信号触发时间
                return dataclass.SignalMessage(
                    sender=self.name,
                    content=msg,
                    instId=self.inst_id,
                    price=latest_close,
                    triggerd=triggerd,
                    direction=direction
                )
            else:
                msg = f"{self.inst_id} 价格突破{self.bb_interval} 布林带上轨 {self.bias}倍标准差! 最新价: {Util.price2str(latest_close)}, 上轨: {Util.price2str(upper_band)}"
                self.logger.info(msg)

        # 下跌突破低位，准备做多
        elif latest_close <= (lower_band - delta):
            direction = 0
            # 条件2：RSI指标
            rsi1_cur = df_4H[f'rsi_{self.rsi1}'].iloc[0]
            rsi2_cur = df_4H[f'rsi_{self.rsi2}'].iloc[0]
            rsi1_prev = df_4H[f'rsi_{self.rsi1}'].iloc[-1]
            rsi2_prev = df_4H[f'rsi_{self.rsi2}'].iloc[-1]
            if rsi1_cur >= rsi2_cur and rsi1_prev < rsi2_prev and rsi1_prev <= 15 and abs(rsi1_cur - rsi1_prev) >= 7:
                msg += f"\n RSI金叉触发: 当前RSI{self.rsi1}: {rsi1_cur}, 当前RSI{rsi2_cur}: {rsi2_cur}, 上一RSI{self.rsi2}: {rsi1_prev}, 上一RSI{self.rsi2}: {rsi2_prev}"
                msg += f"\n 信号触发！！ {self.inst_id}当前价格={latest_close}, 下跌突破布林通道且RSI低位金叉, 建议方向：做多！"
                triggerd = True
                self.logger.critical(msg)
                msg = f"\n 信号触发！！ {self.inst_id}当前价格={latest_close}, 日线下跌突破布林通道下轨(={lower_band}){self.bias}倍标准差, 且4小时K线RSI低位金叉, 建议方向：做空！"
                #self.last_signal_time = dt.datetime.now()  # 更新上次信号触发时间
                return dataclass.SignalMessage(
                    sender=self.name,
                    content=msg,
                    instId=self.inst_id,
                    price=latest_close,
                    triggerd=triggerd,
                    direction=direction
                )
            else:
                msg = f"{self.inst_id} 价格跌破{self.bb_interval} 布林带下轨 {self.bias}倍标准差! 最新价: {Util.price2str(latest_close)}, 下轨: {Util.price2str(lower_band)}"
                self.logger.info(msg)
        
        return None  # 没有触发信号

