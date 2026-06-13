"\nDukascopy Provider – OHLCV & Tick data module.\n\nMarket data from the Dukascopy Historical Data feed (jetta.dukas.com).\n\nAvailable REST endpoints:\n    GET /v1/candles/minute/{symbol}/{side}/{year}/{month}/{day}\n        → Minute candles for one calendar day.\n    GET /v1/candles/day/{symbol}/{side}\n        → Full daily candle history (no date parameter).\n    GET /v1/ticks/{symbol}/{year}/{month}/{day}/{hour}\n        → Tick data for one hour.\n\nAll other timeframes (1h, 4h, 1w, 1M) are computed by resampling:\n    1h / 4h  → fetch 1m data per day, resample\n    1w / 1M  → fetch full daily history, resample\n\nAPI Response Format\n───────────────────\nDukascopy returns **delta-encoded** compressed arrays:\n  - ``timestamp``  – Unix ms of the first bar's open time.\n  - ``shift``      – Bar duration in ms.\n  - ``multiplier`` – Price precision (e.g. 0.001 means integers represent 0.001 units).\n  - ``times``      – Cumulative time-step deltas (int); absolute = timestamp + cumsum(times)*shift\n  - ``opens/highs/lows/closes`` – Cumulative price deltas; absolute = open + cumsum(deltas)*multiplier\n  - ``volumes``    – Raw (non-delta) volume values.\n"
from __future__ import annotations
import datetime
from itertools import accumulate
import pandas as pd,requests
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
logger=get_logger(__name__)
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.dukas.const import _BASE_URL,_COMMON_SYMBOL_MAP,_SYMBOL_SUFFIX_PATTERN
def _clean_symbol(symbol):'Normalise a Dukascopy symbol code.\n\n    Accepts both the verbose instrument code (e.g. ``USA500.IDX-USD``) and the\n    short user-facing form (e.g. ``USA500``).  Both are converted to the exact\n    code expected by the API.\n\n    Currently a no-op transformation – the API accepts the full code directly.\n    The helper exists as a central place to add further normalization if needed.\n    ';import re;return re.sub(_SYMBOL_SUFFIX_PATTERN,'',symbol.strip().upper())
_INTERVAL_FETCH={bytes([49,109]).decode():(bytes([109,105,110,117,116,101]).decode(),None),bytes([49,104]).decode():(bytes([109,105,110,117,116,101]).decode(),bytes([49,104]).decode()),bytes([52,104]).decode():(bytes([109,105,110,117,116,101]).decode(),bytes([52,104]).decode()),bytes([49,100]).decode():(bytes([100,97,121]).decode(),None),bytes([49,119]).decode():(bytes([100,97,121]).decode(),bytes([49,87]).decode()),bytes([49,77]).decode():(bytes([100,97,121]).decode(),bytes([49,77,83]).decode())}
_MINUTE_BASED={bytes([49,109]).decode(),bytes([49,104]).decode(),bytes([52,104]).decode()}
def _session():A=requests.Session();A.headers.update(get_headers(bytes([68,85,75,65,83,67,79,80,89]).decode(),random_agent=False,browser=bytes([99,104,114,111,109,101]).decode(),platform=bytes([109,97,99,111,115]).decode()));A.headers[bytes([97,99,99,101,112,116]).decode()]=bytes([97,112,112,108,105,99,97,116,105,111,110,47,106,115,111,110,44,32,116,101,120,116,47,112,108,97,105,110,44,32,42,47,42]).decode();return A
def _decode_candles(data,tz=bytes([65,115,105,97,47,72,111,95,67,104,105,95,77,105,110,104]).decode()):
	'Decode Dukascopy delta-compressed candle response into a DataFrame.';A=data;F=A[bytes([116,105,109,101,115,116,97,109,112]).decode()];B=A[bytes([109,117,108,116,105,112,108,105,101,114]).decode()];G=A[bytes([115,104,105,102,116]).decode()];D=list(accumulate(A[bytes([116,105,109,101,115]).decode()]));H=list(accumulate(A[bytes([111,112,101,110,115]).decode()]));I=list(accumulate(A[bytes([104,105,103,104,115]).decode()]));J=list(accumulate(A[bytes([108,111,119,115]).decode()]));K=list(accumulate(A[bytes([99,108,111,115,101,115]).decode()]));E=A.get(bytes([118,111,108,117,109,101,115]).decode(),[0]*len(D));L=[{bytes([116,105,109,101]).decode():pd.Timestamp(F+D[A]*G,unit=bytes([109,115]).decode()),bytes([111,112,101,110]).decode():H[A]*B,bytes([104,105,103,104]).decode():I[A]*B,bytes([108,111,119]).decode():J[A]*B,bytes([99,108,111,115,101]).decode():K[A]*B,bytes([118,111,108,117,109,101]).decode():E[A]if A<len(E)else 0}for A in range(len(D))];C=pd.DataFrame(L)
	if not C.empty:C[bytes([116,105,109,101]).decode()]=C[bytes([116,105,109,101]).decode()].dt.tz_localize(bytes([85,84,67]).decode()).dt.tz_convert(tz).dt.tz_localize(None)
	return C
