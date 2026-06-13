'\nBase classes for unified Market Data access (Layer 2).\nProvides the universal market data namespace across all instrument types.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDetail
class BaseMarketData(BaseDetail):
	'\n    Unified base class for fetching market data across all asset classes\n    (Equity, Index, Futures, Warrant).\n    \n    Provides standardized methods aligned with international schemas\n    (OHLCV, Time & Sales, Order Book, Quote Snapshots) while retaining\n    familiar terminology for backward compatibility.\n    '
	def ohlcv(A,**B):"\n        Historical OHLCV bars.\n        \n        Args:\n            start (str): Start date (YYYY-MM-DD). Optional if count_back is provided.\n            end (str): End date (YYYY-MM-DD). Default is today.\n            interval (str): Timeframe interval ('1D', '1W', '1M', '1m', '5m', '15m', '1H').\n            count_back (int): Number of bars to fetch backward from end date.\n            \n        Returns:\n            pd.DataFrame: OHLCV data adhering to `market.ohlcv` schema.\n        ";return A._dispatch(bytes([111,104,108,99,118]).decode(),**B)
	def history(A,**B):'\n        [Backward Compatible Alias] Relays to `.ohlcv()`.\n        Provides historical candlestick bars.\n        ';return A.ohlcv(**B)
	def trades(B,limit=1000,**A):
		'\n        Real-time or intraday tick-by-tick trading tape (Time & Sales).\n        \n        Args:\n            limit (int): Number of records to fetch (default: 1000).\n            page (int): Page number (default: 1).\n            get_all (bool): Fetch all available data (default: False).\n            \n        Returns:\n            pd.DataFrame: Intraday ticks adhering to `market.trades` schema.\n        '
		if bytes([112,97,103,101,95,115,105,122,101]).decode()not in A:A[bytes([112,97,103,101,95,115,105,122,101]).decode()]=limit
		return B._dispatch(bytes([116,114,97,100,101,115]).decode(),**A)
	def intraday(A,**B):'\n        [Backward Compatible Alias] Relays to `.trades()`.\n        Provides intraday tick-by-tick data.\n        ';return A.trades(**B)
	def order_book(A,**B):
		'\n        Order book levels (Best Bid/Ask L2/L3).\n        \n        Returns:\n            pd.DataFrame: Order book adhering to `market.order_book` schema.\n        '
		if bytes([115,121,109,98,111,108,115,95,108,105,115,116]).decode()not in B:B[bytes([115,121,109,98,111,108,115,95,108,105,115,116]).decode()]=A.symbol if isinstance(A.symbol,list)else[A.symbol]
		return A._dispatch(bytes([111,114,100,101,114,95,98,111,111,107]).decode(),**B)
	def price_depth(A,**B):'\n        [Backward Compatible Alias] Relays to `.order_book()`.\n        Provides order book levels.\n        ';return A.order_book(**B)
	def quote(A,**B):
		'\n        Real-time single-symbol pricing snapshot.\n        If the underlying provider expects `symbols_list`, it injects `[self.symbol]`.\n        \n        Returns:\n            pd.DataFrame: Quote snapshot adhering to `market.quote` schema.\n        '
		if bytes([115,121,109,98,111,108,115,95,108,105,115,116]).decode()not in B:B[bytes([115,121,109,98,111,108,115,95,108,105,115,116]).decode()]=A.symbol if isinstance(A.symbol,list)else[A.symbol]
		B[bytes([103,101,116,95,97,108,108]).decode()]=True;return A._dispatch(bytes([113,117,111,116,101]).decode(),**B)
	def price_board(A,**B):'\n        [Backward Compatible Alias] Relays to `.quote()`.\n        Provides real-time single-symbol pricing snapshot.\n        ';return A.quote(**B)
	def session_stats(A,**B):'\n        End-of-session aggregate statistics.\n        \n        Returns:\n            pd.DataFrame: Session statistics.\n        ';return A._dispatch(bytes([115,101,115,115,105,111,110,95,115,116,97,116,115]).decode(),**B)
	def trading_stats(A,**B):'\n        [Backward Compatible Alias] Relays to `.session_stats()`.\n        Provides end-of-session aggregate statistics.\n        ';return A.session_stats(**B)
	def summary(A,**B):'\n        Stock Info / Snapshot summary metrics including pricing, \n        52-week ranges, and fundamental ratios.\n\n        Returns:\n            pd.DataFrame: Snapshot metrics adhering to `market.summary` schema.\n        ';return A._dispatch(bytes([115,117,109,109,97,114,121]).decode(),**B)