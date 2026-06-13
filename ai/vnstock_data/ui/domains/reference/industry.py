'\nIndustry Reference Domain.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDomain
from vnstock_data.ui._registry import REFERENCE_SOURCES
class IndustryReference(BaseDomain):
	'\n    Industry Reference Data (Layer 1).\n    '
	def __init__(A):super().__init__(domain_name=bytes([105,110,100,117,115,116,114,121]).decode(),layer_sources=REFERENCE_SOURCES)
	def list(B,lang=bytes([118,105]).decode()):
		"\n        List ICB industry classifications for all symbols in the market.\n        Uses VCI as the data source over KBS because VCI provides deeper ICB levels (up to 4 levels).\n        \n        Note: The underlying data source may not be available in all environments \n        (e.g., might be blocked on Google Colab).\n        \n        Args:\n            lang (str): Language code 'vi' or 'en'. Default 'vi'.\n        ";A=B._dispatch(bytes([108,105,115,116]).decode())
		if lang==bytes([118,105]).decode():
			if bytes([101,110,95,105,99,98,95,110,97,109,101]).decode()in A.columns:A=A.drop(columns=[bytes([101,110,95,105,99,98,95,110,97,109,101]).decode()])
		elif lang==bytes([101,110]).decode():
			if bytes([105,99,98,95,110,97,109,101]).decode()in A.columns:A=A.drop(columns=[bytes([105,99,98,95,110,97,109,101]).decode()])
		return A
	def sectors(C,icb_code=None,lang=bytes([118,105]).decode()):
		"\n        List all symbols by their industry sectors.\n        \n        Args:\n            icb_code (str, optional): Filter by a specific ICB code.\n            lang (str): Language code 'vi' or 'en'. Default 'vi'.\n        ";B=icb_code;A=C._dispatch(bytes([115,101,99,116,111,114,115]).decode(),lang=lang)
		if A is not None and not A.empty and B is not None:A=A[A[bytes([105,99,98,95,99,111,100,101]).decode()]==B].reset_index(drop=True)
		return A