'\nBond Reference Domain (Layer 1).\n'
import pandas as pd
from vnstock_data.ui._base import BaseDomain
from vnstock_data.ui._registry import REFERENCE_SOURCES
class BondReference(BaseDomain):
	'\n    Bond Reference Data (Layer 1).\n    '
	def __init__(A):super().__init__(domain_name=bytes([98,111,110,100]).decode(),layer_sources=REFERENCE_SOURCES)
	def list(A,bond_type=bytes([97,108,108]).decode()):
		"\n        List bonds available in the market.\n        \n        Args:\n            bond_type (str): Type of bond to filter ('all', 'corporate', 'government'). Default is 'all'.\n                             - If 'corporate' or 'government', returns a pandas Series of symbols.\n                             - If 'all', returns a pandas DataFrame with 'symbol' and 'type' columns.\n                             \n        Note: The government bond data source might be restricted in some environments (e.g., Google Colab).\n        ";B=bond_type;import logging as F;D=[bytes([97,108,108]).decode(),bytes([99,111,114,112,111,114,97,116,101]).decode(),bytes([103,111,118,101,114,110,109,101,110,116]).decode()]
		if B not in D:raise ValueError(f"Invalid bond_type: {B}. Must be one of {D}.")
		if B==bytes([99,111,114,112,111,114,97,116,101]).decode():return A._dispatch(bytes([99,111,114,112,111,114,97,116,101]).decode())
		elif B==bytes([103,111,118,101,114,110,109,101,110,116]).decode():return A._dispatch(bytes([103,111,118,101,114,110,109,101,110,116]).decode())
		E=A._dispatch(bytes([99,111,114,112,111,114,97,116,101]).decode())
		try:C=A._dispatch(bytes([103,111,118,101,114,110,109,101,110,116]).decode())
		except Exception as G:F.warning(f"Could not fetch government bonds (source may be blocked): {G}");C=pd.Series(dtype=bytes([111,98,106,101,99,116]).decode())
		H=pd.DataFrame({bytes([115,121,109,98,111,108]).decode():E,bytes([116,121,112,101]).decode():bytes([99,111,114,112,111,114,97,116,101]).decode()})if getattr(E,bytes([101,109,112,116,121]).decode(),True)is False else pd.DataFrame(columns=[bytes([115,121,109,98,111,108]).decode(),bytes([116,121,112,101]).decode()]);I=pd.DataFrame({bytes([115,121,109,98,111,108]).decode():C,bytes([116,121,112,101]).decode():bytes([103,111,118,101,114,110,109,101,110,116]).decode()})if getattr(C,bytes([101,109,112,116,121]).decode(),True)is False else pd.DataFrame(columns=[bytes([115,121,109,98,111,108]).decode(),bytes([116,121,112,101]).decode()]);return pd.concat([H,I],ignore_index=True)