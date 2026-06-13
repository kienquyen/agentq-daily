'\nFund Market Domain (Layer 2).\nWraps the `fmarket.fund` module for NAV history and portfolio holdings.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDetail
from vnstock_data.ui._registry import MARKET_SOURCES
from vnstock_data.ui.schemas.core import standardize_columns
class FundMarket(BaseDetail):
	"\n    Access point for fetching a specific fund's historical data and portfolio details.\n    "
	def __init__(A,symbol):super().__init__(symbol=symbol,domain_name=bytes([109,97,114,107,101,116,46,102,117,110,100]).decode(),layer_sources=MARKET_SOURCES)
	def _dispatch_and_format(A,method_name,**E):
		B=method_name;C=A._dispatch(B,**E)
		if C.empty:return C
		from vnstock_data.ui.config import get_route as F;G,D,D,D=F(A._domain_name,B,A._sources_config);H=bytes([109,97,114,107,101,116,46,102,117,110,100]).decode();return standardize_columns(C,f"{H}.{B}",G,strict=False)
	def history(A,**B):'\n        Extracts the historical Net Asset Value (NAV) of the fund over time.\n        ';return A._dispatch_and_format(bytes([104,105,115,116,111,114,121]).decode(),**B)
	def top_holding(A,**B):'\n        Extracts the top equity/bond holdings of the fund.\n        ';return A._dispatch_and_format(bytes([116,111,112,95,104,111,108,100,105,110,103]).decode(),**B)
	def industry_holding(A,**B):"\n        Extracts the industry weighting inside the fund's portfolio.\n        ";return A._dispatch_and_format(bytes([105,110,100,117,115,116,114,121,95,104,111,108,100,105,110,103]).decode(),**B)
	def asset_holding(A,**B):'\n        Extracts the asset allocation (Equities vs Cash/Bonds) of the fund.\n        ';return A._dispatch_and_format(bytes([97,115,115,101,116,95,104,111,108,100,105,110,103]).decode(),**B)