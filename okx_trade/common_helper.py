import logging
from logging.handlers import TimedRotatingFileHandler
import os
import toml
import json
import math
from datetime import datetime

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import dataclass

class Logger:
    _logger_instance = None

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

        # 创建控制台处理器
        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(message)s')

        file_handler.setFormatter(formatter)
        # console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        # self.logger.addHandler(console_handler)

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
            logger.error(f"Error sending email: {e}")
            return False


    @staticmethod
    def load_config(file_path: str = 'config.toml') -> dataclass.Config:
        with open(file_path, 'r', encoding='utf-8') as file:
            config_data = toml.load(file)

        api_config = dataclass.ApiConfig(
            key=config_data['api']['key'],
            secret=config_data['api']['secret'],
            passphase=config_data['api']['passphase'],
            base_url=config_data['api']['base_url']
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
            auth_163=config_data['email']['auth_163']
        )

        common_config = dataclass.CommonConfig(
            interval=config_data['common']['interval'],
            flag=config_data['common']['flag']
        )

        return dataclass.Config(
            api=api_config,
            symbols=symbols_config,
            indicators=indicators_config,
            email=email_config,
            common=common_config
        )
    

    def read_last_send_time(instid, filename='last_send_time.json'):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                return datetime.strptime(data[instid], "%Y-%m-%d %H:%M:%S")
        except (FileNotFoundError, KeyError):
            return None

    def update_last_send_time(instid, filename='last_send_time.json'):
        try:
            with open(filename, 'r+') as f:
                data = json.load(f)
                data[instid] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.seek(0)  
                json.dump(data, f, indent=4)
                f.truncate()  # 确保原有多余的内容被截断
        except (FileNotFoundError, json.JSONDecodeError):
            # 如果文件不存在或者格式错误，重新创建文件
            data = {instid: datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
    
    @staticmethod
    def price2str(price)->str:
        price = float(price)
        if price < 1:
            return round(price, 4)
        elif price < 100:
            return round(price, 3)
        elif price < 10000:
            return round(price, 2)
        else:
            return round(price, 1)
