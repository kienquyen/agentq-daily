import pandas as pd,requests
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.user_agent import get_headers
from vnstock_data.core.utils.parser import lookback_date
from vnstock_data.explorer.vnd.const import _INDEX_MAPPING
logger=get_logger(__name__)
class Market:
	"\n    Provides market insights, including P/E and P/B ratios over time.\n\n    Attributes:\n        index (str): Market index (e.g., 'VNINDEX', 'HNX').\n        base_url (str): Base URL for retrieving data.\n        headers (dict): HTTP headers for API requests.\n    "
	def __init__(A,index=bytes([86,78,73,78,68,69,88]).decode(),random_agent=False,show_log=False):
		A.index=A._index_validation(index);A.base_url=bytes([104,116,116,112,115,58,47,47,97,112,105,45,102,105,110,102,111,46,118,110,100,105,114,101,99,116,46,99,111,109,46,118,110,47,118,52,47,114,97,116,105,111,115]).decode();A.headers=get_headers(data_source=bytes([86,78,68]).decode(),random_agent=random_agent)
		if not show_log:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	def _index_validation(B,index):
		"\n        Validates the index input.\n\n        Parameters:\n            index (str): The index to validate. Valid indices are 'VNINDEX' and 'HNX'.\n\n        Returns:\n            str: The validated index.\n        ";A=index;A=A.upper()
		if A==bytes([72,78,88]).decode():A=bytes([72,78,88,73,78,68,69,88]).decode()
		if A not in[bytes([86,78,73,78,68,69,88]).decode(),bytes([72,78,88,73,78,68,69,88]).decode(),bytes([86,78,51,48]).decode()]:raise ValueError(f"Invalid index: {A}. Valid indices are: 'VNINDEX', 'HNX', 'VN30'")
		if A==bytes([86,78,51,48]).decode():return bytes([86,78,51,48]).decode()
		else:return _INDEX_MAPPING[A]
	def _fetch_data(B,ratio_code,start_date):
		"\n        Fetches market ratio data from the API.\n\n        Parameters:\n            ratio_code (str): Ratio code ('PRICE_TO_BOOK' or 'PRICE_TO_EARNINGS').\n            start_date (str): Start date for fetching data (format: YYYY-MM-DD).\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the report date and ratio values.\n        ";C=ratio_code;F=f"{B.base_url}?q=ratioCode:{C}~code:{B.index}~reportDate:gte:{start_date}&sort=reportDate:desc&size=10000&fields=value,reportDate"
		try:
			logger.info(f"Fetching {C} data for index {B.index}...");D=requests.get(F,headers=B.headers);D.raise_for_status();E=D.json().get(bytes([100,97,116,97]).decode(),[])
			if not E:logger.warning(bytes([78,111,32,100,97,116,97,32,114,101,116,117,114,110,101,100,32,102,114,111,109,32,65,80,73,46]).decode());return pd.DataFrame()
			A=pd.DataFrame(E);A[bytes([114,101,112,111,114,116,68,97,116,101]).decode()]=pd.to_datetime(A[bytes([114,101,112,111,114,116,68,97,116,101]).decode()]);A=A.rename(columns={bytes([118,97,108,117,101]).decode():C.lower()});A=A.rename(columns={bytes([112,114,105,99,101,95,116,111,95,101,97,114,110,105,110,103,115]).decode():bytes([112,101]).decode(),bytes([112,114,105,99,101,95,116,111,95,98,111,111,107]).decode():bytes([112,98]).decode()});return A.set_index(bytes([114,101,112,111,114,116,68,97,116,101]).decode()).sort_index()
		except requests.RequestException as G:logger.error(f"Failed to fetch data: {G}");return pd.DataFrame()
	@agg_execution(bytes([86,78,68,46,101,120,116]).decode())
	def pe(self,duration=bytes([53,89]).decode()):"\n        Retrieves P/E (Price-to-Earnings) ratio data.\n\n        Parameters:\n            duration (str): Number of years to retrieve data back (e.g., '1Y', '5Y', '10Y').\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the P/E ratio data.\n        ";A=lookback_date(duration);return self._fetch_data(ratio_code=bytes([80,82,73,67,69,95,84,79,95,69,65,82,78,73,78,71,83]).decode(),start_date=A)
	@agg_execution(bytes([86,78,68,46,101,120,116]).decode())
	def pb(self,duration=bytes([53,89]).decode()):"\n        Retrieves P/B (Price-to-Book) ratio data.\n\n        Parameters:\n            duration (str): Number of years to retrieve data back (e.g., '1Y', '5Y', '10Y').\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the P/B ratio data.\n        ";A=lookback_date(duration);return self._fetch_data(ratio_code=bytes([80,82,73,67,69,95,84,79,95,66,79,79,75]).decode(),start_date=A)
	@agg_execution(bytes([86,78,68,46,101,120,116]).decode())
	def evaluation(self,duration=bytes([53,89]).decode()):
		"\n        Retrieves an overview of the market with both P/E and P/B ratios.\n\n        Parameters:\n            duration (str): Number of years to retrieve data back (e.g., '1Y', '5Y', '10Y').\n\n        Returns:\n            pd.DataFrame: A DataFrame containing P/E and P/B ratio data.\n        ";A=duration;E=lookback_date(A);B=self.pe(duration=A);C=self.pb(duration=A)
		if B.empty and C.empty:logger.warning(bytes([78,111,32,100,97,116,97,32,97,118,97,105,108,97,98,108,101,32,102,111,114,32,98,111,116,104,32,80,47,69,32,97,110,100,32,80,47,66,32,114,97,116,105,111,115,46]).decode());return pd.DataFrame()
		D=pd.concat([B,C],axis=1);return D
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([109,97,114,107,101,116]).decode(),bytes([118,110,100]).decode(),Market)