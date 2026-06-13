'\nEvents Reference domain.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDomain
from vnstock_data.ui._registry import REFERENCE_SOURCES
class EventsReference(BaseDomain):
	'\n    Events Reference Data.\n    Provides access to market events, news, and other time-bound occurrences.\n    '
	def __init__(A):super().__init__(domain_name=bytes([101,118,101,110,116,115]).decode(),layer_sources=REFERENCE_SOURCES)
	def calendar(A,start=None,end=None,event_type=None,page=0,limit=20000):"\n        Retrieve events calendar (dividends, AGM, new listings, ...) from the default data source.\n        \n        Args:\n            start (str, optional): Start date (YYYY-MM-DD). Defaults to the current date.\n            end (str, optional): End date (YYYY-MM-DD). Defaults to the current date.\n            event_type (str, optional): Type of event or event group:\n                - 'dividend': Returns dividends, share issuance\n                - 'insider': Returns insider trading, major shareholders\n                - 'agm': Returns shareholder meetings\n                - 'others': Returns other fluctuations\n                - Or a specific eventCode (e.g., 'ISS,DIV')\n            page (int): Page index. Defaults to 0.\n            limit (int): Number of records per page. Defaults to 20000.\n            \n        Returns:\n            pd.DataFrame: Standardized list of events.\n        ";return A._dispatch(bytes([99,97,108,101,110,100,97,114]).decode(),start=start,end=end,event_type=event_type,page=page,limit=limit)
	def market(Y,start=None,end=None,event_type=None):
		"\n        Retrieve special stock market events (holidays, system incidents, ...)\n        \n        Uses a static internal database from the vnstock library.\n        \n        Args:\n            start (str, optional): Start date (YYYY-MM-DD). Defaults to all events.\n            end (str, optional): End date (YYYY-MM-DD). Defaults to all events.\n            event_type (str, optional): Event type ('Holiday', 'Suspension', 'Compensation').\n            \n        Returns:\n            pd.DataFrame: List of market events.\n        ";E=event_type;D=start;B={}
		try:from vnstock.core.utils import market_events as N;B=getattr(N,bytes([77,65,82,75,69,84,95,69,86,69,78,84,83]).decode(),{})
		except ImportError:
			try:import importlib;C=importlib.import_module(bytes([118,110,115,116,111,99,107,46,99,111,114,101,46,117,116,105,108,115,46,109,97,114,107,101,116,95,101,118,101,110,116,115]).decode());B=getattr(C,bytes([77,65,82,75,69,84,95,69,86,69,78,84,83]).decode(),{})
			except ImportError:
				try:C=importlib.import_module(bytes([118,110,115,116,111,99,107,46,99,111,114,101,46,117,116,105,108,115,46,109,97,114,107,101,116,45,101,118,101,110,116,115]).decode());B=getattr(C,bytes([77,65,82,75,69,84,95,69,86,69,78,84,83]).decode(),{})
				except ImportError:
					import os
					try:
						import vnstock as O;P=os.path.join(os.path.dirname(O.__file__),bytes([99,111,114,101]).decode(),bytes([117,116,105,108,115]).decode())
						for Q in[bytes([109,97,114,107,101,116,95,101,118,101,110,116,115,46,112,121]).decode(),bytes([109,97,114,107,101,116,45,101,118,101,110,116,115,46,112,121]).decode()]:
							F=os.path.join(P,Q)
							if os.path.exists(F):import importlib.util;G=importlib.util.spec_from_file_location(bytes([109,97,114,107,101,116,95,101,118,101,110,116,115,95,101,120,116]).decode(),F);H=importlib.util.module_from_spec(G);G.loader.exec_module(H);B=getattr(H,bytes([77,65,82,75,69,84,95,69,86,69,78,84,83]).decode(),{});break
					except Exception as R:from vnstock.core.utils.logger import get_logger as S;T=S(__name__);T.warning(f"Failed to load market events: {R!s}. Please ensure you have vnstock v3.4.3+ installed.");pass
		if not B:return pd.DataFrame()
		I=[]
		for(U,V)in B.items():J={bytes([100,97,116,101]).decode():U};J.update(V);I.append(J)
		A=pd.DataFrame(I);from vnstock_data.ui.schemas.events import SCHEMA_MAP as W,STANDARD_COLUMNS as X;K=W.get(bytes([101,118,101,110,116,115,46,109,97,114,107,101,116]).decode(),{}).get(bytes([118,110,115,116,111,99,107]).decode(),{});L=X.get(bytes([101,118,101,110,116,115,46,109,97,114,107,101,116]).decode(),[])
		if not A.empty and K:A.rename(columns=K,inplace=True)
		for M in L:
			if M not in A.columns:A[M]=pd.NA
		A=A[L]
		if not A.empty:
			A[bytes([100,97,116,101]).decode()]=pd.to_datetime(A[bytes([100,97,116,101]).decode()])
			if D:
				try:A=A[A[bytes([100,97,116,101]).decode()]>=pd.to_datetime(D)]
				except Exception:pass
			if end:
				try:A=A[A[bytes([100,97,116,101]).decode()]<=pd.to_datetime(end)]
				except Exception:pass
			if E:A=A[A[bytes([101,118,101,110,116,95,116,121,112,101]).decode()].str.lower()==E.lower()]
		return A.reset_index(drop=True)