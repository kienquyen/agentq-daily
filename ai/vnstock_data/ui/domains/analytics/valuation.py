'\nValuation Domain (Insights Layer).\n'
import pandas as pd
from vnstock_data.ui._base import BaseDomain
from vnstock_data.ui._registry import INSIGHTS_SOURCES
from vnstock_data.ui.schemas.core import standardize_columns
class MarketValuation(BaseDomain):
	'\n    Market Valuation Insights.\n    Wraps provider methods (like vnd.market.Market) to provide\n    historical P/E and P/B ratios for an index.\n    '
	def __init__(A,index=bytes([86,78,73,78,68,69,88]).decode()):super().__init__(domain_name=bytes([105,110,115,105,103,104,116,115,46,118,97,108,117,97,116,105,111,110]).decode(),layer_sources=INSIGHTS_SOURCES);A.index=index
	def _dispatch_custom(B,method_name,**G):
		'\n        Custom dispatch to inject the index parameter during initialization\n        for providers that require it (like vnd.market.Market).\n        ';D=method_name;import importlib as H;from vnstock_data.core.registry import ProviderRegistry as E;from vnstock_data.ui.config import get_route as I;A,C,N,J=I(B._domain_name,D,B._sources_config)
		if not E.is_registered(C,A):
			try:H.import_module(f"vnstock_data.explorer.{A}.{C}")
			except ImportError:pass
		F=E.get(C,A)
		if not F:raise ValueError(f"Provider not found for {A}.{C}")
		K=F(index=B.index);L=getattr(K,J);M=L(**G);return standardize_columns(M,f"{B._domain_name}.{D}",A,strict=True)
	def pe(A,duration=bytes([53,89]).decode(),**B):'Retrieves P/E (Price-to-Earnings) ratio data.';return A._dispatch_custom(bytes([112,101]).decode(),duration=duration,**B)
	def pb(A,duration=bytes([53,89]).decode(),**B):'Retrieves P/B (Price-to-Book) ratio data.';return A._dispatch_custom(bytes([112,98]).decode(),duration=duration,**B)
	def evaluation(A,duration=bytes([53,89]).decode(),**B):'Retrieves an overview of the market with both P/E and P/B ratios.';return A._dispatch_custom(bytes([101,118,97,108,117,97,116,105,111,110]).decode(),duration=duration,**B)