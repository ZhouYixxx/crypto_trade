# import os
# import okx_api_async
# import time
import asyncio
import copy
import common_helper
import strategies.rumi as stgy1
from quote_monitor import crypto_quote_monitor
from typing import Dict, List, Set
from update_task import HotSymbolUpdater
import traceback
from okx_api_async import OKXAPI_Async_Wrapper 
import numpy as np
import datetime as dt
import pandas as pd
import math
import talib
from trader import CryptoTrader
from globals import global_instance


async def main():
    # rumi = stgy1.rumi("BTC-USDT-SWAP")
    # await rumi.backtest()

    logger = common_helper.Logger(__name__).get_logger()
    logger.info(f"币种配置信息系: {global_instance.config.symbols}")
    message_queue = asyncio.Queue()


    logger.info("行情监控程序启动......")
    logger.newline()

    fixed_symbols = set(global_instance.config.symbols.keys())
    fixed_symbols.remove("default")
    updater = HotSymbolUpdater(config=global_instance.config, initial_hot_symbols=fixed_symbols, message_queue=message_queue)
    trader = CryptoTrader(name="trader", message_queue=message_queue)

    try:
        await asyncio.gather(
            updater.start(),  # 启动更新任务
            trader.start()  # 启动交易任务
        )   
        # await updater.start()
        # await trader.start() 
    except Exception:
        logger.error(f"Error: {traceback.format_exc()}")
        await asyncio.sleep(3)
    finally:
        await updater.stop()
        updater = None
        trader.stop() 

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


def signal_order(df:pd.DataFrame, down_groups:pd.DataFrame, up_groups:pd.DataFrame):
    """思路: 以下跌为例 
        日线级别: 连续下跌超过至少3日, 总跌幅超过设定值(例如20%), 就择机开始做多.
        1H级别: 计算RSV值, RSV2 <= 20 且出现RSV2与RSV12的金叉. 
    Args:
        df (pd.DataFrame): _description_
        down_groups (pd.DataFrame): _description_
        up_groups (pd.DataFrame): _description_

    Returns:
        _type_: _description_
    """
    dec = 0.225
    result = []
    for index, row in down_groups.iterrows():
        start_date = row["start_date"]
        end_date = row["end_date"]
        start_price = row['start_price']
        current_day = 3

        begin = pd.Timestamp(start_date, tz='Asia/Hong_Kong')
        # 第三天的开始触发
        begin = begin + pd.Timedelta(days=2)
        end = pd.Timestamp(end_date, tz='Asia/Hong_Kong')
        df_days = df[(df['timestamp'] >= begin) & (df['timestamp'] <= end)]
        for index, df_row in df_days.iterrows():
            open_price = start_price * (1- dec)
            if df_row['low'] <= open_price:
                result.append({
                    'open_date': df_row['timestamp'].strftime('%Y-%m-%d'), #(dt.datetime.fromtimestamp(df_row['timestamp']/1000)+ dt.timedelta(hours=8)).strftime('%Y-%m-%d'),
                    'open_price': open_price,
                    'direction': '开仓做多'
                })
                break
            elif current_day >= 5:
                #单边行情超过5天
                open_price = start_price * (1-0.18) #单边行情超过5天
                if df_row['low'] <= open_price:
                    result.append({
                        'open_date': df_row['timestamp'].strftime('%Y-%m-%d'), #(dt.datetime.fromtimestamp(df_row['timestamp']/1000)+ dt.timedelta(hours=8)).strftime('%Y-%m-%d'),
                        'open_price': open_price,
                        'direction': '开仓做多'
                    })
                    break
                break
            current_day += 1

    rise = 0.225
    for index, row in up_groups.iterrows():
        start_date = row["start_date"]
        end_date = row["end_date"]
        start_price = row['start_price']
        current_day = 3
        open_price = start_price * (1 + rise)

        # 第三天的timestamp
        begin = pd.Timestamp(start_date, tz='Asia/Hong_Kong')
        begin = begin + pd.Timedelta(days=2)
        end = pd.Timestamp(end_date, tz='Asia/Hong_Kong')
        df_days = df[(df['timestamp'] >= begin) & (df['timestamp'] <= end)]
        for index, df_row in df_days.iterrows():
            if df_row['high'] >= open_price:
                result.append({
                    'open_date': df_row['timestamp'].strftime('%Y-%m-%d'), #(dt.datetime.fromtimestamp(df_row['timestamp']/1000)+ dt.timedelta(hours=8)).strftime('%Y-%m-%d'),
                    'open_price': open_price,
                    'direction': '开仓做空'
                })
                break
            elif current_day >= 5:
                open_price = start_price * (1 + 0.18) #单边行情超过5天
                if df_row['high'] >= open_price:
                    result.append({
                        'open_date': df_row['timestamp'].strftime('%Y-%m-%d'), #(dt.datetime.fromtimestamp(df_row['timestamp']/1000)+ dt.timedelta(hours=8)).strftime('%Y-%m-%d'),
                        'open_price': open_price,
                        'direction': '开仓做空'
                    })
                    break
            current_day += 1

    return pd.DataFrame(result).sort_values('open_date', ascending=True)
            


def calculate_bollinger_bands(df, length = 20, multiplier = 2):
    close_prices = df['close'].values
    upper, middle, lower = talib.BBANDS(
        close_prices,  # 收盘价数据
        timeperiod=length,  # 布林带周期
        nbdevup=multiplier,  # 上轨倍数
        nbdevdn=multiplier,  # 下轨倍数
        matype=talib.MA_Type.SMA  # 使用简单移动平均线
    )
    # df['upper'] = upper[::-1] # 返回的结果以时间降序排列，即arr[0] 为最新价格，arr[-1]为最老价格
    # df['middle'] = middle[::-1]
    # df['lower'] = lower[::-1]
    df['upper'] = upper # 返回的结果以时间降序排列，即arr[0] 为最新价格，arr[-1]为最老价格
    df['middle'] = middle
    df['lower'] = lower
    return df

def bband_signal(df:pd.DataFrame, bias:float = 2)->pd.DataFrame:
    result = []
    for index, df_row in df.iterrows():
        close = df_row['close'] # 最新收盘价
        high = df_row['high'] 
        low = df_row['low'] 
        upper_band = df_row['upper']  # 最新上轨
        lower_band = df_row['lower']  # 最新下轨
        middle_band = df_row['middle']  # 最新中轨
        if math.isnan(upper_band):
            continue
        date = df_row['timestamp'].strftime('%Y-%m-%d')
        # if date == '2024-04-14':
        #     msg = "test on"
        delta = (upper_band - middle_band) / 2
        if high >= upper_band + delta * bias:
            result.append({
                'open_date': df_row['timestamp'].strftime('%Y-%m-%d'), #(dt.datetime.fromtimestamp(df_row['timestamp']/1000)+ dt.timedelta(hours=8)).strftime('%Y-%m-%d'),
                'open_price': upper_band + delta * bias,
                'direction': '开仓做空'
            })
        elif low <= lower_band - delta * bias:
            result.append({
                'open_date': df_row['timestamp'].strftime('%Y-%m-%d'), #(dt.datetime.fromtimestamp(df_row['timestamp']/1000)+ dt.timedelta(hours=8)).strftime('%Y-%m-%d'),
                'open_price': lower_band - delta * bias,
                'direction': '开仓做多'
            })
    return pd.DataFrame() if result == [] else pd.DataFrame(result).sort_values('open_date', ascending=True)
        

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger = common_helper.Logger(__name__).get_logger()
        logger.error(f"Error: {e}")
        print(f"Error: {e}")