import logging
from logging.handlers import TimedRotatingFileHandler
import os
import toml
import json
import time
from datetime import datetime, timedelta, time as dt_time
import types
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import dataclass
import aiohttp
import traceback
import numpy as np
import pandas as pd
import threading
from types import MappingProxyType


class Logger:
    _logger_instance = None
    _empty_line_lock = threading.Lock()

    def __init__(self, name, log_dir='logs', level=logging.INFO):
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        if Logger._logger_instance is not None:
            # 如果logger实例已经创建过，直接返回已存在的logger
            self.logger = Logger._logger_instance
            return
        
        # 创建一个logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        log_file = os.path.join(log_dir, f'trade.log')

        # 每天创建一个日志文件
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when='midnight',          # 'midnight' 表示每天午夜0:00创建新日志文件
            interval=1,   
            encoding='utf-8'
        )
        file_handler.suffix ='%Y-%m-%d'
        file_handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(message)s')

        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        #用于输出空行
        def log_newline(self, lines=1):
            with Logger._empty_line_lock:
                formatter = self.handlers[0].formatter 
                self.handlers[0].setFormatter(logging.Formatter(fmt=''))  
                for _ in range(lines):
                    self.info('')  
                self.handlers[0].setFormatter(formatter)

        self.logger.newline = types.MethodType(log_newline, self.logger)
        Logger._logger_instance = self.logger

    def get_logger(self):
        return self.logger

class Util:
    @staticmethod
    def send_email_outlook(sender_email:str, sender_password:str, smtp_server:str, smtp_port:int, receiver_emails:str, subject:str, body:str, logger:logging.Logger):
        try:
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = ','.join(receiver_emails)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                # server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, receiver_emails, msg.as_string())
                logger.info("send email successfully")
                return True
        except Exception as e:
            logger.error(f"Error sending email: {traceback.format_exc()}")
            return False


    @staticmethod
    async def send_feishu_message(webhook_url: str, message: str, logger:logging.Logger)->bool:
        """使用 Webhook 发送飞书消息"""
        try:
            headers = {"Content-Type": "application/json"}
            data = {
                "msg_type": "text",
                "content": {"text": message}
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    headers=headers,
                    data=json.dumps(data)
                ) as response:
                    resp = await response.json()
                    if resp['StatusMessage'] == 'success':
                        logger.info("发送飞书消息成功")
                        return True
                    else:
                        logger.info(f"发送飞书消息失败: StatusMessage = {resp['StatusMessage']}, StatusCode = {resp['StatusCode']}")
                        return False
        except Exception as e:
            logger.error(f"发送飞书消息失败: {traceback.format_exc()}")
            return False

    @staticmethod
    def load_config(file_path: str = 'config.toml') -> dataclass.Config:
        with open(file_path, 'r', encoding='utf-8') as file:
            config_data = toml.load(file)
        common_config = dataclass.CommonConfig(
            wait_seconds=config_data['common']['wait_seconds'],
            flag=config_data['common']['flag']
        )
        if common_config.flag == '0': #实盘
            api_config = dataclass.ApiConfig(
                key=config_data['api']['key'],
                secret=config_data['api']['secret'],
                passphase=config_data['api']['passphase'],
                base_url=config_data['api']['base_url']
            )
        else:
            api_config = dataclass.ApiConfig(
                key=config_data['demo_api']['key'],
                secret=config_data['demo_api']['secret'],
                passphase=config_data['demo_api']['passphase'],
                base_url=config_data['demo_api']['base_url']
            )
        
        symbols_config = {}
        for symbol_name, symbol_data in config_data['symbols'].items():
            symbols_config[symbol_name] = dataclass.SymbolConfig(
                instId=symbol_data['instId'],
                K_interval=symbol_data['K_interval'],
                bias=symbol_data['bias']
            )

        bollinger_bands_config = dataclass.BollingerBandsConfig(
            length=config_data['indicators']['bollinger_bands']['length'],
            multipler=config_data['indicators']['bollinger_bands']['multipler'],
            ma_type=config_data['indicators']['bollinger_bands']['ma_type']
        )

        indicators_config = dataclass.IndicatorsConfig(
            bollinger_bands=bollinger_bands_config
        )

        email_config = dataclass.EmailConfig(
            from_email=config_data['email']['from_email'],
            to_email=config_data['email']['to_email'],
            smtp_server=config_data['email']['smtp_server'],
            smtp_port=config_data['email']['smtp_port'],
            password=config_data['email']['password'],
            auth_163=config_data['email']['auth_163'],
            feishu_webhook=config_data['email']['feishu_webhook']
        )

        return dataclass.Config(
            api=api_config,
            symbols=symbols_config,
            indicators=indicators_config,
            email=email_config,
            common=common_config
        )
    
    @staticmethod
    def price2str(price)->str:
        price = float(price)
        if price < 10**-5:
            return f"{round(price, 9):.10f}"
        if price < 10**-4:
            return f"{round(price, 7):.10f}"
        if price < 10**-3:
            return f"{round(price, 5):.10f}"
        if price < 1:
            return f"{round(price, 4):.10f}"
        elif price < 100:
            return f"{round(price, 3):.10f}"
        elif price < 10000:
            return f"{round(price, 2):.10f}"
        else:
            return f"{round(price, 1):.10f}"
        
    
    @staticmethod
    def str2mins(str:str)->int:
        if str.endswith("m"): return int(str[:-1])
        if str.endswith("H"): return int(str[:-1]) * 60
        if str.endswith("D"): return int(str[:-1]) * 24 * 60
        if str.endswith("W"): return int(str[:-1]) * 24 * 60 * 7
        if str.endswith("M"): return int(str[:-1]) * 24 * 60 * 7 * 30 # 月份求出大概值即可

    @staticmethod
    def find_consecutive_groups(df:pd.DataFrame, min_days=3, direction=1)->pd.DataFrame:
        """识别连续涨跌的时期

        Args:
            df (pd.DataFrame): 数据源, 必须按timestamp升序排列
            min_days (int, optional): 要统计的连续上涨/下跌的最小天数. Defaults to 3.
            direction (int, optional): 方向 1=上涨, -1 = 下跌. Defaults to 1.

        Returns:
            pd.DataFrame: ['start_date','end_date','days','start_price','end_price']
        """
        # 计算每日涨跌幅（当日收盘价对比前一日收盘价）
        if 'pct_change' not in df.columns:
            df['pct_change'] = df['close'].pct_change() * 100

        # 标记涨跌状态 (1: 上涨, -1: 下跌, 0: 平盘)
        if 'direction' not in df.columns:
            df['direction'] = 0
            df.loc[df['pct_change'] > 0, 'direction'] = 1
            df.loc[df['pct_change'] < 0, 'direction'] = -1

        # 创建变化点标记
        df['change_point'] = df['direction'].ne(df['direction'].shift())
        df['group_id'] = df['change_point'].cumsum()
        
        # 筛选指定方向的组
        groups = df.groupby('group_id')
        result = []
        
        for group_id, group_df in groups:
            if len(group_df) >= min_days and group_df['direction'].iloc[0] == direction:
                start_date = group_df['timestamp'].iloc[0]
                end_date = group_df['timestamp'].iloc[-1]
                days = len(group_df)
                start_price = group_df['open'].iloc[0]  # 使用第一天的开盘价作为起始价
                end_price = group_df['close'].iloc[-1]   # 使用最后一天的收盘价作为结束价
                high_price = group_df['high'].max()
                low_price = group_df['low'].min()
                total_pct = (end_price - start_price) / start_price * 100
                max_volatility = (high_price - low_price) / start_price * 100

                result.append({
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'days': days,
                    'start_price': round(start_price, 4),
                    'end_price': round(end_price, 4),
                    'high_price': round(high_price, 4),
                    'low_price': round(low_price, 4),
                    'total_pct': f'{round(total_pct, 2)}%',
                    'max_volatility': f'{round(max_volatility, 2)}%'
                })
        
        return pd.DataFrame(result)



