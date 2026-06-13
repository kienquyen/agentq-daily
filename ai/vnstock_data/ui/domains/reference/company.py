'\nCompany Reference Domain.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDetail
from vnstock_data.ui._registry import REFERENCE_SOURCES
class CompanyReference(BaseDetail):
	'\n    Company Reference Data (Layer 1).\n    Wraps functionality for retrieving company-specific static data.\n    '
	def __init__(A,symbol):super().__init__(symbol=symbol,domain_name=bytes([99,111,109,112,97,110,121]).decode(),layer_sources=REFERENCE_SOURCES)
	def info(A):'Get company info/overview.';return A._dispatch(bytes([105,110,102,111]).decode())
	def shareholders(A):'Get company shareholders.';return A._dispatch(bytes([115,104,97,114,101,104,111,108,100,101,114,115]).decode())
	def officers(A,filter_by=bytes([119,111,114,107,105,110,103]).decode()):"\n        Get company officers.\n        \n        Args:\n            filter_by (str): 'working', 'resigned', or 'all'. Default 'working'.\n        ";return A._dispatch(bytes([111,102,102,105,99,101,114,115]).decode(),filter_by=filter_by)
	def subsidiaries(A,filter_by=bytes([97,108,108]).decode()):"\n        Get company subsidiaries.\n        \n        Args:\n             filter_by (str): 'all', 'subsidiary', 'affiliate'. Default 'all'.\n        ";return A._dispatch(bytes([115,117,98,115,105,100,105,97,114,105,101,115]).decode(),filter_by=filter_by)
	def news(A):'Get company news.';return A._dispatch(bytes([110,101,119,115]).decode())
	def events(A):'Get company events.';return A._dispatch(bytes([101,118,101,110,116,115]).decode())
	def margin_ratio(A):'Get margin lending ratio for the company across brokers.';return A._dispatch(bytes([109,97,114,103,105,110,95,114,97,116,105,111]).decode())