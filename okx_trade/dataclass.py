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

@dataclass
class CommonConfig:
    interval: int
    flag: str

@dataclass
class Config:
    api: ApiConfig
    symbols: Dict[str, SymbolConfig]
    indicators: IndicatorsConfig
    email: EmailConfig
    common: CommonConfig
