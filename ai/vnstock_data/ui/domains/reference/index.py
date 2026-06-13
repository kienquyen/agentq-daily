'\nIndex Reference Domain.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDomain
from vnstock_data.ui._registry import REFERENCE_SOURCES
class IndexDetail:
	'\n    Detailed information for a specific index.\n    '
	def __init__(A,index_symbol,sources_config=None):A.symbol=index_symbol;A._sources_config=sources_config;A._domain=BaseDomain(domain_name=bytes([105,110,100,101,120]).decode(),layer_sources=REFERENCE_SOURCES);A._domain._sources_config=A._sources_config
	def members(B):
		'\n        List constituents/members of the index.\n        ';A=B.symbol.upper()
		if A==bytes([86,78,73,78,68,69,88]).decode():A=bytes([72,79,83,69]).decode()
		elif A==bytes([72,78,88,73,78,68,69,88]).decode():A=bytes([72,78,88]).decode()
		elif A==bytes([85,80,67,79,77,73,78,68,69,88]).decode():A=bytes([85,80,67,79,77]).decode()
		return B._domain._dispatch(bytes([109,101,109,98,101,114,115]).decode(),group=A)
	def info(B):
		'Get complete information for this index.';from vnstock.common import indices as C;A=C.get_index_info(B.symbol)
		if not A:return pd.DataFrame()
		return pd.DataFrame([A])
	def description(A):'Get description for this index.';from vnstock.common import indices as B;return B.get_index_description(A.symbol)
class IndexReference(BaseDomain):
	'\n    Index Reference Data (Layer 1).\n    Acts as a Hub for index listings and navigating to specific index details.\n    '
	def __init__(A):super().__init__(domain_name=bytes([105,110,100,101,120]).decode(),layer_sources=REFERENCE_SOURCES)
	def __call__(A,symbol):"\n        Access details for a specific index.\n        \n        Args:\n            symbol (str): Index symbol (e.g., 'VN30').\n            \n        Returns:\n            IndexDetail: Object to access index-specific data.\n        ";return IndexDetail(symbol,A._sources_config)
	def groups(A):'\n        List all supported index groups and categories.\n        ';return A._dispatch(bytes([103,114,111,117,112,115]).decode())
	def members(A,group):"\n        List constituents/members of the specified index.\n        \n        Args:\n            group (str): Index symbol (e.g., 'VN30').\n        ";return A(group).members()
	def list(B):'\n        List all standardized market indices with metadata.\n        \n        Returns:\n            DataFrame with columns:\n            - symbol: Index symbol (VN30, VNIT, etc.)\n            - name: Index name\n            - description: Vietnamese description\n            - full_name: Full English name\n            - group: Index group (HOSE Indices, Sector Indices, etc.)\n            - index_id: Unique index ID\n            - sector_id: ICB sector ID (for sector indices only)\n        ';from vnstock.common import indices as A;return A.get_all_indices()
	def list_by_group(E,group=bytes([86,78,51,48]).decode()):
		"\n        List market indices by group/category.\n        \n        Args:\n            group (str): Index group name (e.g., 'vn30', 'Hose'). Default 'VN30'.\n        \n        Returns:\n            DataFrame with index information filtered by group.\n        ";A=group;from vnstock.common import indices as B
		if isinstance(A,str):
			D=A.upper().strip()
			if A in B.get_all_index_groups():return B.get_indices_by_group(A)
			for C in B.get_all_index_groups():
				if D in C.upper():return B.get_indices_by_group(C)
		return pd.DataFrame()