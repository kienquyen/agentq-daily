'\nCommodity Market Data Domain.\n'
from vnstock_data.ui._registry import MARKET_SOURCES
from vnstock_data.ui.domains.market.base import BaseMarketData
class CommodityMarket(BaseMarketData):
	'\n    Commodity Market Data (Layer 2).\n    Provides access to historical pricing data for commodities via FXSB source.\n    ';trades=None;intraday=None;order_book=None;price_depth=None;session_stats=None;trading_stats=None
	def __init__(B,symbol,**A):super().__init__(symbol=symbol,domain_name=bytes([109,97,114,107,101,116,46,99,111,109,109,111,100,105,116,121]).decode(),layer_sources=MARKET_SOURCES,**A)