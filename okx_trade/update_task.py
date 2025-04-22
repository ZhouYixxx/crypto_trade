import asyncio
from typing import Dict, List, Set
from crypto_trader import crypto_trader 
from okx_api_async import OKXAPI_Async_Wrapper 
import pandas as pd
import numpy as np
import datetime as dt
from common_helper import Util
import dataclass
import copy
from common_helper import Logger
import traceback

class HotSymbolUpdater:
    """每隔一段时间，更新当前最热门的币种 (取涨跌幅前5)
    """
    def __init__(
        self,
        config:dataclass.Config,
        initial_hot_symbols: List[str],
        update_interval_minutes: int = 240,
    ):
        self.config:dataclass.Config = config
        self.hot_symbols = initial_hot_symbols  # 当前热门币种
        self.update_interval = update_interval_minutes * 60  # 转换为秒
        self.active_traders: Dict[str, crypto_trader] = {}  # 当前活跃的 trader
        self.tasks: List[asyncio.Task] = []  # 所有运行中的任务
        self._update_task: asyncio.Task | None = None  # update_task 的任务句柄
        self.logger = Logger(__name__).get_logger()

    def stop_trader(self, symbol: str):
        """停止某个币种的 trader"""
        if symbol in self.active_traders:
            trader = self.active_traders.pop(symbol)
            trader.stop()
        idx = -1
        for tsk in self.tasks:
            idx += 1
            name = tsk.get_name()
            if name == f"{symbol}_task":
                tsk.cancel()
                break
        if -1 < idx < len(self.tasks):
            self.tasks.pop(idx)
    
    def start_trader(self, symbol: str, delay: int = 2):
        """启动某个币种的 trader"""
        if symbol in self.active_traders:
            return  # 已经存在，不重复启动
        
        inst_config = copy.copy(self.config.symbols[symbol] if (symbol in self.config.symbols) else self.config.symbols["default"])
        inst_config.instId = symbol
        trader = crypto_trader(
            inst_config,
            self.config.email,
            self.config.indicators.bollinger_bands,
            self.config.common,
        )
        task = asyncio.create_task(trader.run(delay)) #后台运行trader
        task.set_name(f"{symbol}_task")
        self.active_traders[symbol] = trader
        self.tasks.append(task)

    async def run_update_task(self):
        """定期更新热门币种的循环任务"""
        while True:
            try:
                new_hot_list = await self.get_hot_symbols()
                new_top_symbols = {item[0] for item in new_hot_list}

                self.logger.newline(2)
                self.logger.info(f"当前TOP5币种:  {",".join(new_top_symbols)}")
                # 1. 停止不再热门的 trader
                to_stop = set(self.active_traders.keys()) - set(new_top_symbols)
                for symbol in to_stop:
                    if symbol not in self.config.symbols:
                        self.stop_trader(symbol)

                # 2. 启动新增的热门币种 trader
                to_add = set(new_top_symbols) - set(self.active_traders.keys())
                # 固定监控的币种仍然要添加
                for symbol in self.config.symbols.keys():
                    if symbol not in self.active_traders and symbol != "default":
                        to_add.add(symbol)
                
                delay = 0
                for symbol in to_add:
                    self.start_trader(symbol, delay)
                    delay += 2
                # if self.tasks:
                #     await asyncio.gather(*self.tasks)

                self.hot_symbols = new_top_symbols
            except Exception:
                self.logger.newline()
                self.logger.error(f"[HotSymbolUpdater] 运行失败: {traceback.format_exc()}")
            await asyncio.sleep(self.update_interval)

    async def start(self):
        """启动 updater, 在 main() 里调用"""
        if self._update_task is not None:
            return  # 防止重复启动

        # 启动定期更新任务
        self._update_task = asyncio.create_task(self.run_update_task())
        await self._update_task

    async def stop(self):
        """停止所有 trader 和 updater（在程序退出时调用）"""
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        # 停止所有 trader
        for symbol in list(self.active_traders.keys()):
            await self.stop_trader(symbol)

        # 取消所有任务
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()

    async def get_hot_symbols(self, count:int = 5) -> List[str]:
        """获取当前热门Top N币种列表"""
        response = await OKXAPI_Async_Wrapper.get_tickers_async(instType='SWAP')
        if response['code'] == '0':
            data = response['data']
            df = pd.DataFrame(data, columns=['instId', 'last', 'open24h', 'high24h', 'low24h', 'volCcy24h', 'vol24h', 'sodUtc0', 'sodUtc8', 'ts'])
            
            cols_to_convert = ['last', 'open24h', 'high24h', 'low24h', 'volCcy24h', 'vol24h', 'sodUtc0', 'sodUtc8']
            for col in cols_to_convert:
                df[col] = df[col].str.replace(r'[^\d.]', '', regex=True)  # 清理非数字字符
                df[col] = pd.to_numeric(df[col], errors='coerce')          # 转换为浮点数

            # 1. 计算涨幅列和保守交易量
            df['rise24h'] = (df['last'] - df['sodUtc8']) / df['sodUtc8']
            df['volUSD24h'] = df['volCcy24h'] * df['low24h'] 

            # 2. 筛选条件：交易量 > 500万美元 且 涨跌幅绝对值 > 10%
            rise_min = 0.1
            df_filtered = df[
                (df['volUSD24h'] > 5 * 10**6) & 
                (df['rise24h'].abs() > rise_min)
            ].copy()

            # 3. 按涨跌幅绝对值降序排序
            df_sorted = df_filtered.sort_values(
                by='rise24h', 
                key=lambda x: x.abs(), 
                ascending=False
            )

            # 4. 取前5名（若不足则全取）
            result = df_sorted.head(count)[['instId', 'rise24h', 'volUSD24h']].values.tolist()
            return result
        else:
            return []