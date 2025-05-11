import asyncio
import datetime as dt
from typing import List
import pandas as pd
import numpy as np
from common_helper import Logger
from common_helper import Util
import dataclass
import traceback
from globals import global_instance
from okx_api_async import OKXAPI_Async_Wrapper
from strategies import bbands_rsi_strategy
from strategies import sequential_rising_strategy
from strategies import rumi

class crypto_quote_monitor:
    def __init__(self, inst_config:dataclass.SymbolConfig, 
                 email_config:dataclass.EmailConfig, 
                 bb_config:dataclass.BollingerBandsConfig, 
                 common_config: dataclass.CommonConfig,
                 message_queue: asyncio.Queue):
        self.inst_config = inst_config
        self.email_config = email_config
        self.bb_config = bb_config
        self.common_config = common_config
        self.wait_seconds = common_config.wait_seconds
        self.message_queue = message_queue
        self.log_flag = 0 
        # self.inst_id = inst_id
        # self.exec_interval = exec_interval
        # self.k_interval = k_interval
        # self.flag = flag

        self.stop_event = asyncio.Event()  

        self.logger = Logger(__name__).get_logger()
        self.bbands_rsi_strategy = bbands_rsi_strategy.bbands_rsi_strategy(inst_id=inst_config.instId, bb_interval=inst_config.K_interval, bias=inst_config.bias)
        # self.sequential_rising_strategy = sequential_rising_strategy.sequential_rising_strategy(inst_id=inst_config.instId)
        self.rumi_strategy = rumi.rumi(inst_id=inst_config.instId)

    async def run(self, delay:int = 0):
            if delay > 0:
                await asyncio.sleep(delay)
            self.logger.info(f"K线监控与自动交易模块启动, 当前币种：{self.inst_config.instId}, K线级别: {self.inst_config.K_interval}, 监控间隔: {self.common_config.wait_seconds}s ......")
            """运行交易逻辑"""
            while not self.stop_event.is_set():
                try:
                    # 获取最新的K线数据
                    market_data = await self._get_candles()
                    if market_data is None or len(market_data) == 0:
                        await self._stoppable_wait()
                        continue
                    signal_msg = self.bbands_rsi_strategy.SignalRaise(df_list=market_data)
                    new_mode = self.bbands_rsi_strategy.on_mode_changed()
                    if new_mode == 1:
                        self.wait_seconds = self.common_config.wait_seconds
                    elif new_mode == 2:
                        self.wait_seconds = min(15, self.common_config.wait_seconds)
                    # signal_msg2 = self.rumi_strategy.SignalRaise(df_list=market_data)
                    signal_msg2 = None
                    if (signal_msg is None or signal_msg.triggerd==False) and (signal_msg2 is None or signal_msg2.triggerd==False):
                        await self._stoppable_wait()
                        continue

                    last_send_time = global_instance.inst_update_dict.get(self.inst_config.instId)
                    #隔4小时才重复提醒
                    can_send_new = (last_send_time is None or 
                                    (dt.datetime.now() - dt.datetime.strptime(last_send_time, "%Y-%m-%d %H:%M:%S")) > dt.timedelta(hours=4))
                    if signal_msg is not None and signal_msg.triggerd == True and can_send_new:
                        await self.message_queue.put(signal_msg)
                    elif signal_msg2 is not None and signal_msg2.triggerd == True and can_send_new:
                        await self.message_queue.put(signal_msg2)
                    await self._stoppable_wait()
                except Exception as e:
                    self.logger.newline()
                    self.logger.error(f"Error: {traceback.format_exc()}")
                    await asyncio.sleep(10)    

    async def _stoppable_wait(self):
        """使用wait_for来实现可中断的sleep. 实现在调用stop()后立即退出
        """
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(self.stop_event.wait()),
                asyncio.create_task(asyncio.sleep(self.wait_seconds)),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        
        # 方法二：用try catch来实现可中断的sleep
        # try:
        #     await asyncio.wait_for(self.stop_event.wait(), timeout=self.common_config.interval)
        # except asyncio.TimeoutError:
        #     pass

    # 获取K线数据
    async def _get_candles(self, limit=100)->List[pd.DataFrame]:
        df_list = []
        for item in ["15m","1H", "1D"]: #后续需要更多级别K线, 按需添加
            # response = market_data_api.get_candlesticks(instId=INST_ID, bar=interval, limit=limit)
            response = await OKXAPI_Async_Wrapper.get_candlesticks_async(instId=self.inst_config.instId, interval=item, limit=limit)
            if response['code'] == '0':
                data = response['data']
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
                df['close'] = df['close'].astype(float)
                df['timestamp'] = pd.to_datetime(df['timestamp'].astype(np.int64), unit='ms', utc=True).map(lambda t: t.tz_convert('Asia/Hong_Kong'))  # 转化UTC+8
                df.name = item
                df_list.append(df)
                await asyncio.sleep(0.25)  # 避免触发限流
            else:
                self.logger.error(f"获取K线数据失败, 当前币种: {self.inst_config.instId}, K线级别: {item}, 错误信息: {response['msg']}")
        return df_list
    
    def stop(self):
        print(f"停止监控币种 {self.inst_config} ...")
        self.stop_event.set()  # 通知 run() 退出
        self.logger = None
        self.bbands_rsi_strategy = None
        self.stop_event = None
        self.inst_config = None
        self.email_config = None
        self.bb_config = None
        self.common_config = None