'\nEquity Reference Domain.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDomain
from vnstock_data.ui._registry import REFERENCE_SOURCES
class EquityReference(BaseDomain):
	'\n    Equity Reference Data (Layer 1).\n    '
	def __init__(A):super().__init__(domain_name=bytes([101,113,117,105,116,121]).decode(),layer_sources=REFERENCE_SOURCES)
	def list(A):'List all equity symbols.';return A._dispatch(bytes([108,105,115,116]).decode())
	def list_by_group(A,group):'\n        List equities by group (e.g., VN30, HOSE).\n        \n        Args:\n            group (str): Group code (VN30, HOSE, HNX, etc.)\n        ';return A._dispatch(bytes([98,121,95,103,114,111,117,112]).decode(),group=group)
	def list_by_industry(C,icb_code=None,lang=bytes([118,105]).decode()):
		"\n        List equities by industry (ICB classification).\n        \n        Args:\n            icb_code (str, optional): The ICB code to filter by (e.g., '8773'). If None, returns all.\n            lang (str): Language ('vi' or 'en'). Default 'vi'.\n            \n        Returns:\n            DataFrame: List of symbols related to the industry with ICB info.\n        ";B=icb_code;A=C._dispatch(bytes([98,121,95,105,110,100,117,115,116,114,121]).decode(),lang=lang)
		if A is not None and not A.empty and B is not None:A=A[A[bytes([105,99,98,95,99,111,100,101]).decode()]==B].reset_index(drop=True)
		return A
	def by_group(A,group):'[DEPRECATED] Use list_by_group() instead.';return A.list_by_group(group)
	def list_by_exchange(A):'List all equities organized by exchange.';return A._dispatch(bytes([98,121,95,101,120,99,104,97,110,103,101]).decode())
	def by_exchange(A):'[DEPRECATED] Use list_by_exchange() instead.';return A.list_by_exchange()