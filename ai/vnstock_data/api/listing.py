from functools import wraps
from typing import Any
from tenacity import retry,stop_after_attempt,wait_exponential
from vnstock_data.base import BaseAdapter,dynamic_method
from vnstock_data.config import Config
from vnstock_data.enums import IndexGroup
def source_required(func):
	'Decorator to ensure source is specified for source-specific methods.\n    \n    This decorator is applied BEFORE @retry so that ValueError from missing source\n    is raised immediately without retry logic.\n    ';A=func;B=A.__name__
	@wraps(A)
	def C(self,*C,**D):
		if self._provider is None:raise ValueError(bytes([77,101,116,104,111,100,32,39]).decode()+B+bytes([40,41,39,32,114,101,113,117,105,114,101,115,32,97,32,100,97,116,97,32,115,111,117,114,99,101,46,32]).decode()+bytes([73,110,105,116,105,97,108,105,122,101,32,119,105,116,104,32,76,105,115,116,105,110,103,40,115,111,117,114,99,101,61,39,118,99,105,39,124,39,107,98,115,39,124,39,118,110,100,39,41,32]).decode()+bytes([111,114,32,117,115,101,32,115,111,117,114,99,101,45,105,110,100,101,112,101,110,100,101,110,116,32,109,101,116,104,111,100,115,32,108,105,107,101,32,97,108,108,95,105,110,100,105,99,101,115,40,41,44,32,105,110,100,105,99,101,115,95,98,121,95,103,114,111,117,112,40,41,46]).decode())
		return A(self,*C,**D)
	return C
def _normalize_index_group(group):
	"\n    Normalize short index group names to their full names.\n    \n    Accepts both enum values and string values:\n        'HOSE' or IndexGroup.HOSE -> 'HOSE Indices'\n        'SECTOR' or IndexGroup.SECTOR -> 'Sector Indices'\n        'INVESTMENT' or IndexGroup.INVESTMENT -> 'Investment Indices'\n        'VNX' or IndexGroup.VNX -> 'VNX Indices'\n    \n    Args:\n        group: Index group name or IndexGroup enum value\n        \n    Returns:\n        Full name of the index group, or original value if not mapped\n    ";A=group
	if A is None:return
	if isinstance(A,IndexGroup):return A.full_name
	B=str(A).upper().strip();C={bytes([72,79,83,69]).decode():bytes([72,79,83,69,32,73,110,100,105,99,101,115]).decode(),bytes([83,69,67,84,79,82]).decode():bytes([83,101,99,116,111,114,32,73,110,100,105,99,101,115]).decode(),bytes([73,78,86,69,83,84,77,69,78,84]).decode():bytes([73,110,118,101,115,116,109,101,110,116,32,73,110,100,105,99,101,115]).decode(),bytes([86,78,88]).decode():bytes([86,78,88,32,73,110,100,105,99,101,115]).decode()};return C.get(B,A)