class ImmutableViewDict:
    """用于保存/更新 高频读取、低频更新的字典对象
    """
    def __init__(self):
        self._data = {}
        self._view = MappingProxyType(self._data)
        self._lock = threading.Lock()

        # 启动定时清空线程
        self.clear_time = "00:01"
        self._running = True
        self._clear_thread = threading.Thread(target=self._daily_clear)
        self._clear_thread.daemon = True
        self._clear_thread.start()
    
    def get(self, key):
        # 无锁读取不可变视图
        return self._view.get(key)
    
    def update(self, key, value, save_to_file:bool = True):
        # 加锁更新
        with self._lock:
            self._data[key] = value
            if save_to_file:
                self._save_to_file()

    def _save_to_file(self, filename='last_send_time.json'):
        """内部方法：保存字典到文件"""
        with open(filename, 'w') as f:
            json.dump(self._data, f, indent=2)

    def get_all(self):
        # 无锁读取不可变视图
        return self._view.items()
    
    def _daily_clear(self):
        """每日定时清空字典的线程函数"""
        while self._running:
            now = datetime.now()
            target_time = dt_time(*map(int, self.clear_time.split(':')))
            
            # 计算到下次清空时间的秒数
            target_datetime = datetime.combine(now.date(), target_time)
            if now >= target_datetime:
                target_datetime = datetime.combine(now.date() + timedelta(days=1), target_time)
            
            wait_seconds = (target_datetime - now).total_seconds()
            time.sleep(wait_seconds)
            
            # 执行清空操作
            with self._lock:
                self._data.clear()
                # 可选：清空后立即保存空字典到文件
                self._save_to_file()

