import pandas as pd
from vnstock_data.connector.binance.spot._base import BinanceSpotBase
class SpotMarket:
	"\n    Binance Spot Market Data – Implementation Layer.\n\n    All public REST endpoints are exposed with **provider-agnostic names**\n    aligned with the Vnstock Unified UI naming convention (mirrors FIX / Bloomberg\n    terminology where applicable). The Unified UI facade delegates to these methods\n    via the registry.\n\n    Endpoint mapping (method → Binance REST endpoint):\n    ────────────────────────────────────────────────────\n    ohlcv           → GET /api/v3/uiKlines       (display-optimised candlesticks)\n    ohlcv_raw       → GET /api/v3/klines          (raw candlesticks, full fields)\n    trades          → GET /api/v3/trades           (mode='raw', default)\n                    → GET /api/v3/aggTrades        (mode='aggregate')\n    trade_history   → GET /api/v3/historicalTrades (older trades by ID)\n    order_book      → GET /api/v3/depth            (L2 Market Depth)\n    quote           → GET /api/v3/ticker/24hr      (24-h rolling quote snapshot)\n    vwap            → GET /api/v3/avgPrice         (Volume-Weighted Average Price)\n    daily_stats     → GET /api/v3/ticker/tradingDay(trading-day session stats)\n    last_price      → GET /api/v3/ticker/price     (last traded price)\n    rolling_stats   → GET /api/v3/ticker           (rolling-window statistics)\n    reference_price → GET /api/v3/referencePrice   (reference / indicative price)\n    reference_calc  → GET /api/v3/referencePrice/calculation\n\n    Connector-only (not exposed in Unified UI):\n    ────────────────────────────────────────────\n    bbo             → GET /api/v3/ticker/bookTicker(best bid / offer)\n    "
	def __init__(A,symbol):A.symbol=symbol
	def _format_columns(E,df):
		'Convert camelCase → snake_case, coerce timestamps & numerics.';A=df
		if A.empty:return A
		C={A:''.join([bytes([95]).decode()+A.lower()if A.isupper()else A for A in A]).lstrip(bytes([95]).decode())for A in A.columns};A.rename(columns=C,inplace=True);A=A.loc[:,~A.columns.duplicated()].copy()
		for B in(bytes([116,105,109,101]).decode(),bytes([111,112,101,110,95,116,105,109,101]).decode(),bytes([99,108,111,115,101,95,116,105,109,101]).decode(),bytes([116,105,109,101,115,116,97,109,112]).decode()):
			if B in A.columns:A[B]=pd.to_datetime(A[B],unit=bytes([109,115]).decode()).dt.tz_localize(None)
		D={bytes([115,121,109,98,111,108]).decode(),bytes([115,105,100,101]).decode(),bytes([109,97,116,99,104,95,116,121,112,101]).decode(),bytes([105,100]).decode(),bytes([116,105,109,101]).decode(),bytes([111,112,101,110,95,116,105,109,101]).decode(),bytes([99,108,111,115,101,95,116,105,109,101]).decode(),bytes([116,105,109,101,115,116,97,109,112]).decode()}
		for B in A.columns:
			if B not in D:A[B]=pd.to_numeric(A[B],errors=bytes([99,111,101,114,99,101]).decode())
		return A
	def ohlcv(C,interval=bytes([49,100]).decode(),start_time=None,end_time=None,limit=500,mode=None,**I):
		"\n        Historical OHLCV candlestick bars.\n\n        Args:\n            interval (str): Timeframe – ``1s``, ``1m``–``30m``, ``1h``–``12h``,\n                ``1d``, ``3d``, ``1w``, ``1M``.\n            limit (int): Number of bars (default 500, max 1000).\n            mode (str | None):\n                - ``None`` (default) – chart-optimised UIKlines that filters\n                  anomalous data. Binance: ``GET /api/v3/uiKlines``.\n                - ``'raw'`` – full kline with extra fields (``quote_volume``,\n                  ``trades``, ``taker_buy_base_vol``, ``taker_buy_quote_vol``).\n                  Binance: ``GET /api/v3/klines``.\n        ";E=end_time;D=start_time;G=[bytes([116,105,109,101]).decode(),bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode(),bytes([118,111,108,117,109,101]).decode(),bytes([99,108,111,115,101,95,116,105,109,101]).decode(),bytes([113,117,111,116,101,95,118,111,108,117,109,101]).decode(),bytes([116,114,97,100,101,115]).decode(),bytes([116,97,107,101,114,95,98,117,121,95,98,97,115,101,95,118,111,108]).decode(),bytes([116,97,107,101,114,95,98,117,121,95,113,117,111,116,101,95,118,111,108]).decode(),bytes([105,103,110,111,114,101]).decode()];B={bytes([115,121,109,98,111,108]).decode():C.symbol.upper(),bytes([105,110,116,101,114,118,97,108]).decode():interval,bytes([108,105,109,105,116]).decode():limit}
		if D:B[bytes([115,116,97,114,116,84,105,109,101]).decode()]=D
		if E:B[bytes([101,110,100,84,105,109,101]).decode()]=E
		H=bytes([47,97,112,105,47,118,51,47,107,108,105,110,101,115]).decode()if mode==bytes([114,97,119]).decode()else bytes([47,97,112,105,47,118,51,47,117,105,75,108,105,110,101,115]).decode();F=BinanceSpotBase._request(H,B)
		if not F:return pd.DataFrame()
		A=pd.DataFrame(F,columns=G);A=C._format_columns(A)
		if mode==bytes([114,97,119]).decode():return A.drop(columns=[bytes([105,103,110,111,114,101]).decode()],errors=bytes([105,103,110,111,114,101]).decode())
		return A[[bytes([116,105,109,101]).decode(),bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode(),bytes([118,111,108,117,109,101]).decode()]]
	def order_book(G,limit=10,**I):
		'\n        L2 order book depth – top N bid/ask price levels.\n\n        Binance endpoint: ``GET /api/v3/depth``\n        ';C=limit;H={bytes([115,121,109,98,111,108]).decode():G.symbol.upper(),bytes([108,105,109,105,116]).decode():C};D=BinanceSpotBase._request(bytes([47,97,112,105,47,118,51,47,100,101,112,116,104]).decode(),H)
		if not D:return pd.DataFrame()
		A={}
		for(B,E)in enumerate(D.get(bytes([98,105,100,115]).decode(),[])[:C]):A[f"bid_price_{B+1}"]=float(E[0]);A[f"bid_vol_{B+1}"]=float(E[1])
		for(B,F)in enumerate(D.get(bytes([97,115,107,115]).decode(),[])[:C]):A[f"ask_price_{B+1}"]=float(F[0]);A[f"ask_vol_{B+1}"]=float(F[1])
		return pd.DataFrame([A])
	def intraday(D,limit=500,mode=bytes([114,97,119]).decode(),start_time=None,end_time=None,**J):
		"\n        Tick-by-tick trade tape (Time & Sales).\n\n        Args:\n            limit (int): Number of records (default 500, max 1000).\n            mode (str):\n                - ``'raw'`` (default) – individual fills from ``GET /api/v3/trades``.\n                - ``'aggregate'`` – compressed fills aggregated at same price &\n                  direction, from ``GET /api/v3/aggTrades``.  Consecutive fills at\n                  the same price and side are merged into one record.\n            start_time (int): Unix ms – used only with ``mode='aggregate'``.\n            end_time (int): Unix ms – used only with ``mode='aggregate'``.\n\n        Returns:\n            pd.DataFrame: Schema ``[time, price, volume, side, match_type, id]``\n        ";G=end_time;F=start_time;E=limit
		if mode==bytes([97,103,103,114,101,103,97,116,101]).decode():
			B={bytes([115,121,109,98,111,108]).decode():D.symbol.upper(),bytes([108,105,109,105,116]).decode():E}
			if F:B[bytes([115,116,97,114,116,84,105,109,101]).decode()]=F
			if G:B[bytes([101,110,100,84,105,109,101]).decode()]=G
			C=BinanceSpotBase._request(bytes([47,97,112,105,47,118,51,47,97,103,103,84,114,97,100,101,115]).decode(),B)
			if not C:return pd.DataFrame()
			A=pd.DataFrame(C);H={bytes([84]).decode():bytes([116,105,109,101]).decode(),bytes([112]).decode():bytes([112,114,105,99,101]).decode(),bytes([113]).decode():bytes([118,111,108,117,109,101]).decode(),bytes([97]).decode():bytes([105,100]).decode()};A.rename(columns={B:C for(B,C)in H.items()if B in A.columns},inplace=True);A=D._format_columns(A)
			if bytes([109]).decode()in A.columns:A[bytes([115,105,100,101]).decode()]=A[bytes([109]).decode()].apply(lambda x:bytes([83,101,108,108]).decode()if x else bytes([66,117,121]).decode())
			A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=bytes([65,103,103,114,101,103,97,116,101]).decode()
		else:
			B={bytes([115,121,109,98,111,108]).decode():D.symbol.upper(),bytes([108,105,109,105,116]).decode():E};C=BinanceSpotBase._request(bytes([47,97,112,105,47,118,51,47,116,114,97,100,101,115]).decode(),B)
			if not C:return pd.DataFrame()
			A=pd.DataFrame(C)
			if bytes([113,116,121]).decode()in A.columns:A.rename(columns={bytes([113,116,121]).decode():bytes([118,111,108,117,109,101]).decode()},inplace=True)
			A=D._format_columns(A)
			if bytes([105,115,95,98,117,121,101,114,95,109,97,107,101,114]).decode()in A.columns:A[bytes([115,105,100,101]).decode()]=A[bytes([105,115,95,98,117,121,101,114,95,109,97,107,101,114]).decode()].apply(lambda x:bytes([83,101,108,108]).decode()if x else bytes([66,117,121]).decode())
			A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=bytes([78,111,114,109,97,108]).decode()
		I=[bytes([116,105,109,101]).decode(),bytes([112,114,105,99,101]).decode(),bytes([118,111,108,117,109,101]).decode(),bytes([115,105,100,101]).decode(),bytes([109,97,116,99,104,95,116,121,112,101]).decode(),bytes([105,100]).decode()];return A[[B for B in I if B in A.columns]]
	def trade_history(B,limit=500,from_id=None,**G):
		'\n        Historical trade look-up (paginate by trade ID for older data).\n\n        Binance endpoint: ``GET /api/v3/historicalTrades``\n        ';C=from_id;D={bytes([115,121,109,98,111,108]).decode():B.symbol.upper(),bytes([108,105,109,105,116]).decode():limit}
		if C:D[bytes([102,114,111,109,73,100]).decode()]=C
		E=BinanceSpotBase._request(bytes([47,97,112,105,47,118,51,47,104,105,115,116,111,114,105,99,97,108,84,114,97,100,101,115]).decode(),D)
		if not E:return pd.DataFrame()
		A=pd.DataFrame(E)
		if bytes([113,116,121]).decode()in A.columns:A.rename(columns={bytes([113,116,121]).decode():bytes([118,111,108,117,109,101]).decode()},inplace=True)
		A=B._format_columns(A)
		if bytes([105,115,95,98,117,121,101,114,95,109,97,107,101,114]).decode()in A.columns:A[bytes([115,105,100,101]).decode()]=A[bytes([105,115,95,98,117,121,101,114,95,109,97,107,101,114]).decode()].apply(lambda x:bytes([83,101,108,108]).decode()if x else bytes([66,117,121]).decode())
		A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=bytes([72,105,115,116,111,114,105,99,97,108]).decode();F=[bytes([116,105,109,101]).decode(),bytes([112,114,105,99,101]).decode(),bytes([118,111,108,117,109,101]).decode(),bytes([115,105,100,101]).decode(),bytes([109,97,116,99,104,95,116,121,112,101]).decode(),bytes([105,100]).decode()];return A[[B for B in F if B in A.columns]]
	def quote(A,**D):
		'\n        24-hour rolling price-change statistics (quote snapshot).\n\n        Binance endpoint: ``GET /api/v3/ticker/24hr``\n        ';C={bytes([115,121,109,98,111,108]).decode():A.symbol.upper()};B=BinanceSpotBase._request(bytes([47,97,112,105,47,118,51,47,116,105,99,107,101,114,47,50,52,104,114]).decode(),C)
		if not B:return pd.DataFrame()
		return A._format_columns(pd.DataFrame([B]))
	def vwap(A,**D):
		'\n        Volume-Weighted Average Price over the last N minutes.\n\n        Binance endpoint: ``GET /api/v3/avgPrice``\n        ';C={bytes([115,121,109,98,111,108]).decode():A.symbol.upper()};B=BinanceSpotBase._request(bytes([47,97,112,105,47,118,51,47,97,118,103,80,114,105,99,101]).decode(),C)
		if not B:return pd.DataFrame()
		return A._format_columns(pd.DataFrame([B]))
	def daily_stats(A,**D):
		'\n        Trading-day stats (open, high, low, close, volume for the current day).\n\n        Binance endpoint: ``GET /api/v3/ticker/tradingDay``\n        ';C={bytes([115,121,109,98,111,108]).decode():A.symbol.upper()};B=BinanceSpotBase._request(bytes([47,97,112,105,47,118,51,47,116,105,99,107,101,114,47,116,114,97,100,105,110,103,68,97,121]).decode(),C)
		if not B:return pd.DataFrame()
		return A._format_columns(pd.DataFrame([B]))
	def last_price(A,**D):
		'\n        Most-recent last traded price – ultra-lightweight single-field response.\n\n        Binance endpoint: ``GET /api/v3/ticker/price``\n        ';C={bytes([115,121,109,98,111,108]).decode():A.symbol.upper()};B=BinanceSpotBase._request(bytes([47,97,112,105,47,118,51,47,116,105,99,107,101,114,47,112,114,105,99,101]).decode(),C)
		if not B:return pd.DataFrame()
		return A._format_columns(pd.DataFrame([B]))
	def rolling_stats(B,window_size=bytes([49,100]).decode(),**E):
		'\n        Rolling-window price-change statistics over a custom window.\n\n        Binance endpoint: ``GET /api/v3/ticker``\n        ';C={bytes([115,121,109,98,111,108]).decode():B.symbol.upper(),bytes([119,105,110,100,111,119,83,105,122,101]).decode():window_size};A=BinanceSpotBase._request(bytes([47,97,112,105,47,118,51,47,116,105,99,107,101,114]).decode(),C)
		if not A:return pd.DataFrame()
		D=pd.DataFrame([A]if isinstance(A,dict)else A);return B._format_columns(D)
	def reference_price(A,mode=bytes([112,114,105,99,101]).decode(),**D):
		"\n        Reference (indicative) price for mark / liquidation calculations.\n\n        Args:\n            mode (str):\n                - ``'price'`` (default) – reference price only.\n                  Binance: ``GET /api/v3/referencePrice``.\n                - ``'calc'`` – detailed calculation breakdown.\n                  Binance: ``GET /api/v3/referencePrice/calculation``.\n\n        Note: Not all symbols have a reference price; returns empty DataFrame if unavailable.\n        ";C=bytes([47,97,112,105,47,118,51,47,114,101,102,101,114,101,110,99,101,80,114,105,99,101,47,99,97,108,99,117,108,97,116,105,111,110]).decode()if mode==bytes([99,97,108,99]).decode()else bytes([47,97,112,105,47,118,51,47,114,101,102,101,114,101,110,99,101,80,114,105,99,101]).decode();B=BinanceSpotBase._request(C,{bytes([115,121,109,98,111,108]).decode():A.symbol.upper()})
		if not B:return pd.DataFrame()
		return A._format_columns(pd.DataFrame([B]))
	def bbo(A,**E):
		'\n        Best Bid / Offer (top-of-book snapshot, single price level).\n\n        This is a connector-only method not exposed in the Unified UI facade,\n        because ``order_book(limit=1)`` provides equivalent information with a\n        richer schema.  Use this when you need the absolute minimalist payload.\n\n        Binance endpoint: ``GET /api/v3/ticker/bookTicker``\n        ';D={bytes([115,121,109,98,111,108]).decode():A.symbol.upper()};B=BinanceSpotBase._request(bytes([47,97,112,105,47,118,51,47,116,105,99,107,101,114,47,98,111,111,107,84,105,99,107,101,114]).decode(),D)
		if not B:return pd.DataFrame()
		C=pd.DataFrame([B]);C.rename(columns={bytes([98,105,100,80,114,105,99,101]).decode():bytes([98,105,100,95,112,114,105,99,101,95,49]).decode(),bytes([98,105,100,81,116,121]).decode():bytes([98,105,100,95,118,111,108,95,49]).decode(),bytes([97,115,107,80,114,105,99,101]).decode():bytes([97,115,107,95,112,114,105,99,101,95,49]).decode(),bytes([97,115,107,81,116,121]).decode():bytes([97,115,107,95,118,111,108,95,49]).decode()},inplace=True);return A._format_columns(C)