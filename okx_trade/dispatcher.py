from quote_monitor import crypto_quote_monitor

class MarketDataDispatcher:
    """市场行情消息分发
    """
    def __init__(self):
        self.subscribers = set[crypto_quote_monitor]()
    
    def subscribe(self, subscriber:crypto_quote_monitor):
        """交易者订阅行情数据"""
        self.subscribers.add(subscriber)
    
    def unsubscribe(self, subscriber):
        """交易者取消订阅"""
        self.subscribers.discard(subscriber)
    
    def dispatch(self, market_data_msg):
        """分发行情数据给所有订阅者"""
        for subscriber in self.subscribers:
            subscriber.on_market_data(market_data_msg)