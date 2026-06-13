'\nFund Reference Domain (Layer 1).\nWraps the `fmarket.fund` module for global fund operations like listing.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDomain
from vnstock_data.ui._registry import REFERENCE_SOURCES
from vnstock_data.ui.schemas.core import standardize_columns
class FundReference(BaseDomain):
	'\n    Access point for listing mutual funds.\n    '
	def __init__(A):super().__init__(domain_name=bytes([114,101,102,101,114,101,110,99,101,46,102,117,110,100]).decode(),layer_sources=REFERENCE_SOURCES)
	def list(A):
		'\n        Extracts the list of all available mutual funds.\n        ';B=A._dispatch(bytes([108,105,115,116]).decode())
		if B is None or B.empty:return pd.DataFrame()
		from vnstock_data.ui.config import get_route as D;E,C,C,C=D(A._domain_name,bytes([108,105,115,116]).decode(),A._sources_config);return standardize_columns(B,f"{A._domain_name}.list",E,strict=True)