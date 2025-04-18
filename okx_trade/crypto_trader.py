import asyncio
import datetime as dt
import pandas as pd
import numpy as np
from common_helper import Logger
from common_helper import Util
from market_monitor import bbands_monitor
import dataclass
import traceback

class crypto_trader:
    def __init__(self, inst_config:dataclass.SymbolConfig, email_config:dataclass.EmailConfig, bb_config:dataclass.BollingerBandsConfig, 
                 common_config: dataclass.CommonConfig):
        self.inst_config = inst_config
        self.email_config = email_config
        self.bb_config = bb_config
        self.common_config = common_config
        self.log_flag = 0 
        # self.inst_id = inst_id
        # self.exec_interval = exec_interval
        # self.k_interval = k_interval
        # self.flag = flag

        self.stop_event = asyncio.Event()  

        self.logger = Logger(__name__).get_logger()
        self.market_monitor = bbands_monitor(inst_config.instId, inst_config.K_interval, inst_config.bias)

    async def run(self, delay:int = 0):
            if delay > 0:
                await asyncio.sleep(delay)
            self.logger.info(f"K线监控与自动交易模块启动, 当前币种：{self.inst_config.instId}, K线级别: {self.inst_config.K_interval}, 监控间隔: {self.common_config.interval}s ......")
            """运行交易逻辑"""
            while not self.stop_event.is_set():
                try:
                    result = await self.market_monitor.price_triggered()
                    last_send_time = Util.read_last_send_time(self.inst_config.instId)
                    can_send_new = last_send_time is None or (dt.datetime.now() - last_send_time) > dt.timedelta(hours=1)
                    if result[0] == True and can_send_new:
                    # todo: 下单
                        msg = result[4]
                        success = Util.send_email_outlook(self.email_config.from_email, self.email_config.auth_163, self.email_config.smtp_server, self.email_config.smtp_port,
                                                        self.email_config.to_email, f"{self.inst_config.instId} 价格预警", msg, self.logger)
                        if success:
                            Util.update_last_send_time(self.inst_config.instId)
                    # if await self.should_trade(price):
                    #     order = await self.order_manager.place_order(price)
                    #     if order:
                    #         await self.risk_manager.monitor_order(order["id"], price)
                    elif result[0] == False:
                        #降低常规log频率
                        if  self.log_flag == 3:
                            self.logger.info(f"{self.inst_config.instId} 价格尚未突破 {self.inst_config.K_interval}级别K线b-band...")
                            self.log_flag = 0
                        else:
                            self.log_flag += 1
                    # 使用wait_for来实现可中断的sleep. 默认情况下等待 interval 秒，调用stop()后立即退出
                    done, pending = await asyncio.wait(
                        [
                            asyncio.create_task(self.stop_event.wait()),
                            asyncio.create_task(asyncio.sleep(self.common_config.interval)),
                        ],
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                    # try:
                    #     await asyncio.wait_for(self.stop_event.wait(), timeout=self.common_config.interval)
                    # except asyncio.TimeoutError:
                    #     pass
                except Exception as e:
                    self.logger.newline()
                    self.logger.error(f"Error: {traceback.format_exc()}")
                    await asyncio.sleep(5)    
    def stop(self):
        print(f"停止监控币种 {self.inst_config} ...")
        self.stop_event.set()  # 通知 run() 退出