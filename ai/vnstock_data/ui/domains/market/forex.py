'\nForex Market Data Domain.\n'
from vnstock_data.ui._registry import MARKET_SOURCES
from vnstock_data.ui.domains.market.base import BaseMarketData
class ForexMarket(BaseMarketData):
	'\n    Forex Market Data (Layer 2).\n    Provides access to historical pricing data for foreign exchange pairs via FXSB source.\n    ';trades=None;intraday=None;order_book=None;price_depth=None;session_stats=None;trading_stats=None
	def __init__(B,symbol,**A):super().__init__(symbol=symbol,domain_name=bytes([109,97,114,107,101,116,46,102,111,114,101,120]).decode(),layer_sources=MARKET_SOURCES,**A)