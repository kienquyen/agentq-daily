'\nIndex Market Data Domain.\n'
import pandas as pd
from vnstock_data.ui._registry import MARKET_SOURCES
from vnstock_data.ui.domains.market.base import BaseMarketData
class IndexMarket(BaseMarketData):
	'\n    Index Market Data (Layer 2).\n    ';trades=None;intraday=None;order_book=None;price_depth=None
	def __init__(D,symbol,**A):
		C=A.pop(bytes([115,99,111,112,101]).decode(),'');B=MARKET_SOURCES.copy()
		if C==bytes([103,108,111,98,97,108]).decode():B[bytes([109,97,114,107,101,116,46,105,110,100,101,120]).decode()]={bytes([111,104,108,99,118]).decode():(bytes([100,117,107,97,115,99,111,112,121]).decode(),bytes([113,117,111,116,101]).decode(),bytes([81,117,111,116,101]).decode(),bytes([104,105,115,116,111,114,121]).decode()),bytes([105,110,116,114,97,100,97,121]).decode():(bytes([100,117,107,97,115,99,111,112,121]).decode(),bytes([113,117,111,116,101]).decode(),bytes([81,117,111,116,101]).decode(),bytes([105,110,116,114,97,100,97,121]).decode())}
		super().__init__(symbol=symbol,domain_name=bytes([109,97,114,107,101,116,46,105,110,100,101,120]).decode(),layer_sources=B,**A)
	def trade_history(A,**B):'\n        Historical trading statistics (price, volume, value) for Indices.\n        ';return A._dispatch(bytes([112,114,105,99,101,95,104,105,115,116,111,114,121]).decode(),**B)