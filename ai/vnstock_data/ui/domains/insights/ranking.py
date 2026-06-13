'\nRanking Domain (Insights Layer).\n'
import pandas as pd
from vnstock_data.ui._base import BaseDomain
from vnstock_data.ui._registry import INSIGHTS_SOURCES
from vnstock_data.ui.schemas.core import standardize_columns
class RankingReference(BaseDomain):
	'\n    Market Ranking Insights.\n    Wraps provider methods (like vnd.insight.TopStock) to identify\n    market movers based on volume, value, foreign flow, etc.\n    '
	def __init__(A):super().__init__(domain_name=bytes([105,110,115,105,103,104,116,115,46,114,97,110,107,105,110,103]).decode(),layer_sources=INSIGHTS_SOURCES)
	def _dispatch_and_format(A,method_name,**D):B=method_name;E=A._dispatch(B,**D);from vnstock_data.ui.config import get_route as F;G,C,C,C=F(A._domain_name,B,A._sources_config);return standardize_columns(E,f"{A._domain_name}.{B}",G,strict=True)
	def gainer(A,index=bytes([86,78,73,78,68,69,88]).decode(),limit=10,**B):'Top 10 stocks with highest price increase.';return A._dispatch_and_format(bytes([103,97,105,110,101,114]).decode(),index=index,limit=limit,**B)
	def loser(A,index=bytes([86,78,73,78,68,69,88]).decode(),limit=10,**B):'Top 10 stocks with highest price decrease.';return A._dispatch_and_format(bytes([108,111,115,101,114]).decode(),index=index,limit=limit,**B)
	def value(A,index=bytes([86,78,73,78,68,69,88]).decode(),limit=10,**B):'Top 10 stocks with highest trading value.';return A._dispatch_and_format(bytes([118,97,108,117,101]).decode(),index=index,limit=limit,**B)
	def volume(A,index=bytes([86,78,73,78,68,69,88]).decode(),limit=10,**B):'Top 10 stocks with highest volume spikes.';return A._dispatch_and_format(bytes([118,111,108,117,109,101]).decode(),index=index,limit=limit,**B)
	def deal(A,index=bytes([86,78,73,78,68,69,88]).decode(),limit=10,**B):'Top 10 stocks with highest put-through/deal volume spikes.';return A._dispatch_and_format(bytes([100,101,97,108]).decode(),index=index,limit=limit,**B)
	def foreign_buy(A,date=None,limit=10,**B):'Top 10 stocks with highest foreign net buy value.';return A._dispatch_and_format(bytes([102,111,114,101,105,103,110,95,98,117,121]).decode(),date=date,limit=limit,**B)
	def foreign_sell(A,date=None,limit=10,**B):'Top 10 stocks with highest foreign net sell value.';return A._dispatch_and_format(bytes([102,111,114,101,105,103,110,95,115,101,108,108]).decode(),date=date,limit=limit,**B)