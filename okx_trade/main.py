# import os
# import okx_api_async
# import time
import asyncio
import common_helper
import strategies.rumi as stgy1
from crypto_trader import crypto_trader
from typing import Dict, List, Set
from okx_api_async import OKXAPI_Async_Wrapper 
import pandas as pd
import numpy as np
import datetime as dt


# FLAG = "0"  # live trading: 0, demo trading: 1
# # 布林带参数
# LENGTH = 20  # 布林带周期
# MULTIPLIER = 2  # 布林带倍数
# INST_ID = 'BTC-USDT-SWAP'  # 交易对
# INTERVAL = '4H'  # K线周期，例如 4小时
# Bias = 0.5 # 偏置，理解为价格突破上轨后，还要再上涨0.5个标准差才能触发
# Auth_163 = "YMbXMY87PuJmFbZ2"

async def main():
    # rumi = stgy1.rumi("BTC-USDT-SWAP")
    # await rumi.backtest()
    config = common_helper.Util.load_config()
    active_traders: Dict[str, crypto_trader] = {}  # 当前运行中的交易监控器
    last_top_symbols: Set[str] = set()  # 上一次的热门币种
    logger = common_helper.Logger(__name__).get_logger()

    while True:
        try:
            fixed_symbols = set(config.symbols.keys())
            fixed_symbols.remove("default")
            # 将不再是top5的币种停止监控
            top_list = await get_hot_symbols()
            if top_list is not None and len(top_list) > 0:
                current_top_symbols = {item[0] for item in top_list}
            to_remove = last_top_symbols - current_top_symbols
            for symbol in to_remove:
                if (symbol in active_traders) and (symbol not in fixed_symbols):
                    active_traders[symbol].stop()  
                    active_traders.pop(symbol)
            
            to_add = current_top_symbols - last_top_symbols
            tasks = []
            i = 0
            # 将当前Top5币种添加到监控中
            for symbol in to_add:
                if symbol in config.symbols:
                    inst_config = config.symbols[symbol]
                else:
                    inst_config = config.symbols["default"]
                inst_trader = crypto_trader(
                    inst_config, 
                    config.email, 
                    config.indicators.bollinger_bands, 
                    config.common
                )
                active_traders[symbol] = inst_trader
                tasks.append(run_trader_with_delay(inst_trader, i * 5))
                i += 1

            # BTC、ETH等币种默认进行监控
            for inst in fixed_symbols:
                if inst in active_traders:
                    continue
                inst_config = config.symbols[inst]
                inst_trader = crypto_trader(inst_config, config.email, config.indicators.bollinger_bands, config.common)
                tasks.append(run_trader_with_delay(inst_trader, i * 5))
                i+=1

            if tasks:
                await asyncio.gather(*tasks)
            
            last_top_symbols = current_top_symbols
            
            # 等待半小时
            await asyncio.sleep(1800)

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(10)

    # btc_config = config.symbols["BTC-USDT-SWAP"]
    # btc_trader = crypto_trader(btc_config, config.email, config.indicators.bollinger_bands, config.common)

    # eth_config = config.symbols["ETH-USDT-SWAP"]
    # eth_trader = crypto_trader(eth_config, config.email, config.indicators.bollinger_bands, config.common)

    # sol_config = config.symbols["SOL-USDT-SWAP"]
    # sol_trader = crypto_trader(sol_config, config.email, config.indicators.bollinger_bands, config.common)

    # pnut_config = config.symbols["PNUT-USDT-SWAP"]
    # pnut_trader = crypto_trader(pnut_config, config.email, config.indicators.bollinger_bands, config.common)

    # await asyncio.gather(
    #     # 每个trader之间延迟 5秒 启动
    #     run_trader_with_delay(btc_trader, 0),
    #     run_trader_with_delay(eth_trader, 5),
    #     run_trader_with_delay(sol_trader, 10),
    #     run_trader_with_delay(pnut_trader, 15),
    # )

async def run_trader_with_delay(trader:crypto_trader, delay:int):
    await asyncio.sleep(delay)
    await trader.run()

async def get_hot_symbols() -> List[str]:
    """获取当前热门Top10币种列表"""
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

        # 2. 筛选条件：交易量 > 1000万美元 且 涨跌幅绝对值 > 5%
        rise_min = 0.05 if dt.datetime.now().hour < 10 else 0.1
        df_filtered = df[
            (df['volUSD24h'] > 10**7) & 
            (df['rise24h'].abs() > rise_min)
        ].copy()

        # 3. 按涨跌幅绝对值降序排序
        df_sorted = df_filtered.sort_values(
            by='rise24h', 
            key=lambda x: x.abs(), 
            ascending=False
        )

        # 4. 取前10名（若不足则全取）
        result = df_sorted.head(10)[['instId', 'rise24h', 'volUSD24h']].values.tolist()
        return result
    else:
        # print("Failed to fetch data:", response['msg'])
        return None

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger = common_helper.Logger(__name__).get_logger()
        logger.error(f"Error: {e}")