def _decode_ticks(data,tz=bytes([65,115,105,97,47,72,111,95,67,104,105,95,77,105,110,104]).decode()):
	'Decode Dukascopy delta-compressed tick response into a DataFrame.';A=data;G=A[bytes([116,105,109,101,115,116,97,109,112]).decode()];C=A[bytes([109,117,108,116,105,112,108,105,101,114]).decode()];D=list(accumulate(A[bytes([116,105,109,101,115]).decode()]));H=list(accumulate(A[bytes([97,115,107,115]).decode()]));I=list(accumulate(A[bytes([98,105,100,115]).decode()]));E=A.get(bytes([97,115,107,86,111,108,117,109,101,115]).decode(),[]);F=A.get(bytes([98,105,100,86,111,108,117,109,101,115]).decode(),[]);J=[{bytes([116,105,109,101]).decode():pd.Timestamp(G+D[A],unit=bytes([109,115]).decode()),bytes([97,115,107]).decode():H[A]*C,bytes([98,105,100]).decode():I[A]*C,bytes([97,115,107,95,118,111,108,117,109,101]).decode():E[A]if A<len(E)else 0,bytes([98,105,100,95,118,111,108,117,109,101]).decode():F[A]if A<len(F)else 0}for A in range(len(D))];B=pd.DataFrame(J)
	if not B.empty:B[bytes([116,105,109,101]).decode()]=B[bytes([116,105,109,101]).decode()].dt.tz_localize(bytes([85,84,67]).decode()).dt.tz_convert(tz).dt.tz_localize(None);B[bytes([112,114,105,99,101]).decode()]=round((B[bytes([97,115,107]).decode()]+B[bytes([98,105,100]).decode()])/2,6)
	return B
def _safe_get(session,url):
	'GET with timeout. Returns None on 404 or empty data (no bars for that period).';B=url
	try:A=session.get(B,timeout=15)
	except requests.exceptions.Timeout:raise ConnectionError(f"Dukascopy timed out (15s): {B}")
	except requests.exceptions.RequestException as D:raise ConnectionError(f"Dukascopy connection error: {D}")
	if A.status_code==404:return
	if A.status_code!=200:raise ValueError(f"Dukascopy HTTP {A.status_code}: {B}")
	try:C=A.json()
	except Exception:return
	return C if C and C.get(bytes([116,105,109,101,115]).decode())else None
