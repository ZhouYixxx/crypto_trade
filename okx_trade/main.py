import os
import okx_api_async
import quote_monitor
import time
import asyncio


FLAG = "0"  # live trading: 0, demo trading: 1
# 布林带参数
LENGTH = 20  # 布林带周期
MULTIPLIER = 2  # 布林带倍数
INST_ID = 'BTC-USDT-SWAP'  # 交易对
INTERVAL = '4H'  # K线周期，例如 4小时
Bias = 0.5 # 偏置，理解为价格突破上轨后，还要再上涨0.5个标准差才能触发

Auth_163 = "YMbXMY87PuJmFbZ2"

# 主函数
async def main():
    # 使用示例
    # send_email_outlook(
    #     sender_email="zhouyi9211@163.com",
    #     sender_password=Auth_163,
    #     receiver_emails=["zhouyiwenyu@outlook.com", "joey.zhou@dfzq.com.hk"],
    #     subject="BTC Test Email",
    #     body=f"{SYMBOL} 价格突破{INTERVAL}K线上轨! 最新价: 97500, 上轨: 97000"
    # )
    while True:
        # 获取K线数据
        df = await quote_monitor.get_candles(INST_ID, INTERVAL)
        if df is not None:
            # 使用 TA-Lib 计算布林带
            df = quote_monitor.calculate_bollinger_bands(df, LENGTH, MULTIPLIER)
            # 监控价格突破
            quote_monitor.monitor_breakout(df)
        # 每隔一段时间运行一次（例如每5分钟）
        time.sleep(180)  # 300秒 = 5分钟



if __name__ == "__main__":
    asyncio.run(main())