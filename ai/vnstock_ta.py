import pandas as pd
import ta
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volume import OnBalanceVolumeIndicator

class Indicator:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        # Ensure columns are lowercase
        self.df.columns = [str(c).lower() for c in self.df.columns]

    def ema(self, window: int) -> pd.Series:
        if "close" not in self.df.columns:
            return pd.Series([None] * len(self.df))
        return EMAIndicator(close=self.df["close"], window=window).ema_indicator()

    def rsi(self, window: int) -> pd.Series:
        if "close" not in self.df.columns:
            return pd.Series([None] * len(self.df))
        return RSIIndicator(close=self.df["close"], window=window).rsi()

    def obv(self) -> pd.Series:
        if "close" not in self.df.columns or "volume" not in self.df.columns:
            return pd.Series([None] * len(self.df))
        return OnBalanceVolumeIndicator(close=self.df["close"], volume=self.df["volume"]).on_balance_volume()
