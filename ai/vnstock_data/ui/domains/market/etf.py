from vnstock_data.ui._registry import MARKET_SOURCES
from vnstock_data.ui.domains.market.base import BaseMarketData
class ETFMarket(BaseMarketData):
	'\n    Electronic Traded Funds (ETF) market data domain.\n    Provides access to quotes, trades, and history for ETF symbols.\n    '
	def __init__(A,symbol):super().__init__(symbol,bytes([109,97,114,107,101,116,46,101,116,102]).decode(),MARKET_SOURCES)