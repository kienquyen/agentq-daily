'\nDukascopy Provider – Listing module.\n\nInstrument discovery for the Dukascopy data feed.\nAll symbols from https://jetta.dukascopy.com/v1/instruments,\norganized and searchable by code, description, or instrument type.\n\nSupported instrument types:\n  FX    – Forex currency pairs (EUR-USD, USD-JPY, GBP-USD…)\n  IDX   – Global indices (USA500.IDX-USD, GER30.IDX-EUR, JPN225.IDX-JPY…)\n  CMD   – Commodities (XAUUSD.CMD-USD, XAGUSD.CMD-USD, COFFEE.CMD-USX…)\n  STK   – Individual stocks (AAPL.NYSE-USD, META.NSD-USD…)\n  CFD   – Contract-for-Difference instruments\n  CRYPTO– Cryptocurrencies (BTCUSD, ETHUSD…)\n'
import re as _re,pandas as pd,requests
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock_data.core.utils.user_agent import get_headers
logger=get_logger(__name__)
from vnstock_data.explorer.dukas.const import _BASE_URL,_PLATFORM_GROUP_MAP,_SYMBOL_SUFFIX_PATTERN
_SUFFIX_RE=_re.compile(_SYMBOL_SUFFIX_PATTERN)
def _clean_code(code):'Return user-friendly symbol: strip exchange/asset-class suffixes and hyphens.\n    e.g. EUR-USD -> EURUSD.\n    ';A=_SUFFIX_RE.sub('',code);return A.replace(bytes([45]).decode(),'')
class Listing:
	"\n    Dukascopy instrument discovery.\n\n    Retrieves the full catalogue from ``GET /v1/instruments``\n    and provides filtering/search utilities.\n\n    Supported instrument types\n    ──────────────────────────\n    FX      Currency pairs        EUR-USD, USD-JPY, GBP-USD\n    IDX     Global indices        USA500.IDX-USD, GER30.IDX-EUR\n    CMD     Commodities           XAUUSD.CMD-USD, COFFEE.CMD-USX\n    STK     Individual stocks     AAPL.NYSE-USD, META.NSD-USD\n    CFD     CFDs\n    CRYPTO  Cryptocurrencies      BTCUSD, ETHUSD\n\n    Example\n    -------\n    >>> from vnstock_data import Reference\n    >>> ref = Reference()\n    >>> ref.instruments().all_symbols(instrument_type='IDX')\n    "
	def __init__(A,show_log=False,**C):
		B=show_log;A.data_source=bytes([68,117,107,97,115,99,111,112,121]).decode();A.base_url=_BASE_URL;A.show_log=B
		if not B:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	def _fetch_instruments(C):
		try:B=requests.get(f"{C.base_url}/instruments",headers=get_headers(bytes([68,85,75,65,83,67,79,80,89]).decode(),random_agent=False,browser=bytes([99,104,114,111,109,101]).decode(),platform=bytes([109,97,99,111,115]).decode()),timeout=15)
		except requests.exceptions.Timeout:raise ConnectionError(bytes([68,117,107,97,115,99,111,112,121,32,105,110,115,116,114,117,109,101,110,116,115,32,114,101,113,117,101,115,116,32,116,105,109,101,100,32,111,117,116,32,40,49,53,115,41,46,32,67,104,101,99,107,32,110,101,116,119,111,114,107,46]).decode())
		except requests.exceptions.RequestException as D:raise ConnectionError(f"Dukascopy connection error: {D}")
		if B.status_code!=200:raise ValueError(f"Dukascopy instruments error: HTTP {B.status_code}")
		A=B.json();return A.get(bytes([105,110,115,116,114,117,109,101,110,116,115]).decode(),A)if isinstance(A,dict)else A
	@agg_execution(bytes([68,117,107,97,115,99,111,112,121,46,101,120,116]).decode())
	def all_symbols(self,instrument_type=None,to_df=True):
		"\n        Retrieve the full instrument catalogue from Dukascopy.\n\n        Args:\n            instrument_type (str | None): Filter by type – ``'FX'``, ``'IDX'``,\n                ``'CMD'``, ``'STK'``, ``'CFD'``, ``'CRYPTO'``. ``None`` = all.\n            to_df (bool): Return DataFrame (default) or raw list.\n\n        Returns:\n            pd.DataFrame: Schema ``[code, name, description, type, country_code,\n                pip_value, price_scale]``\n        ";D=instrument_type;C=self;H=C._fetch_instruments();B=[]
		for A in H:E=A.get(bytes([112,108,97,116,102,111,114,109,71,114,111,117,112,73,100]).decode(),'');I=_PLATFORM_GROUP_MAP.get(E,E);F=A.get(bytes([99,111,100,101]).decode(),'');B.append({bytes([115,121,109,98,111,108]).decode():_clean_code(F),bytes([99,111,100,101]).decode():F,bytes([110,97,109,101]).decode():A.get(bytes([110,97,109,101]).decode(),''),bytes([100,101,115,99,114,105,112,116,105,111,110]).decode():A.get(bytes([100,101,115,99,114,105,112,116,105,111,110]).decode(),'')or'',bytes([116,121,112,101]).decode():I,bytes([99,111,117,110,116,114,121,95,99,111,100,101]).decode():A.get(bytes([99,111,117,110,116,114,121,67,111,100,101]).decode(),''),bytes([112,105,112,95,118,97,108,117,101]).decode():A.get(bytes([112,105,112,86,97,108,117,101]).decode()),bytes([112,114,105,99,101,95,115,99,97,108,101]).decode():A.get(bytes([112,114,105,99,101,83,99,97,108,101]).decode())})
		if D:J=D.upper();B=[A for A in B if A[bytes([116,121,112,101]).decode()]==J]
		K=D or bytes([97,108,108]).decode()
		if C.show_log:logger.info(f"Dukascopy: {len(B)} instruments found (type={K})")
		if not to_df:return B
		G=pd.DataFrame(B);G.source=C.data_source;return G
	@agg_execution(bytes([68,117,107,97,115,99,111,112,121,46,101,120,116]).decode())
	def search_symbol(self,query,instrument_type=None,to_df=True):
		'\n        Search instruments by keyword (matches code or description).\n\n        Args:\n            query (str): Search keyword.\n            instrument_type (str | None): Optional type filter.\n            to_df (bool): Return DataFrame or raw list.\n\n        Returns:\n            pd.DataFrame: Filtered instrument list.\n        ';D=query;A=self.all_symbols(instrument_type=instrument_type,to_df=True)
		if A.empty:return A
		B=D.lower();E=A[bytes([115,121,109,98,111,108]).decode()].str.lower().str.contains(B,na=False)|A[bytes([99,111,100,101]).decode()].str.lower().str.contains(B,na=False)|A[bytes([100,101,115,99,114,105,112,116,105,111,110]).decode()].str.lower().str.contains(B,na=False);C=A[E].reset_index(drop=True)
		if self.show_log:logger.info(f"Dukascopy search '{D}': {len(C)} results")
		if not to_df:return C.to_dict(bytes([114,101,99,111,114,100,115]).decode())
		return C
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([108,105,115,116,105,110,103]).decode(),bytes([100,117,107,97,115,99,111,112,121]).decode(),Listing)