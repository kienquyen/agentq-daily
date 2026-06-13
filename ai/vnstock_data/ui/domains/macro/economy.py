'\nEconomy Reference Domain (Layer 6).\nWraps the `mbk.macro.Macro` module for generic macroeconomic indicators.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDetail
from vnstock_data.ui._registry import MACRO_SOURCES
from vnstock_data.ui.schemas.core import standardize_columns
class EconomyReference(BaseDetail):
	'\n    Access point for fetching macroeconomic data such as GDP, CPI, FDI, etc.\n    '
	def __init__(A):super().__init__(symbol=bytes([77,65,67,82,79]).decode(),domain_name=bytes([109,97,99,114,111,46,101,99,111,110,111,109,121]).decode(),layer_sources=MACRO_SOURCES)
	def _dispatch_and_format(A,method_name,**E):
		'\n        Dispatches method to MBK Macro and standardizes columns without strict trimming.\n        ';B=method_name;C=A._dispatch(B,**E)
		if C.empty:return C
		from vnstock_data.ui.config import get_route as F;G,D,D,D=F(A._domain_name,B,A._sources_config);H=bytes([109,97,99,114,111,46,101,99,111,110,111,109,121]).decode();return standardize_columns(C,f"{H}.{B}",G,strict=False)
	def gdp(A,**B):'GDP data.';return A._dispatch_and_format(bytes([103,100,112]).decode(),**B)
	def cpi(A,**B):'Consumer Price Index data.';return A._dispatch_and_format(bytes([99,112,105]).decode(),**B)
	def industry_prod(A,**B):'Industrial Production data.';return A._dispatch_and_format(bytes([105,110,100,117,115,116,114,121,95,112,114,111,100]).decode(),**B)
	def import_export(A,**B):'Import/Export macro data.';return A._dispatch_and_format(bytes([105,109,112,111,114,116,95,101,120,112,111,114,116]).decode(),**B)
	def retail(A,**B):'Retail macro data.';return A._dispatch_and_format(bytes([114,101,116,97,105,108]).decode(),**B)
	def fdi(A,**B):'Foreign Direct Investment data.';return A._dispatch_and_format(bytes([102,100,105]).decode(),**B)
	def money_supply(A,**B):'Money supply data.';return A._dispatch_and_format(bytes([109,111,110,101,121,95,115,117,112,112,108,121]).decode(),**B)
	def population_labor(A,**B):'Population and Labor data.';return A._dispatch_and_format(bytes([112,111,112,117,108,97,116,105,111,110,95,108,97,98,111,114]).decode(),**B)