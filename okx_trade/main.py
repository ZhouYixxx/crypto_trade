import os
import okx_api_async
import time
import asyncio
import common_helper
from crypto_trader import crypto_trader
import dataclass


# FLAG = "0"  # live trading: 0, demo trading: 1
# # 布林带参数
# LENGTH = 20  # 布林带周期
# MULTIPLIER = 2  # 布林带倍数
# INST_ID = 'BTC-USDT-SWAP'  # 交易对
# INTERVAL = '4H'  # K线周期，例如 4小时
# Bias = 0.5 # 偏置，理解为价格突破上轨后，还要再上涨0.5个标准差才能触发
# Auth_163 = "YMbXMY87PuJmFbZ2"

async def main():
    config = common_helper.Util.load_config()
    
    btc_config = config.symbols["BTC-USDT-SWAP"]
    btc_trader = crypto_trader(btc_config, config.email, config.indicators.bollinger_bands, config.common)

    eth_config = config.symbols["ETH-USDT-SWAP"]
    eth_trader = crypto_trader(eth_config, config.email, config.indicators.bollinger_bands, config.common)

    sol_config = config.symbols["SOL-USDT-SWAP"]
    sol_trader = crypto_trader(sol_config, config.email, config.indicators.bollinger_bands, config.common)

    pnut_config = config.symbols["PNUT-USDT-SWAP"]
    pnut_trader = crypto_trader(pnut_config, config.email, config.indicators.bollinger_bands, config.common)

    await asyncio.gather(
        # 每个trader之间延迟 5秒 启动
        run_trader_with_delay(btc_trader, 0),
        run_trader_with_delay(eth_trader, 5),
        run_trader_with_delay(sol_trader, 10),
        run_trader_with_delay(pnut_trader, 15),
    )

async def run_trader_with_delay(trader:crypto_trader, delay:int):
    await asyncio.sleep(delay)
    await trader.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger = common_helper.Logger(__name__).get_logger()
        logger.error(f"Error: {e}")