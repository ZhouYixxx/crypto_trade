import aiohttp
import asyncio
import time
import hmac
import base64
from urllib.parse import urlencode
from common_helper import Logger
from common_helper import Util
import datetime as dt
import re


logger = Logger(__name__).get_logger()
config = Util.load_config()
# OKX API配置
_API_KEY = config.api.key
_SECRET_KEY = config.api.secret
_PASSPHRASE = config.api.passphase
_BASE_URL = config.api.base_url

class OKXAPI_Async_Wrapper:

    @staticmethod
    async def get_candlesticks_async(instId, interval, limit):
        """
        获取K线数据
        """

        endpoint = "/api/v5/market/candles"
        method = 'GET'
        params = {
            "instId": instId,
            "bar": interval,
            "limit": limit
        }
        
        requestPath = f"{endpoint}?{urlencode(params)}"
        url = f"{_BASE_URL}{requestPath}"

        # 生成签名
        timestamp = str(int(time.time()))
        signature = OKXAPI_Async_Wrapper.__generate_signature(_SECRET_KEY, timestamp, method, requestPath)
        return await OKXAPI_Async_Wrapper.__http_request(url, timestamp, signature, method)



    @staticmethod
    async def get_history_candles_async(instId, interval, start="", end=""):
        """获取从before到after这一段时间内的历史行情K线数据
        Args:
            instId (_type_): 币种
            interval (_type_): K线级别
            after (str, optional): 结束时间(不包括本身), 例如 "2024-05-01 12:30:00". Defaults to "".
            before (str, optional): 开始时间(不包括本身). 例如 "2024-05-01 12:30:00". Defaults to "".

        Returns:
            {
                "code":"0",
                "msg":"",
                "data":[
                [
                    "1597026383085",
                    "3.721",
                    "3.743",
                    "3.677",
                    "3.708",
                    "8422410",
                    "22698348.04828491",
                    "12698348.04828491",
                    "1"
                ],
                [...]]
            }
        """
        if len(start) == 10:  # 纯日期
            start += " 00:00:00"
        if len(end) == 10:  # 纯日期
            end += " 23:59:59"
        start_ts:int = round(dt.datetime.strptime(start, "%Y-%m-%d %H:%M:%S").timestamp()) * 1000 if start != "" else 0 
        end_ts:int = round(dt.datetime.strptime(end, "%Y-%m-%d %H:%M:%S").timestamp()) * 1000 if end != "" else round(dt.datetime.timestamp(dt.datetime.now()))* 1000 
        end = f"{end_ts}"
        start = f"{start_ts}"
        unit = Util.str2mins(interval)
        count = round((end_ts - start_ts) / (unit * 60 * 1000))
        if count < 100:
            return await OKXAPI_Async_Wrapper.__get_history_candles_internal(instId, interval, end, start, limit="100")
        merged_data = []
        while count > 0:
            response = (await OKXAPI_Async_Wrapper.__get_history_candles_internal(instId=instId, after=end, before="", interval=interval, limit="100") 
                        if count > 100 else 
                        await OKXAPI_Async_Wrapper.__get_history_candles_internal(instId=instId, after=end, before=start, interval=interval, limit=""))
            if response is None or response["code"] != "0":
                merged_resp = {
                    "code": response["code"],
                    "msg": response["msg"],
                    "data": []
                }
                return merged_resp
            end = response["data"][-1][0]
            merged_data.extend(response["data"])
            count -= 100
            await asyncio.sleep(0.2) # OKX对接口有限流
        merged_resp = {
            "code": "0",
            "msg": "",
            "data": merged_data
        }
        return merged_resp

    @staticmethod
    async def __get_history_candles_internal(instId, interval, after="", before="", limit = "100"):
        """
        获取历史K线数据
        """

        endpoint = "/api/v5/market/history-candles"
        method = 'GET'
        params = {
            "instId": instId,
            "after": after,
            "before": before,
            "bar": interval,
            "limit": limit
        }
        
        requestPath = f"{endpoint}?{urlencode(params)}"
        url = f"{_BASE_URL}{requestPath}"

        # 生成签名
        timestamp = str(int(time.time()))
        signature = OKXAPI_Async_Wrapper.__generate_signature(_SECRET_KEY, timestamp, method, requestPath)
        return await OKXAPI_Async_Wrapper.__http_request(url, timestamp, signature, method)

    @staticmethod
    async def get_tickers_async(instType, uly = '', instFamily = ''):
        """
        获取所有产品行情信息
        """

        endpoint = "/api/v5/market/tickers"
        method = 'GET'
        params = {
            "instType": instType,
            "uly": uly,
            "instFamily": instFamily
        }
        
        requestPath = f"{endpoint}?{urlencode(params)}"
        url = f"{_BASE_URL}{requestPath}"

        # 公共接口无需签名
        return await OKXAPI_Async_Wrapper.__http_request(url, "", "", method)

    @staticmethod
    async def get_account_balance_async(ccy = ''):
        """
        查看交易账户余额
        """

        endpoint = "/api/v5/account/balance"
        method = 'GET'
        params = {
            "ccy": ccy,
        }
        requestPath = f"{endpoint}?{urlencode(params)}"
        url = f"{_BASE_URL}{requestPath}"

        # 生成签名
        timestamp = str(int(time.time()))
        signature = OKXAPI_Async_Wrapper.__generate_signature(_SECRET_KEY, timestamp, method, requestPath)

        return await OKXAPI_Async_Wrapper.__http_request(url, timestamp, signature, method)


    @staticmethod
    async def place_order_async(instId, tdMode, side, ordType, sz, px):
        """
        下单接口

        参数:
        instId (string): 币种类型 \n
        tdMode(string): 交易模式, 现货=cash, 合约逐仓 = isolated, 全仓= cross \n
        side(string): 订单方向 buy/sell \n
        ordType(string):订单类型 market/limit \n
        sz(string): 委托数量 \n
        px(string): 委托价格 \n

        """

        endpoint = "/api/v5/trade/order"
        method = 'POST'
        requestPath = f"{endpoint}"
        url = f"{_BASE_URL}{requestPath}"
        body = {
            instId: instId,
            tdMode: tdMode,
            side: side,
            ordType: ordType,
            sz: sz,
            px: px
        }
        # 生成签名
        timestamp = str(int(time.time()))
        signature = OKXAPI_Async_Wrapper.__generate_signature(_SECRET_KEY, timestamp, method, requestPath, body)

        return await OKXAPI_Async_Wrapper.__http_request(url, timestamp, signature, method)




    # 生成签名
    def __generate_signature(secret_key, timestamp, method, requestPath, body = ''):
        message = timestamp + method + requestPath + body
        message_bytes = message.encode('utf-8')
        hmac_key = hmac.new(secret_key.encode('utf-8'), message_bytes, digestmod='sha256')
        return base64.b64encode(hmac_key.digest()).decode('utf-8')
    

    async def __http_request(url, timestamp, signature, method):
        if signature:
            headers = {
                "OK-ACCESS-KEY": _API_KEY,
                "OK-ACCESS-SIGN": signature,
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": _PASSPHRASE,
                "Content-Type": "application/json"
            }
        else:
            headers = {}
        async with aiohttp.ClientSession() as session:
            if method == 'GET':
                request_func = session.get
            elif method == 'POST':
                request_func = session.post
            else:
                logger.error(f"Unsupported method: {method}")
                return None

            async with request_func(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"net error: {response.status}")
                    return None
                data = await response.json()
                if data.get('code') != '0':
                    logger.error(f"error code = {data['code']}, message = {data['msg']}")
                    return None
                return data