class Listing(BaseAdapter):
	_module_name=bytes([108,105,115,116,105,110,103]).decode();bytes([10,32,32,32,32,65,100,97,112,116,101,114,32,102,111,114,32,108,105,115,116,105,110,103,32,100,97,116,97,58,10,32,32,32,32,32,32,45,32,97,108,108,95,115,121,109,98,111,108,115,10,32,32,32,32,32,32,45,32,115,121,109,98,111,108,115,95,98,121,95,105,110,100,117,115,116,114,105,101,115,10,32,32,32,32,32,32,45,32,115,121,109,98,111,108,115,95,98,121,95,101,120,99,104,97,110,103,101,10,32,32,32,32,32,32,45,32,105,110,100,117,115,116,114,105,101,115,95,105,99,98,10,32,32,32,32,32,32,45,32,115,121,109,98,111,108,115,95,98,121,95,103,114,111,117,112,10,32,32,32,32,32,32,45,32,97,108,108,95,102,117,116,117,114,101,95,105,110,100,105,99,101,115,10,32,32,32,32,32,32,45,32,97,108,108,95,103,111,118,101,114,110,109,101,110,116,95,98,111,110,100,115,10,32,32,32,32,32,32,45,32,97,108,108,95,99,111,118,101,114,101,100,95,119,97,114,114,97,110,116,10,32,32,32,32,32,32,45,32,97,108,108,95,98,111,110,100,115,10,10,32,32,32,32,85,115,97,103,101,58,10,32,32,32,32,32,32,32,32,108,115,116,32,61,32,76,105,115,116,105,110,103,40,115,111,117,114,99,101,61,34,118,99,105,34,44,32,114,97,110,100,111,109,95,97,103,101,110,116,61,70,97,108,115,101,44,32,115,104,111,119,95,108,111,103,61,84,114,117,101,41,10,32,32,32,32,32,32,32,32,100,102,32,61,32,108,115,116,46,97,108,108,95,115,121,109,98,111,108,115,40,116,111,95,100,102,61,84,114,117,101,41,10,32,32,32,32,32,32,32,32,100,102,50,32,61,32,108,115,116,46,115,121,109,98,111,108,115,95,98,121,95,101,120,99,104,97,110,103,101,40,108,97,110,103,61,34,101,110,34,41,10,32,32,32,32,32,32,32,32,105,100,120,32,61,32,108,115,116,46,105,110,100,117,115,116,114,105,101,115,95,105,99,98,40,41,10,32,32,32,32,32,32,32,32,103,114,111,117,112,32,61,32,108,115,116,46,115,121,109,98,111,108,115,95,98,121,95,103,114,111,117,112,40,103,114,111,117,112,61,34,86,78,51,48,34,41,10,32,32,32,32,32,32,32,32,102,117,32,61,32,108,115,116,46,97,108,108,95,102,117,116,117,114,101,95,105,110,100,105,99,101,115,40,41,10,32,32,32,32]).decode()
	def __init__(B,source=None,random_agent=False,show_log=False):
		C=show_log;A=source
		if A is not None and A.lower()not in[bytes([118,99,105]).decode(),bytes([107,98,115]).decode(),bytes([118,110,100]).decode()]:raise ValueError(bytes([76,225,187,155,112,32,76,105,115,116,105,110,103,32,99,104,225,187,137,32,110,104,225,186,173,110,32,103,105,195,161,32,116,114,225,187,139,32,116,104,97,109,32,115,225,187,145,32,115,111,117,114,99,101,32,108,195,160,32,39,86,67,73,39,44,32,39,75,66,83,39,32,104,111,225,186,183,99,32,39,86,78,68,39,46]).decode())
		B.source=A;B.show_log=C;B._provider=None
		if A is not None:super().__init__(source=A,random_agent=random_agent,show_log=C)
	def _ensure_provider(A,method_name):
		'Ensure provider is initialized for source-specific methods.'
		if A._provider is None:raise ValueError(bytes([77,101,116,104,111,100,32,39]).decode()+method_name+bytes([40,41,39,32,114,101,113,117,105,114,101,115,32,97,32,100,97,116,97,32,115,111,117,114,99,101,46,32]).decode()+bytes([73,110,105,116,105,97,108,105,122,101,32,119,105,116,104,32,76,105,115,116,105,110,103,40,115,111,117,114,99,101,61,39,118,99,105,39,124,39,107,98,115,39,124,39,118,110,100,39,41,32,111,114,32,117,115,101,32]).decode()+bytes([115,111,117,114,99,101,45,105,110,100,101,112,101,110,100,101,110,116,32,109,101,116,104,111,100,115,32,108,105,107,101,32,97,108,108,95,105,110,100,105,99,101,115,40,41,44,32]).decode()+bytes([105,110,100,105,99,101,115,95,98,121,95,103,114,111,117,112,40,41,46]).decode())
	@source_required
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def all_symbols(self,*A,**B):'Retrieve all symbols (filtered to STOCK).'
	@source_required
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def symbols_by_industries(self,*A,**B):'Retrieve symbols grouped by ICB industries.'
	@source_required
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def symbols_by_exchange(self,*A,**B):'Retrieve symbols by exchange/board.'
	@source_required
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def industries_icb(self,*A,**B):'Retrieve ICB code hierarchy and mapping.'
	@source_required
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def symbols_by_group(self,*A,**B):'Retrieve symbols by predefined group (VN30, HNX30, CW, etc.).'
	@source_required
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	def all_future_indices(self,**A):"Retrieve all futures indices (group='FU_INDEX').";return self.symbols_by_group(group=bytes([70,85,95,73,78,68,69,88]).decode(),**A)
	@source_required
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@source_required
	@dynamic_method
	def all_government_bonds(self,*A,**B):'Retrieve all government bonds.'
	@source_required
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	def all_covered_warrant(self,**A):"Retrieve all covered warrants (group='CW').";return self.symbols_by_group(group=bytes([67,87]).decode(),**A)
	@source_required
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	def all_bonds(self,**A):"Retrieve all bonds (group='BOND').";return self.symbols_by_group(group=bytes([66,79,78,68]).decode(),**A)
	@source_required
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def all_etf(self,*A,**B):'Retrieve all ETF (exchange-traded funds).'
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	def all_indices(self,*B,**C):'\n        Retrieve all standardized market indices with metadata.\n\n        Returns:\n            DataFrame with columns:\n            - symbol: Index symbol (VN30, VNIT, etc.)\n            - name: Index name\n            - description: Vietnamese description\n            - full_name: Full English name\n            - group: Index group (HOSE Indices, Sector Indices, etc.)\n            - index_id: Unique index ID\n            - sector_id: ICB sector ID (for sector indices only)\n        ';from vnstock.common import indices as A;return A.get_all_indices()
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	def indices_by_group(self,*B,**C):
		"\n        Retrieve standardized market indices by group/category.\n\n        Args:\n            group (str or IndexGroup): Index group name. Accepts both short names, \n                enum values, and full names:\n                - 'HOSE', IndexGroup.HOSE, or 'HOSE Indices' - HOSE market indices\n                - 'SECTOR', IndexGroup.SECTOR, or 'Sector Indices' - Sector indices\n                - 'INVESTMENT', IndexGroup.INVESTMENT, or 'Investment Indices' - Investment indices\n                - 'VNX', IndexGroup.VNX, or 'VNX Indices' - VNX market indices\n\n        Returns:\n            DataFrame with index information filtered by group,\n            or None if group not found.\n\n        Examples:\n            >>> from vnstock_data.api.listing import Listing\n            >>> from vnstock_data.enums import IndexGroup\n            >>> lst = Listing()\n            >>> # Using string short names\n            >>> lst.indices_by_group('HOSE')\n            >>> # Using enum values\n            >>> lst.indices_by_group(IndexGroup.SECTOR)\n            >>> # Using full names\n            >>> lst.indices_by_group('HOSE Indices')\n        ";from vnstock.common import indices as D;A=C.get(bytes([103,114,111,117,112]).decode())
		if A is None and len(B)>0:A=B[0]
		A=_normalize_index_group(A);return D.get_indices_by_group(A)