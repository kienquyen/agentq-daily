'\nCurrency Reference Domain (Layer 6).\nWraps the `mbk.macro.Macro.exchange_rate` module.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDetail
from vnstock_data.ui._registry import MACRO_SOURCES
from vnstock_data.ui.schemas.core import standardize_columns
class CurrencyReference(BaseDetail):
	'\n    Access point for fetching currency exchange rates.\n    '
	def __init__(A):super().__init__(symbol=bytes([77,65,67,82,79]).decode(),domain_name=bytes([109,97,99,114,111,46,99,117,114,114,101,110,99,121]).decode(),layer_sources=MACRO_SOURCES)
	def _dispatch_and_format(A,method_name,**E):
		'\n        Dispatches method to MBK Macro and standardizes columns without strict trimming.\n        ';B=method_name;C=A._dispatch(B,**E)
		if C.empty:return C
		from vnstock_data.ui.config import get_route as F;G,D,D,D=F(A._domain_name,B,A._sources_config);H=bytes([109,97,99,114,111,46,99,117,114,114,101,110,99,121]).decode();return standardize_columns(C,f"{H}.{B}",G,strict=False)
	def exchange_rate(A,**B):'Foreign exchange rates.';return A._dispatch_and_format(bytes([101,120,99,104,97,110,103,101,95,114,97,116,101]).decode(),**B)
	def interest_rate(A,**B):'Interest rates data.';return A._dispatch_and_format(bytes([105,110,116,101,114,101,115,116,95,114,97,116,101]).decode(),**B)