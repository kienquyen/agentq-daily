'\nWarrant domain reference structure.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDetail,BaseDomain
from vnstock_data.ui._registry import REFERENCE_SOURCES
class WarrantReference(BaseDetail):
	'\n    Reference Data Layer for Covered Warrants.\n    '
	def __init__(A,symbol=None):
		B=symbol
		if B is None:super().__init__(bytes([87,65,82,82,65,78,84]).decode(),bytes([100,101,114,105,118,97,116,105,118,101,115,46,119,97,114,114,97,110,116]).decode(),REFERENCE_SOURCES);A._is_listing=True
		else:super().__init__(B,bytes([100,101,114,105,118,97,116,105,118,101,115,46,119,97,114,114,97,110,116]).decode(),REFERENCE_SOURCES);A._is_listing=False
	def list(B):'\n        List all available covered warrants.\n        ';A=BaseDomain(bytes([100,101,114,105,118,97,116,105,118,101,115,46,119,97,114,114,97,110,116]).decode(),REFERENCE_SOURCES);return A._dispatch(bytes([108,105,115,116]).decode())
	def info(A):'\n        Get info and realtime information for the specific covered warrant.\n        \n        Returns:\n            pd.DataFrame: A standardized dataframe with warrant details.\n        ';return A._dispatch(bytes([105,110,102,111]).decode())
class FuturesReference(BaseDetail):
	'\n    Reference Data Layer for Index Futures.\n    '
	def __init__(A,symbol=None):
		B=symbol
		if B is None:super().__init__(bytes([70,85,84,85,82,69,83]).decode(),bytes([100,101,114,105,118,97,116,105,118,101,115,46,102,117,116,117,114,101,115]).decode(),REFERENCE_SOURCES);A._is_listing=True
		else:super().__init__(B,bytes([100,101,114,105,118,97,116,105,118,101,115,46,102,117,116,117,114,101,115]).decode(),REFERENCE_SOURCES);A._is_listing=False
	def list(B):'\n        List all available futures indices with metadata.\n        \n        Returns:\n            DataFrame with futures information\n        ';A=BaseDomain(bytes([100,101,114,105,118,97,116,105,118,101,115,46,102,117,116,117,114,101,115]).decode(),REFERENCE_SOURCES);return A._dispatch(bytes([108,105,115,116]).decode())
	def info(A):'\n        Get info and realtime information for the specific index future.\n        ';return A._dispatch(bytes([105,110,102,111]).decode())
class DerivativesReference:
	'\n    Derivatives domain wrapper containing Futures and Warrants.\n    '
	def warrant(A,symbol=None):"\n        Access covered warrant profile and reference data.\n        \n        Args:\n            symbol (str, optional): Warrant symbol (e.g., 'CACB2511').\n        ";return WarrantReference(symbol)
	def futures(A,symbol=None):"\n        Access index futures profile and reference data.\n        \n        Args:\n            symbol (str, optional): Future symbol (e.g., 'VN30F2503').\n        ";return FuturesReference(symbol)