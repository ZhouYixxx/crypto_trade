# import os
# import okx_api_async
# import time
import asyncio
import copy
import common_helper
import strategies.rumi as stgy1
from crypto_trader import crypto_trader
from typing import Dict, List, Set
from update_task import HotSymbolUpdater
import traceback

# Auth_163 = "YMbXMY87PuJmFbZ2" //每隔180天要重新授权一次

async def main():
    # rumi = stgy1.rumi("BTC-USDT-SWAP")
    # await rumi.backtest()
    config = common_helper.Util.load_config()
    logger = common_helper.Logger(__name__).get_logger()
    fixed_symbols = set(config.symbols.keys())
    fixed_symbols.remove("default")
    updater = HotSymbolUpdater(config, fixed_symbols)

    try:
        await updater.start()
    except Exception:
        logger.error(f"Error: {traceback.format_exc()}")
        await asyncio.sleep(3)
    finally:
        await updater.stop() 

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

# async def run_trader_with_delay(trader:crypto_trader, delay:int):
#     await asyncio.sleep(delay)
#     await trader.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger = common_helper.Logger(__name__).get_logger()
        logger.error(f"Error: {e}")