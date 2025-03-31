import tushare
import numpy as np
import pandas as pd
import talib
import matplotlib.pyplot as plt
import warnings
from okx_api_async import OKXAPI_Async_Wrapper


warnings.filterwarnings('ignore')

class rumi:
    def __init__(self, inst_id):
        self.inst_id = inst_id
    async def backtest(self) -> None:
        # 历史行情数据
        # data = tushare.get_k_data(code='hs300', start = '2018-01-01', end = '2023-11-18', ktype = 'D')
        response = await OKXAPI_Async_Wrapper.get_history_candles_async(instId=self.inst_id, after='1732032000000', before='', interval='1D')
        data = pd.DataFrame(response['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
        data = data.set_index('date')
        data.index = pd.to_datetime(data.index)
        data = data[['open','close','high','low']]
        data['pct'] = data['close'].shift(-1)/data['close']-1 #计算每日收益率
        
        #计算rumi
        data['fast'] = talib.SMA(data['close'].values, timeperiod = 3)
        data['slow'] = talib.WMA(data['close'].values, timeperiod = 50)
        data['diff'] = data['fast']-data['slow']
        data['rumi'] = talib.SMA(data['diff'].values, timeperiod = 30)
        data = data.dropna()
        
        #back test
        data['strategy_pct']=data.apply(lambda x: x.pct \
                        if x.rumi > 0 else -x.pct, axis=1)
        data['strategy'] = (1.0 + data['strategy_pct']).cumprod()
        data['benchmark'] = (1.0 + data['pct']).cumprod()
        annual_return = 100 * (pow(data['strategy'].iloc[-1], 250/data.shape[0]) - 1.0)
        print('Annual return for HS300 with RUMI is：%.2f%%' %annual_return)
        ax = data[['strategy','benchmark']].plot(title=f'Selection of {self.inst_id} using RUMI')
        plt.show()

    def run()->None:
        #运行策略
        print('run')
