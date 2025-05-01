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

class CryptoTrader:
    def __init__(self, name, message_queue, max_concurrent=4):
            self.name = name
            self.message_queue = message_queue  
            self.running = True
            self.max_concurrent = max_concurrent
            self.semaphore = asyncio.Semaphore(max_concurrent)
            self.logger = Logger(__name__).get_logger()

    async def process_messages(self):
        """异步从队列中消费消息"""
        while self.running:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=10)
                if not isinstance(message, dataclass.SignalMessage):
                    self.logger(f"Warning: Received invalid message type: {type(message)}")
                    self.message_queue.task_done()
                    continue
                async with self.semaphore:
                    asyncio.create_task(self.handle_message(message))
                self.message_queue.task_done()
            except asyncio.TimeoutError:
                continue

    async def handle_message(self, message:dataclass.SignalMessage):
        try:
            # todo: 下单
            # success2 = Util.send_email_outlook(self.email_config.from_email, self.email_config.auth_163, self.email_config.smtp_server, self.email_config.smtp_port,
            #                                  self.email_config.to_email, f"{self.inst_config.instId} 价格预警", msg, self.logger)
            success = await Util.send_feishu_message(self.email_config.feishu_webhook, f"{message.content} \nsernder = {message.sender}", self.logger)
            if success:
                global_instance.inst_update_dict.update(self.inst_config.instId, dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except Exception:
            self.logger.error(f"Error: {traceback.format_exc()}")
            pass

    def stop(self):
        self.running = False