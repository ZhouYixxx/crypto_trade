import logging
from logging.handlers import TimedRotatingFileHandler
import os

class Logger:
    def __init__(self, name, log_dir='logs', level=logging.INFO):
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
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

    def get_logger(self):
        return self.logger
