from datetime import datetime
import pandas as pd,requests
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake,get_asset_type
from vnstock_data.core.utils.browser import get_cookie
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.vds.const import _BASE_URL,_ORDER_MATCH_MAPPING
logger=get_logger(__name__)
class Quote:
	'\n    Truy xuất dữ liệu giao dịch của mã chứng khoán từ nguồn dữ liệu VDSC.\n    '
	def __init__(A,symbol,cookie=None,random_agent=False,show_log=False):
		C=show_log;B=cookie;A.symbol=symbol.upper();A.asset_type=get_asset_type(A.symbol);A.headers=get_headers(data_source=bytes([86,68,83]).decode(),random_agent=random_agent);A.headers[bytes([67,111,110,116,101,110,116,45,84,121,112,101]).decode()]=bytes([97,112,112,108,105,99,97,116,105,111,110,47,120,45,119,119,119,45,102,111,114,109,45,117,114,108,101,110,99,111,100,101,100,59,32,99,104,97,114,115,101,116,61,85,84,70,45,56]).decode()
		if B is None:B=get_cookie(bytes([104,116,116,112,115,58,47,47,108,105,118,101,100,114,97,103,111,110,46,118,100,115,99,46,99,111,109,46,118,110,47,103,101,110,101,114,97,108,47,105,110,116,114,97,100,97,121,66,111,97,114,100,46,114,118]).decode(),headers=A.headers);A.headers[bytes([67,111,111,107,105,101]).decode()]=B
		else:A.headers[bytes([67,111,111,107,105,101]).decode()]=B
		if not C:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
		A.show_log=C
	@agg_execution(bytes([86,68,83,46,101,120,116]).decode())
	def intraday(self,date=None):
		"\n        Get the matched transactions data for a specific stock symbol and date from Live Dragon website.\n\n        Parameters:\n            date (str): The date for which to retrieve the matched transactions data, in the format 'YYYY-MM-DD'. If None, today's date will be used.\n            cookie (str): The cookie value to include in the request headers. Default is None. If the automatic method fails, you may need to copy the actual cookie value from your web browser.\n        ";A=self
		if date is None:D=datetime.now()
		else:D=datetime.strptime(date,bytes([37,89,45,37,109,45,37,100]).decode())
		H=D.strftime(bytes([37,100,47,37,109,47,37,89]).decode());E=f"{_BASE_URL}general/intradaySearch.rv";F=f"stockCode={A.symbol}&boardDate={H}"
		if A.show_log:logger.info(f"Request data to {E}, using payload as details: {F}. Headers values: {A.headers}")
		C=requests.request(bytes([80,79,83,84]).decode(),E,headers=A.headers,data=F)
		if C.status_code!=200:logger.debug(f"Error: {C.text}")
		G=C.json()
		if A.show_log:logger.info(G)
		B=pd.DataFrame(G[bytes([108,105,115,116]).decode()]);B.columns=[camel_to_snake(A)for A in B.columns];B.rename(columns=_ORDER_MATCH_MAPPING,inplace=True);return B