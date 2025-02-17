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
import market_monitor

class crypto_trader:
    def __init__(self, inst_id:str, k_interval:str, bias:float, exec_interval:int, flag:int):
        self.inst_id = inst_id
        self.exec_interval = exec_interval
        self.k_interval = k_interval
        self.flag = flag
        self.logger = Logger(__name__).get_logger()
        self.market_monitor = market_monitor(inst_id, k_interval, bias)

    async def run(self):
        self.logger.info(f"K线监控与自动交易模块启动, 当前币种：{self.inst_id}, K线级别: {self.k_interval}, 监控间隔: {self.exec_interval}s ......")
        """运行交易逻辑"""
        while True:
            price = await self.market_monitor.price_triggered()
            print(f"{self.symbol} current price: {price}")

            if await self.should_trade(price):
                order = await self.order_manager.place_order(price)
                if order:
                    await self.risk_manager.monitor_order(order["id"], price)
            await asyncio.sleep(self.exec_interval)  # 间隔指定秒