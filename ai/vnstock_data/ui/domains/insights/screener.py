import pandas as pd
from vnstock_data.ui._base import BaseDomain
from vnstock_data.ui._registry import INSIGHTS_SOURCES
class ScreenerReference(BaseDomain):
	'\n    Sub-domain UI model for the Stock Screener feature.\n    Part of Layer 7 - Insights. Provides comprehensive data on all stock criteria\n    allowing users to convert to a DataFrame and perform custom filtering using Pandas.\n    '
	def __init__(A):super().__init__(domain_name=bytes([105,110,115,105,103,104,116,115,46,115,99,114,101,101,110,101,114]).decode(),layer_sources=INSIGHTS_SOURCES)
	def _dispatch(C,method_name,**H):
		'\n        Overwrite the _dispatch to use strict=False.\n        We want to return ALL data fields from the screener, so dropping columns is not ideal.\n        ';E=method_name;import importlib as I;from vnstock_data.core.registry import ProviderRegistry as F;from vnstock_data.ui.config import get_route as J;A,B,P,K=J(C._domain_name,E,C._sources_config)
		if not F.is_registered(B,A):
			try:I.import_module(f"vnstock_data.explorer.{A}.{B}")
			except ImportError:pass
		G=F.get(B,A)
		if not G:raise ValueError(f"Provider not found for {A}.{B}")
		L=G();M=getattr(L,K);D=M(**H);N=f"{C._domain_name}.{E}";from vnstock_data.ui.schemas.core import standardize_columns as O;D=O(D,N,A,strict=False);return D
	def criteria(A,lang=bytes([118,105]).decode(),**B):"\n        Retrieves the mapping list of criteria to explain field names (data columns).\n        \n        Args:\n            lang (str): Language ('vi' or 'en'). Defaults to 'vi'.\n            **kwargs: Additional parameters passed to the provider adapter.\n            \n        Returns:\n            pd.DataFrame: DataFrame mapping the field names.\n        ";return A._dispatch(bytes([99,114,105,116,101,114,105,97]).decode(),lang=lang,**B)
	def filter(A,limit=2000,**B):"\n        Retrieves full market data (all stocks) with all available criteria (ratios, metrics)\n        returning a comprehensive DataFrame of the market.\n        Users can apply advanced filtering logic directly on this DataFrame using Pandas,\n        or pass a custom list of filter conditions via the `filters` parameter.\n        \n        Args:\n            limit (int): Maximum number of records to retrieve. Defaults to 2000.\n            filters (List[Dict], optional): Custom filter conditions identical to the provider's filter payload. Defaults to None.\n            **kwargs: Additional parameters passed to the provider adapter.\n            \n        Returns:\n            pd.DataFrame: Screener data DataFrame containing metrics.\n        ";return A._dispatch(bytes([102,105,108,116,101,114]).decode(),limit=limit,**B)