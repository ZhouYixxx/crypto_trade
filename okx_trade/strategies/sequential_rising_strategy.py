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

class sequential_rising_strategy():
    """价格连续上涨或连续下跌超过一定幅度，触发信号"""
    
    def __init__(self, inst_id:str, chagne_pct:float = 0.25, sequential_days:int = 4,
                 sequential_interval:str = "1D"):
        """
        Args:
            inst_id (str): 币对
            chagne_pct (float, optional): 连续上涨或下跌的幅度. 默认 0.25, 代表这段时间的连续涨跌幅度必须超过25%
            sequential_days (int, optional): 连续上涨或下跌的天数. 默认 4, 代表连续涨跌至少4天
            sequential_interval (str, optional): 使用的K线. 默认 = "1D".
        """
        self.name = "sequential_rising_strategy"
        self.inst_id = inst_id
        self.chagne_pct = chagne_pct
        self.sequential_days = sequential_days
        self.sequential_interval = sequential_interval
        self.logger = Logger(__name__).get_logger()
        self.last_signal_time:dt.datetime = None # 上次信号触发时间

    def SignalRaise(self, df_list: List[pd.DataFrame]) -> dataclass.SignalMessage:
        """ 日线：价格突破布林带, 4小时K线: RSI金叉或死叉 \n
        Returns: dataclass.SignalMessage: 
            如果触发信号, 则返回信号消息且triggerd = True, 否则返回None
        """
        try:
            if self.last_signal_time is not None and ((dt.datetime.now() - self.last_signal_time) < dt.timedelta(hours=1)):
                return None  # 如果上次信号触发时间在1小时内，则不再触发新的信号
            
            df = [df for df in df_list if df.name == "1D"][0]  # 1D K线数据
            # 转换数据类型
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms',utc=True).map(lambda t: t.tz_convert('Asia/Hong_Kong'))  # OKX的时间戳通常是毫秒级, 转化UTC+8
            # df = df.sort_values('timestamp', ascending=True)
            df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)

            # 计算每日涨跌幅（正确的计算方式：当日收盘价对比前一日收盘价）
            df['pct_change'] = df['close'].pct_change() * 100

            # 标记涨跌状态 (1: 上涨, -1: 下跌, 0: 平盘)
            df['direction'] = 0
            df.loc[df['pct_change'] > 0, 'direction'] = 1
            df.loc[df['pct_change'] < 0, 'direction'] = -1
            seque_days = 0
            pct_total = 0.0
            latest_close = df['close'].iloc[0]

            for i in range(1, len(df)):
                curr_pct = df['pct_change'].iloc[i]
                prev_pct = df['pct_change'].iloc[i-1]
                
                if pd.isna(curr_pct) or pd.isna(prev_pct):
                    continue
                
                if (curr_pct >= 0 and prev_pct >= 0) or (curr_pct <= 0 and prev_pct <= 0):
                    seque_days += 1
                    pct_total += curr_pct
                    if seque_days >= self.sequential_days and abs(pct_total) >= self.chagne_pct:
                        trend = "上涨" if curr_pct > 0 else "下跌"
                        msg = f"\n 趋势信号触发！！ {self.inst_id}当前价格={latest_close}, 已经连续{trend}{seque_days}天, 累计{trend}幅度达到 {round(pct_total,2)}%,建议方向：{'做空' if trend == '上涨' else '做多'}！"
                        self.last_signal_time = dt.datetime.now()  # 更新上次信号触发时间
                        return dataclass.SignalMessage(
                            sender=self.name,
                            content=msg,
                            instId=self.inst_id,
                            price=latest_close,
                            triggerd=True,
                            direction = 1 if trend == '上涨' else 0 
                        )
            return None
        except Exception as e:
            self.logger.error(f"Error in SignalRaise: {traceback.format_exc()}")
            return None




