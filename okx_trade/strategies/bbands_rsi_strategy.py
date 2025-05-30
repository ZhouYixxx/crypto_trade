import random
import traceback
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
import collections


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
        self.mode = 1 # 1: bband监控, 2: rsi监控
        self.prev_mode = 1 # 上次监控模式
        self.rsi_data = collections.deque(maxlen=150) # 记录最近150次的RSI计算结果

    def SignalRaise(self, df_list: List[pd.DataFrame]) -> dataclass.SignalMessage:
        """ 日线：价格突破布林带, 4小时K线: RSI金叉或死叉 \n
        Returns: dataclass.SignalMessage: 
            如果触发信号, 则返回信号消息且triggerd = True, 否则返回None
        """
        try:
            if self.last_signal_time is not None and ((dt.datetime.now() - self.last_signal_time) < dt.timedelta(hours=1)):
                return None  # 如果上次信号触发时间在1小时内，则不再触发新的信号

            df_1H = [df for df in df_list if df.name == "1H"][0]  # 1小时K线数据
            df_1D = [df for df in df_list if df.name == "1D"][0]  # 1DK线数据
            # 计算布林带
            df_1D = self._calculate_bollinger_bands(df_1D, self.bb_length, self.multipier)
            # # 计算RSI
            df_1H = self.__calculate_rsi(df_1H, self.rsi1, self.rsi2)
            # df_4h = self.__detect_rsi_divergence(df = df_4h, rsi_period=self.rsi1, rsi_overbought=90, rsi_oversold=15)

            self.prev_mode = self.mode
            # step1: 监控布林带
            signal1 = self.__bband_monitor(df_1D)
            if signal1 == 0 or self.mode == 1:
                return None
            # 计算RSI
            # df_1H = self.__calculate_rsi(df_1H, self.rsi1, self.rsi2)
            # step2: 监控RSI
            signal_msg = self.__rsi_monitor(direction=signal1, df_1H=df_1H)
            if signal_msg is not None and signal_msg.triggerd == True:
                self.last_signal_time = dt.datetime.now()  # 更新上次信号触发时间
            return signal_msg
        except Exception:
            self.logger.error(f"Error: {traceback.format_exc()}")
            return None

    def on_mode_changed(self)->int:
        if self.mode == self.prev_mode:
            return 0
        return self.mode

    def _calculate_bollinger_bands(self, df, length, multiplier):
        """ 使用 TA-Lib 计算布林带, 时间降序排列 """
        scale = 0
        close_prices = df['close'].values
        if close_prices[0] < 10**-2:
            scale = Util.find_scale(close_prices[0])
        close_prices = df['close'].values * 10**scale # 价格数据 
        upper, middle, lower = talib.BBANDS(
            close_prices[::-1],  # 收盘价数据
            timeperiod=length,  # 布林带周期
            nbdevup=multiplier,  # 上轨倍数
            nbdevdn=multiplier,  # 下轨倍数
            matype=talib.MA_Type.SMA  # 使用简单移动平均线
        )
        df['upper'] = upper[::-1] / 10**scale # 返回的结果以时间降序排列，即arr[0] 为最新价格，arr[-1]为最老价格
        df['middle'] = middle[::-1] / 10**scale
        df['lower'] = lower[::-1]  / 10**scale
        return df


    def __calculate_rsi(self, df:pd.DataFrame, n1:int = 3, n2:int = 12):
        """使用 TA-Lib 计算RSI, 时间降序排列 """
        scale = 0
        close_prices = df['close'].values[::-1]
        if close_prices[0] < 10**-3:
            scale = Util.find_scale(close_prices[0])
            close_prices = close_prices * 10**scale
        rsi1 = talib.RSI(
            close_prices,
            timeperiod=n1,
        )
        rsi2 = talib.RSI(
            close_prices,
            timeperiod=n2,
        )
        df[f'rsi_{n1}'] = rsi1[::-1] / 10**scale 
        df[f'rsi_{n2}'] = rsi2[::-1] / 10**scale
        self.rsi_data.append(df[f'rsi_{n1}'].iloc[0])
        # if len(self.rsi_data) == 0:
        #     self.rsi_data.extend(rsi1[~np.isnan(rsi1)] / 10**scale)
        # else:
        #     self.rsi_data.append(df[f'rsi_{n1}'].iloc[0])
        return df

    def __bband_monitor(self, df_1D:pd.DataFrame) -> int:
        """ 日线：监控价格是否突破布林带 \n
            如果触发信号, 则监控模式切换为2
        Returns: int: 1 = 上涨突破, -1 = 下跌突破, 0 = 未触发 
        """
        # 条件1：突破布林通道指标
        latest_close = df_1D['close'].iloc[0]  # 最新收盘价
        upper_band = df_1D['upper'].iloc[0]  # 最新上轨
        lower_band = df_1D['lower'].iloc[0]  # 最新下轨
        middle_band = df_1D['middle'].iloc[0]  # 最新中轨
        if self.mode == 1: # 布林带监控
            delta = (upper_band - lower_band) / 4 * self.bias
            if latest_close < (upper_band + delta) and latest_close > (lower_band - delta): #布林通道未能突破
                msg = f"监控模式={self.mode}... {self.inst_id} 价格在{self.bb_interval} 布林带上轨和下轨突破区间之内, 当前价 = {Util.price2str(latest_close)}, 当前上轨 = {Util.price2str(upper_band)}, 上涨突破价格={Util.price2str(upper_band + delta)}, 当前下轨 = {Util.price2str(lower_band)}, 下跌突破价格={Util.price2str(lower_band - delta)}, bias={self.bias}"
                self.logger.info(msg)
                return 0
            elif latest_close >= (upper_band + delta):
                # 上涨突破高位，准备做空
                msg = f"布林带突破！！ {self.inst_id}当前价格={Util.price2str(latest_close)}, 日线上涨突破布林通道上轨(={Util.price2str(upper_band)}) {self.bias}倍标准差！切换监控模式 = 2"
                self.logger.critical(msg)
                self.mode = 2 # 切换到RSI监控模式
                return 1
            elif latest_close <= (lower_band - delta):
                # 下跌突破低位，准备做多
                msg = f"布林带突破！！ {self.inst_id}当前价格={Util.price2str(latest_close)}, 日线下跌突破布林通道下轨(={Util.price2str(lower_band)}){self.bias}倍标准差！切换监控模式 = 2"
                self.logger.critical(msg)
                self.mode = 2 # 切换到RSI监控模式
                return -1

        elif self.mode == 2: # 当前已经是rsi监控，布林带监控应放宽阈值，避免频繁切换
            delta = (upper_band - lower_band) / 4 * self.bias
            delta = delta * 0.5 # 放宽阈值
            if latest_close < (upper_band + delta) and latest_close > (lower_band - delta): #放宽阈值后，布林通道未能突破，则切换回布林带监控
                msg = f"监控模式={self.mode}...{self.inst_id} 价格已回落到{self.bb_interval} 布林带上轨和下轨突破区间之内, 切换监控模式 = 1. 当前价 = {Util.price2str(latest_close)}, 当前上轨 = {Util.price2str(upper_band)}, 上涨突破价格={Util.price2str(upper_band + delta)}, 当前下轨 = {Util.price2str(lower_band)}, 下跌突破价格={Util.price2str(lower_band - delta)}, bias={self.bias}"
                self.logger.info(msg)
                self.mode = 1
                return 0
            elif latest_close >= (upper_band + delta):
                return 1
            elif latest_close <= (lower_band - delta):
                return -1
        
        return 0


    def __rsi_monitor(self, direction:int, df_1H:pd.DataFrame)->dataclass.SignalMessage:
        """ 1H线: 监控是否RSI金叉或死叉 \n
        Returns: 如果触发信号, 则返回信号消息且triggerd = True, 否则返回None
        """ 
        latest_close = df_1H['close'].iloc[0]  # 最新收盘价
        trend, avg_slope = self.__rsi_trend(window=30, overbought=90, oversold=12)
        if direction == 1:
            # 上涨突破高位，准备做空
            rsi1_cur = df_1H[f'rsi_{self.rsi1}'].iloc[0]
            rsi2_cur = df_1H[f'rsi_{self.rsi2}'].iloc[0]
            rsi1_prev = df_1H[f'rsi_{self.rsi1}'].iloc[1]
            rsi2_prev = df_1H[f'rsi_{self.rsi2}'].iloc[1]
            if rsi1_cur <= rsi2_cur and rsi1_prev > rsi2_prev and rsi1_prev >= 96 and abs(rsi1_cur - rsi1_prev) >= 6:
                msg = f"RSI死叉触发: {self.inst_id}当前价格={Util.price2str(latest_close)}, 当前RSI{self.rsi1}: {rsi1_cur}, 当前RSI{self.rsi2}: {rsi2_cur}, 上一RSI{self.rsi2}: {rsi1_prev}, 上一RSI{self.rsi2}: {rsi2_prev}"
                signal_tips = f"信号触发！！ sender = {self.name}! ! {self.inst_id}当前价格={Util.price2str(latest_close)}, 上涨突破布林通道且RSI高位死叉, 建议方向：做空！"
                triggerd = True
                self.logger.critical(msg + "\n" + signal_tips)
                return dataclass.SignalMessage(
                    sender=self.name,
                    content=signal_tips,
                    instId=self.inst_id,
                    price=latest_close,
                    triggerd=triggerd,
                    direction=direction
                )
            if rsi1_prev >= 96 and rsi1_cur < rsi1_prev and abs(rsi1_cur - rsi1_prev) >= 6:
                msg = f"RSI大幅下滑触发: {self.inst_id}当前价格={Util.price2str(latest_close)}, 当前RSI{self.rsi1}: {rsi1_cur}, 上一RSI{self.rsi1}: {rsi1_prev}"
                signal_tips = f"信号触发！！ sender = {self.name}! ! {self.inst_id}当前价格={Util.price2str(latest_close)}, 上涨突破布林通道且RSI大幅回落, 建议方向：做空！"
                triggerd = True
                self.logger.critical(msg + "\n" + signal_tips)
                return dataclass.SignalMessage(
                    sender=self.name,
                    content=signal_tips,
                    instId=self.inst_id,
                    price=latest_close,
                    triggerd=triggerd,
                    direction=direction
                )
            if trend == "做空":
                msg = f"RSI趋势信号触发: {self.inst_id}当前价格={Util.price2str(latest_close)}, 当前RSI{self.rsi1}: {rsi1_cur}, RSI最近10个点的斜率= {avg_slope} "
                signal_tips = f"信号触发！！ sender = {self.name}! ! {self.inst_id}当前价格={Util.price2str(latest_close)}, RSI趋势信号：做空！"
                triggerd = True
                self.logger.critical(msg + "\n" + signal_tips)
                return dataclass.SignalMessage(
                    sender=self.name,
                    content=signal_tips,
                    instId=self.inst_id,
                    price=latest_close,
                    triggerd=triggerd,
                    direction=direction
                )
        elif direction == -1:
            # 下跌突破低位，准备做多
            rsi1_cur = df_1H[f'rsi_{self.rsi1}'].iloc[0]
            rsi2_cur = df_1H[f'rsi_{self.rsi2}'].iloc[0]
            rsi1_prev = df_1H[f'rsi_{self.rsi1}'].iloc[1]
            rsi2_prev = df_1H[f'rsi_{self.rsi2}'].iloc[1]
            if rsi1_cur >= rsi2_cur and rsi1_prev < rsi2_prev and rsi1_prev <= 10 and abs(rsi1_cur - rsi1_prev) >= 6:
                msg = f"RSI金叉触发: {self.inst_id}当前价格={Util.price2str(latest_close)}, 当前RSI{self.rsi1}: {rsi1_cur}, 当前RSI{self.rsi2}: {rsi2_cur}, 上一RSI{self.rsi2}: {rsi1_prev}, 上一RSI{self.rsi2}: {rsi2_prev}"
                signal_tips = f"信号触发, sender = {self.name}！！ {self.inst_id}当前价格={Util.price2str(latest_close)}, 下跌突破布林通道且RSI低位金叉, 建议方向：做多！"
                triggerd = True
                self.logger.critical(msg + "\n" + signal_tips)
                return dataclass.SignalMessage(
                    sender=self.name,
                    content=signal_tips,
                    instId=self.inst_id,
                    price=latest_close,
                    triggerd=triggerd,
                    direction=direction
                )
            if rsi1_prev <= 10 and rsi1_cur > rsi1_prev and abs(rsi1_cur - rsi1_prev) >= 5:
                msg = f"RSI大幅上扬触发: {self.inst_id}当前价格={Util.price2str(latest_close)}, 当前RSI{self.rsi1}: {rsi1_cur}, 上一RSI{self.rsi1}: {rsi1_prev}"
                signal_tips = f"信号触发！！ sender = {self.name}! ! {self.inst_id}当前价格={Util.price2str(latest_close)}, 下跌突破布林通道且RSI大幅回落, 建议方向：做多！"
                triggerd = True
                self.logger.critical(msg + "\n" + signal_tips)
                return dataclass.SignalMessage(
                    sender=self.name,
                    content=signal_tips,
                    instId=self.inst_id,
                    price=latest_close,
                    triggerd=triggerd,
                    direction=direction
                )
            if trend == "做多":
                msg = f"RSI趋势信号触发: {self.inst_id}当前价格={Util.price2str(latest_close)}, 当前RSI{self.rsi1}: {rsi1_cur}, RSI最近10个点的斜率= {avg_slope} "
                signal_tips = f"信号触发！！ sender = {self.name}! ! {self.inst_id}当前价格={Util.price2str(latest_close)}, RSI趋势信号：做多！"
                triggerd = True
                self.logger.critical(msg + "\n" + signal_tips)
                return dataclass.SignalMessage(
                    sender=self.name,
                    content=signal_tips,
                    instId=self.inst_id,
                    price=latest_close,
                    triggerd=triggerd,
                    direction=direction
                )

        msg = f"监控模式={self.mode}... RSI信号未触发: {self.inst_id}当前RSI{self.rsi1}: {rsi1_cur}, 当前RSI{self.rsi2}: {rsi2_cur}, 上一RSI{self.rsi1}: {rsi1_prev}, 上一RSI{self.rsi2}: {rsi2_prev}"
        self.logger.info(msg)
        return None


    def __rsi_trend(self, window=20, overbought=90, oversold=12):
        """
        分析RSI数据, 判断价格趋势
        """
        if len(self.rsi_data) < window:
            return "数据不足", 0

        rsi_array = np.array(self.rsi_data, dtype=float)
        rsi_ema = talib.EMA(rsi_array, timeperiod=window)
        rsi_diff = np.diff(rsi_ema)
        avg_slope = np.mean(rsi_diff[-10:])
        latest_rsi = rsi_array[-1]

        if latest_rsi >= overbought and avg_slope <= -0.15:
            return "做空", avg_slope
        if latest_rsi <= oversold and avg_slope >= 0.15:
            return "做多", avg_slope
        return "无趋势", 0
        