class Quote:
	"\n    Dukascopy market data – OHLCV (candles) and tick data.\n\n    Supports Forex, Commodities, Global Indices, Stocks, and Crypto.\n\n    Symbol format (use the ``code`` field from Dukascopy instruments list):\n        FX:     ``EUR-USD``, ``USD-JPY``, ``GBP-USD``\n        IDX:    ``USA500.IDX-USD``, ``GER30.IDX-EUR``, ``JPN225.IDX-JPY``\n        CMD:    ``COFFEE.CMD-USX``, ``OIL.CMD-USD``, ``WHEAT.CMD-USX``\n        STK:    ``AAPL.NYSE-USD``, ``AMZN.NSD-USD``\n        CRYPTO: ``BTCUSD``, ``ETHUSD``\n\n    Supported intervals: ``1m``, ``1h``, ``4h``, ``1d``, ``1w``, ``1M``\n\n    Side options:\n        ``'bid'`` (default), ``'ask'``, ``'mid'`` (average of bid + ask)\n\n    Note:\n        ``1h``, ``4h``, ``1w``, ``1M`` are computed by resampling lower-frequency data.\n    "
	def __init__(B,symbol,show_log=False,**F):
		E=show_log;B.timezone=F.get(bytes([116,105,109,101,122,111,110,101]).decode(),bytes([65,115,105,97,47,72,111,95,67,104,105,95,77,105,110,104]).decode());A=symbol.strip().upper()
		if A in _COMMON_SYMBOL_MAP:B.symbol=_COMMON_SYMBOL_MAP[A]
		else:
			try:
				from vnstock_data.explorer.dukas.listing import Listing as G;D=G(show_log=False).all_symbols(to_df=False);C=next((B for B in D if B[bytes([99,111,100,101]).decode()].upper()==A),None)
				if not C:C=next((B for B in D if B[bytes([115,121,109,98,111,108]).decode()].upper()==A),None)
				if not C:import re;H=re.sub(bytes([91,94,65,45,90,48,45,57,93]).decode(),'',A);C=next((A for A in D if re.sub(bytes([91,94,65,45,90,48,45,57,93]).decode(),'',A[bytes([99,111,100,101]).decode()].upper())==H),None)
				B.symbol=C[bytes([99,111,100,101]).decode()]if C else A
			except Exception:B.symbol=A
		B.data_source=bytes([68,117,107,97,115,99,111,112,121]).decode();B.show_log=E
		if not E:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	def _fetch_day_history(A,session,side):'Fetch the full daily candle history (one request).';C=f"{_BASE_URL}/candles/day/{A.symbol}/{side.upper()}";B=_safe_get(session,C);return _decode_candles(B,tz=A.timezone)if B else pd.DataFrame()
	def _fetch_minute_range(C,session,side,start_date,end_date):
		'Fetch per-day minute candles over a date range.';B=[];A=start_date
		while A<=end_date:
			E=f"{_BASE_URL}/candles/minute/{C.symbol}/{side.upper()}/{A.year}/{A.month}/{A.day}";D=_safe_get(session,E)
			if D:B.append(_decode_candles(D,tz=C.timezone))
			A+=datetime.timedelta(days=1)
		return pd.concat(B,ignore_index=True)if B else pd.DataFrame()
	def _mid(E,df_bid,df_ask):
		'Compute mid-price from two equally-shaped bid/ask DataFrames.';B=df_ask;A=df_bid
		if A.empty:return pd.DataFrame()
		C=A.copy()
		if not B.empty and len(B)==len(A):
			for D in(bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode()):C[D]=round((C[D]+B[D])/2,6)
		return C
	@agg_execution(bytes([68,117,107,97,115,99,111,112,121,46,101,120,116]).decode())
	def history(self,start='',end='',interval=bytes([49,100]).decode(),side=bytes([98,105,100]).decode(),length=500,to_df=True,**V):
		"\n        Fetch historical OHLCV candlestick data.\n\n        Args:\n            start (str): Start date ``YYYY-MM-DD``. Leave blank to use ``length``.\n            end (str): End date ``YYYY-MM-DD``. Defaults to today (UTC).\n            interval (str): Timeframe – ``1m``, ``1h``, ``4h``, ``1d``, ``1w``, ``1M``.\n            side (str): Price side –\n                ``'bid'`` (default), ``'ask'``, or ``'mid'`` (bid+ask midpoint).\n            length (int): Maximum number of bars returned (tail truncation). Default 500.\n            to_df (bool): Return DataFrame (default) or JSON string.\n\n        Returns:\n            pd.DataFrame: ``[time, open, high, low, close, volume]``\n\n        Note:\n            - ``1h``, ``4h`` are resampled from 1-minute data (slower).\n            - ``1w``, ``1M`` are resampled from daily history.\n            - All timestamps are timezone-naive UTC.\n        ";O=length;K=interval;J=end;G=start;B=self;C=K.strip();Q={bytes([49,72]).decode():bytes([49,104]).decode(),bytes([52,72]).decode():bytes([52,104]).decode(),bytes([49,68]).decode():bytes([49,100]).decode(),bytes([49,87]).decode():bytes([49,119]).decode()};C=Q.get(C.upper(),C.lower())
		if C==bytes([49,109]).decode()and K.endswith(bytes([77]).decode()):C=bytes([49,77]).decode()
		if C not in _INTERVAL_FETCH:R=bytes([44,32]).decode().join(_INTERVAL_FETCH);raise ValueError(f"Interval '{K}' not supported by Dukascopy. Supported: {R}")
		S,P=_INTERVAL_FETCH[C];H=side.lower();D=_session();L=datetime.datetime.utcnow().date()
		if J:
			E=pd.to_datetime(J).date()
			if E>=L:E=L-datetime.timedelta(days=1)
		else:E=L-datetime.timedelta(days=1)
		if S==bytes([109,105,110,117,116,101]).decode():
			T={bytes([49,109]).decode():1440,bytes([49,104]).decode():24,bytes([52,104]).decode():6}
			if not G:U=max(5,O//T.get(C,24)+3);I=E-datetime.timedelta(days=U)
			else:I=pd.to_datetime(G).date()
			F=E
			while F.weekday()>=5:F-=datetime.timedelta(days=1)
			if H==bytes([109,105,100]).decode():M=B._fetch_minute_range(D,bytes([66,73,68]).decode(),I,F);N=B._fetch_minute_range(D,bytes([65,83,75]).decode(),I,F);A=B._mid(M,N)
			else:A=B._fetch_minute_range(D,H.upper(),I,F)
		elif H==bytes([109,105,100]).decode():M=B._fetch_day_history(D,bytes([66,73,68]).decode());N=B._fetch_day_history(D,bytes([65,83,75]).decode());A=B._mid(M,N)
		else:A=B._fetch_day_history(D,H.upper())
		if A.empty:return pd.DataFrame()
		if P:A=A.set_index(bytes([116,105,109,101]).decode());A=A.resample(P,label=bytes([108,101,102,116]).decode(),closed=bytes([108,101,102,116]).decode()).agg({bytes([111,112,101,110]).decode():bytes([102,105,114,115,116]).decode(),bytes([104,105,103,104]).decode():bytes([109,97,120]).decode(),bytes([108,111,119]).decode():bytes([109,105,110]).decode(),bytes([99,108,111,115,101]).decode():bytes([108,97,115,116]).decode(),bytes([118,111,108,117,109,101]).decode():bytes([115,117,109]).decode()}).dropna().reset_index()
		A=A.sort_values(bytes([116,105,109,101]).decode()).reset_index(drop=True)
		if G:A=A[A[bytes([116,105,109,101]).decode()]>=pd.to_datetime(G)]
		if J:A=A[A[bytes([116,105,109,101]).decode()]<=pd.to_datetime(E)+pd.Timedelta(days=1)]
		A=A.tail(O).reset_index(drop=True)
		if hasattr(A[bytes([116,105,109,101]).decode()],bytes([100,116]).decode())and A[bytes([116,105,109,101]).decode()].dt.tz is not None:A[bytes([116,105,109,101]).decode()]=A[bytes([116,105,109,101]).decode()].dt.tz_localize(None)
		A.source=B.data_source;return A if to_df else A.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
	@agg_execution(bytes([68,117,107,97,115,99,111,112,121,46,101,120,116]).decode())
	def intraday(self,date='',hour=None,to_df=True,**I):
		'\n        Fetch tick-level data for a specific date and UTC hour.\n\n        Args:\n            date (str): Date ``YYYY-MM-DD``. Defaults to today (UTC).\n            hour (int | None): UTC hour (0–23). Defaults to the current UTC hour.\n            to_df (bool): Return DataFrame (default) or JSON string.\n\n        Returns:\n            pd.DataFrame: ``[time, ask, bid, price, ask_volume, bid_volume]``\n        ';B=self;F=_session();D=datetime.datetime.utcnow();C=pd.to_datetime(date).date()if date else D.date();G=hour if hour is not None else D.hour;H=f"{_BASE_URL}/ticks/{B.symbol}/{C.year}/{C.month}/{C.day}/{G}";E=_safe_get(F,H)
		if not E:return pd.DataFrame()
		A=_decode_ticks(E,tz=B.timezone)
		if hasattr(A[bytes([116,105,109,101]).decode()],bytes([100,116]).decode())and A[bytes([116,105,109,101]).decode()].dt.tz is not None:A[bytes([116,105,109,101]).decode()]=A[bytes([116,105,109,101]).decode()].dt.tz_localize(None)
		A.source=B.data_source;return A if to_df else A.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([113,117,111,116,101]).decode(),bytes([100,117,107,97,115,99,111,112,121]).decode(),Quote)