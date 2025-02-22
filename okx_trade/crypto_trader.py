# import okx.MarketData as MarketData
# import requests
# import time
# import pandas as pd
# import numpy as np
# import talib
# from okx_api_async import OKXAPI_Async_Wrapper 

import asyncio
import datetime as dt

# import okx.Account as Account
# import okx.Funding as Funding
# import okx.PublicData as Public
# import okx.Trade as Trade
# import okx.TradingData as TradingData
# import okx.Status as Status
# import json
from common_helper import Logger
from common_helper import Util
from market_monitor import market_monitor
import dataclass

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
        self.logger = Logger(__name__).get_logger()
        self.market_monitor = market_monitor(inst_config.instId, inst_config.K_interval, inst_config.bias)

    async def run(self):
        self.logger.info(f"K线监控与自动交易模块启动, 当前币种：{self.inst_config.instId}, K线级别: {self.inst_config.K_interval}, 监控间隔: {self.common_config.interval}s ......")
        """运行交易逻辑"""
        while True:
            result = await self.market_monitor.price_triggered()
            last_send_time = Util.read_last_send_time(self.inst_config.instId)
            can_send_new = last_send_time is None or (dt.datetime.now() - last_send_time) > dt.timedelta(hours=6)
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
            await asyncio.sleep(self.common_config.interval)  # 间隔指定秒