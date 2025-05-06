from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ApiConfig:
    key: str
    secret: str
    passphase: str
    base_url: str

@dataclass
class SymbolConfig:
    instId: str
    K_interval: str
    bias: float

@dataclass
class BollingerBandsConfig:
    length: int
    multipler: int
    ma_type: str

@dataclass
class IndicatorsConfig:
    bollinger_bands: BollingerBandsConfig

@dataclass
class EmailConfig:
    from_email: str
    to_email: List[str]
    smtp_server: str
    smtp_port: int
    password: str
    auth_163: str
    feishu_webhook:str

@dataclass
class CommonConfig:
    wait_seconds: int # 监控间隔, 单位: 秒
    flag: str

@dataclass
class Config:
    api: ApiConfig
    symbols: Dict[str, SymbolConfig]
    indicators: IndicatorsConfig
    email: EmailConfig
    common: CommonConfig

@dataclass
class SignalMessage:
    """由交易策略发送的消息
    """
    sender: str
    content: str
    instId: str 
    price: float # 当前价格
    # threshold_price: float # 触发条件的阈值
    direction: int # 行情方向, 1 = 上涨  -1 = 下跌, 0 = 无信号
    triggerd: bool # 触发条件是否满足, True: 满足, False: 不满足
