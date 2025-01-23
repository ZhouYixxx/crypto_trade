from dataclasses import dataclass

@dataclass # 币种当前实时价格
class TickerPrice:
    ccy: str # 币种
    price: float # 价格
    timestamp: int # 时间戳

