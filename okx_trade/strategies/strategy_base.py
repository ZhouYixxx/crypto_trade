from abc import ABC, abstractmethod
import dataclass
import pandas as pd
from typing import List


class StrategyBase(ABC):
    """
    Abstract base class for trading strategies
    """
    
    @abstractmethod
    def SignalRaise(self, df_list: List[pd.DataFrame]) -> dataclass.SignalMessage:
        """
        Abstract method to generate trading signals
        """
        pass