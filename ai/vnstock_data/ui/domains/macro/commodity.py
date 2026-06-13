'\nCommodity Market Domain (Layer 6).\nWraps the `spl.commodity.CommodityPrice` module for global and local commodity prices.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDetail
from vnstock_data.ui._registry import MACRO_SOURCES
from vnstock_data.ui.schemas.core import standardize_columns
class CommodityReference(BaseDetail):
	'\n    Access point for fetching commodity prices (Gold, Gas, Oil, Steel, etc.).\n    '
	def __init__(A):super().__init__(symbol=bytes([77,65,67,82,79]).decode(),domain_name=bytes([109,97,99,114,111,46,99,111,109,109,111,100,105,116,121]).decode(),layer_sources=MACRO_SOURCES)
	def _dispatch_and_format(B,method_name,**E):
		'\n        Dispatches method to SPL CommodityPrice and standardizes columns.\n        ';C=method_name;A=B._dispatch(C,**E)
		if A.empty:return A
		from vnstock_data.ui.config import get_route as F;G,D,D,D=F(B._domain_name,C,B._sources_config);H=bytes([109,97,99,114,111,46,99,111,109,109,111,100,105,116,121]).decode();A=standardize_columns(A,f"{H}.{C}",G,strict=False)
		if A.index.name==bytes([116,105,109,101]).decode()or A.index.name==bytes([114,101,112,111,114,116,95,116,105,109,101]).decode():
			A=A.reset_index()
			if bytes([116,105,109,101]).decode()in A.columns:A=A.rename(columns={bytes([116,105,109,101]).decode():bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()})
			A[bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()]=pd.to_datetime(A[bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()]);A=A.set_index(bytes([114,101,112,111,114,116,95,116,105,109,101]).decode())
		return A
	def gold(A,market=bytes([86,78]).decode(),**B):
		"\n        Gold prices.\n        \n        Args:\n            market (str): 'VN' for Vietnam SJC/local gold, 'GLOBAL' for GC=F international futures.\n        "
		if str(market).upper()==bytes([71,76,79,66,65,76]).decode():return A._dispatch_and_format(bytes([103,111,108,100,95,103,108,111,98,97,108]).decode(),**B)
		return A._dispatch_and_format(bytes([103,111,108,100,95,118,110]).decode(),**B)
	def gas(A,market=bytes([86,78]).decode(),**B):
		"\n        Gas prices. Note: 'GLOBAL' returns natural gas futures. 'VN' returns aggregated RON/DO prices.\n        "
		if str(market).upper()==bytes([71,76,79,66,65,76]).decode():return A._dispatch_and_format(bytes([103,97,115,95,110,97,116,117,114,97,108]).decode(),**B)
		return A._dispatch_and_format(bytes([103,97,115,95,118,110]).decode(),**B)
	def oil_crude(A,**B):'Crude Oil prices.';return A._dispatch_and_format(bytes([111,105,108,95,99,114,117,100,101]).decode(),**B)
	def coke(A,**B):'Coke (Coal) prices.';return A._dispatch_and_format(bytes([99,111,107,101]).decode(),**B)
	def steel(A,market=bytes([71,76,79,66,65,76]).decode(),**B):
		"Steel prices. 'GLOBAL' for HRC1!, 'VN' for D10."
		if str(market).upper()==bytes([86,78]).decode():return A._dispatch_and_format(bytes([115,116,101,101,108,95,100,49,48]).decode(),**B)
		return A._dispatch_and_format(bytes([115,116,101,101,108,95,104,114,99]).decode(),**B)
	def iron_ore(A,**B):'Iron ore prices.';return A._dispatch_and_format(bytes([105,114,111,110,95,111,114,101]).decode(),**B)
	def fertilizer_ure(A,**B):'Fertilizer URE prices.';return A._dispatch_and_format(bytes([102,101,114,116,105,108,105,122,101,114,95,117,114,101]).decode(),**B)
	def soybean(A,**B):'Soybean prices.';return A._dispatch_and_format(bytes([115,111,121,98,101,97,110]).decode(),**B)
	def corn(A,**B):'Corn prices.';return A._dispatch_and_format(bytes([99,111,114,110]).decode(),**B)
	def sugar(A,**B):'Sugar prices.';return A._dispatch_and_format(bytes([115,117,103,97,114]).decode(),**B)
	def pork(A,market=bytes([86,78]).decode(),**B):
		"Pork prices. 'VN' for local North Pig, 'CHINA' for China market."
		if str(market).upper()==bytes([67,72,73,78,65]).decode():return A._dispatch_and_format(bytes([112,111,114,107,95,99,104,105,110,97]).decode(),**B)
		return A._dispatch_and_format(bytes([112,111,114,107,95,118,110]).decode(),**B)