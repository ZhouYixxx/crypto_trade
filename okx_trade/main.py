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
from okx_api_async import OKXAPI_Async_Wrapper 
import numpy as np
import datetime as dt
import pandas as pd
import math
import talib


async def main():
    # rumi = stgy1.rumi("BTC-USDT-SWAP")
    # await rumi.backtest()
    config = common_helper.Util.load_config()
    logger = common_helper.Logger(__name__).get_logger()

    # await common_helper.Util.send_feishu_message(webhook_url=config.email.feishu_webhook, message="这是测试消息 \n 换行")
    start = "1727740800000" #20241001
    end = "1743465600000" #20250401
    start = "2025-01-01"
    end = "2025-04-10"



    response = await OKXAPI_Async_Wrapper.get_history_candles_async(instId="SOL-USDT-SWAP", interval="4H", start=start, end=end)
    data = response['data']
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
    # 转换数据类型
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms',utc=True).map(lambda t: t.tz_convert('Asia/Hong_Kong'))  # OKX的时间戳通常是毫秒级, 转化UTC+8
    df = df.sort_values('timestamp', ascending=True)
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)

    df = calculate_bollinger_bands(df)
    res = bband_signal(df)
    print(res.to_string())

    # # 计算每日涨跌幅（正确的计算方式：当日收盘价对比前一日收盘价）
    # df['pct_change'] = df['close'].pct_change() * 100

    # # 标记涨跌状态 (1: 上涨, -1: 下跌, 0: 平盘)
    # df['direction'] = 0
    # df.loc[df['pct_change'] > 0, 'direction'] = 1
    # df.loc[df['pct_change'] < 0, 'direction'] = -1
    # min_days = 3
    # # 统计连续下跌超过3天的组
    # print(f"统计区间{start} ~~ {end}")
    # down_groups = common_helper.Util.find_consecutive_groups(df=df, min_days=min_days, direction=-1)
    # print(f"连续下跌超过{min_days}天的组:")
    # print(down_groups.to_string(index=False))
    # print(f"\n总共有 {len(down_groups)} 组连续下跌超过{min_days}天的K线")

    # # 统计连续上涨超过3天的组
    # up_groups = common_helper.Util.find_consecutive_groups(df=df, min_days=min_days, direction=1)
    # print(f"\n连续上涨超过{min_days}天的组:")
    # print(up_groups.to_string(index=False))
    # print(f"\n总共有 {len(up_groups)} 组连续上涨超过{min_days}天的K线")

    # orders = signal_order(df, down_groups, up_groups)

    # print(f"\n总共有 {len(orders)} 次触发下单")
    # print(orders.to_string(index=False))

    logger.info("行情监控程序启动......")
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


def signal_order(df:pd.DataFrame, down_groups:pd.DataFrame, up_groups:pd.DataFrame):
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

def bband_signal(df:pd.DataFrame)->pd.DataFrame:
    result = []
    bias = 1.75
    for index, df_row in df.iterrows():
        close = df_row['close'] # 最新收盘价
        high = df_row['high'] 
        low = df_row['low'] 
        upper_band = df_row['upper']  # 最新上轨
        lower_band = df_row['lower']  # 最新下轨
        middle_band = df_row['middle']  # 最新中轨
        if math.isnan(upper_band):
            continue
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
    return pd.DataFrame(result).sort_values('open_date', ascending=True)
        

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger = common_helper.Logger(__name__).get_logger()
        logger.error(f"Error: {e}")
        print(f"Error: {e}")