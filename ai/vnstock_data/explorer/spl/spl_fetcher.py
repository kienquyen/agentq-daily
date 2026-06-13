from typing import Any
import pandas as pd
from vnstock.core.utils.interval import normalize_interval
from vnstock_data.core.utils.fetcher import Fetcher
from vnstock_data.core.utils.user_agent import HEADERS_MAPPING_SOURCE
from.const import BASE_URL,INTERVALS
class SPLFetcher(Fetcher):
	'\n    Specific fetcher for SPL data provider.\n    '
	def __init__(A):'\n        Initialize the SPLFetcher with SPL-specific settings.\n        ';super().__init__(base_url=BASE_URL,headers=HEADERS_MAPPING_SOURCE.get(bytes([83,73,77,80,76,73,90,69]).decode(),{}))
	def validate(D,params):
		'\n        Validate SPL-specific query parameters.\n\n        Parameters:\n            params (dict): Query parameters to validate.\n        \n        Raises:\n            ValueError: If required parameters are missing or invalid.\n        ';B=params
		if not B.get(bytes([116,105,99,107,101,114]).decode()):raise ValueError(bytes([84,105,99,107,101,114,32,105,115,32,114,101,113,117,105,114,101,100,32,102,111,114,32,83,80,76,32,114,101,113,117,101,115,116,115,46]).decode())
		A=B.get(bytes([105,110,116,101,114,118,97,108]).decode(),bytes([49,68]).decode())
		if A not in INTERVALS:
			try:normalize_interval(A)
			except ValueError:C=bytes([44,32]).decode().join(sorted(INTERVALS));raise ValueError(f"Invalid interval '{A}'. Supported: {C}")
	def to_dataframe(C,raw_data):"\n        Convert SPL-specific raw data to a Pandas DataFrame.\n\n        Parameters:\n            raw_data (list): Raw data from the SPL API response.\n        \n        Returns:\n            pd.DataFrame: A Pandas DataFrame with columns ['time', 'open', 'high', 'low', 'close', 'volume'].\n        ";B=[bytes([116,105,109,101]).decode(),bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode(),bytes([118,111,108,117,109,101]).decode()];A=pd.DataFrame(raw_data,columns=B);A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()],unit=bytes([115]).decode());return A