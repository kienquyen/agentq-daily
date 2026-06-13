'\nEquity Market Data Domain.\n'
import pandas as pd
from vnstock_data.ui._registry import MARKET_SOURCES
from vnstock_data.ui.domains.market.base import BaseMarketData
class EquityMarket(BaseMarketData):
	'\n    Equity Market Data (Layer 2).\n    Provides standard methods (history, intraday, price_depth, price_board)\n    plus specialized flow and statistics models for Equities.\n    '
	def __init__(A,symbol):super().__init__(symbol=symbol,domain_name=bytes([109,97,114,107,101,116,46,101,113,117,105,116,121]).decode(),layer_sources=MARKET_SOURCES)
	def foreign_flow(A,**B):'\n        Historical or daily foreign buy/sell volume and value.\n        ';return A._dispatch(bytes([102,111,114,101,105,103,110,95,102,108,111,119]).decode(),**B)
	def trade_history(A,**B):'\n        Historical trading statistics (price, volume, value) for Equities.\n        ';return A._dispatch(bytes([112,114,105,99,101,95,104,105,115,116,111,114,121]).decode(),**B)
	def proprietary_flow(A,**B):'\n        Trade data for proprietary desks (Tự doanh).\n        ';return A._dispatch(bytes([112,114,111,112,114,105,101,116,97,114,121,95,102,108,111,119]).decode(),**B)
	def box_trades(A):0
	def block_trades(B,limit=1000,**A):
		'\n        Real-time or historical data for negotiated/block trades (giao dịch thoả thuận).\n        \n        Args:\n            limit (int): Number of records to fetch (default: 1000).\n        '
		if bytes([112,97,103,101,95,115,105,122,101]).decode()not in A:A[bytes([112,97,103,101,95,115,105,122,101]).decode()]=limit
		return B._dispatch(bytes([98,108,111,99,107,95,116,114,97,100,101,115]).decode(),**A)
	def put_through(A,**B):'Alias for block_trades (Negotiated Trades).';return A.block_trades(**B)
	def odd_lot(B,**A):
		'\n        Real-time pricing or trades for odd-lot execution (Lô lẻ).\n        '
		if bytes([115,121,109,98,111,108,115,95,108,105,115,116]).decode()not in A:A[bytes([115,121,109,98,111,108,115,95,108,105,115,116]).decode()]=[B.symbol]
		return B._dispatch(bytes([111,100,100,95,108,111,116]).decode(),**A)
	def volume_profile(A,**B):'\n        Aggregated volume distributed across executed price levels (Volume Profile).\n        ';return A._dispatch(bytes([118,111,108,117,109,101,95,112,114,111,102,105,108,101]).decode(),**B)
	def matched_by_price(A,**B):'Alias for volume_profile.';return A.volume_profile(**B)