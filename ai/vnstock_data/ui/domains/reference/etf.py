'\nETF Reference Domain (Layer 1).\n'
import pandas as pd
from vnstock_data.ui._base import BaseDomain
from vnstock_data.ui._registry import REFERENCE_SOURCES
class ETFReference(BaseDomain):
	'\n    ETF Reference Data (Layer 1).\n    '
	def __init__(A):super().__init__(domain_name=bytes([101,116,102]).decode(),layer_sources=REFERENCE_SOURCES)
	def list(B):
		'\n        List all Exchange-Traded Funds (ETFs) available in the market.\n        ';A=B._dispatch(bytes([108,105,115,116]).decode())
		if A is None or A.empty:return pd.DataFrame()
		return A