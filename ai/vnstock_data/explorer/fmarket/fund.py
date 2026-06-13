from datetime import datetime
import pandas as pd
from pandas import json_normalize
from vnai import optimize_execution
from vnstock.core.utils.logger import get_logger
from vnstock.explorer.fmarket.const import _BASE_URL,_FUND_LIST_COLUMNS,_FUND_LIST_MAPPING,_FUND_TYPE_MAPPING
from vnstock_data.core.utils.client import send_request
from vnstock_data.core.utils.user_agent import get_headers
logger=get_logger(__name__)
def convert_unix_to_datetime(df_to_convert,columns):
	'Converts all the specified columns of a dataframe to date format and fill NaN for negative values.';A=df_to_convert.copy()
	for B in columns:A[B]=pd.to_datetime(A[B],unit=bytes([109,115]).decode(),utc=True,errors=bytes([99,111,101,114,99,101]).decode()).dt.strftime(bytes([37,89,45,37,109,45,37,100]).decode());A[B]=A[B].where(A[B].ge(bytes([49,57,55,48,45,48,49,45,48,49]).decode()))
	return A
class Fund:
	def __init__(A,random_agent=False):'\n        Khởi tạo đối tượng để truy cập dữ liệu từ Fmarket.\n        ';B=random_agent;A.random_agent=B;A.data_source=bytes([102,109,97,114,107,101,116]).decode();A.headers=get_headers(data_source=A.data_source,random_agent=B);A.base_url=_BASE_URL;A.fund_list=A.listing()[bytes([115,104,111,114,116,95,110,97,109,101]).decode()].to_list();A.details=A.FundDetails(A)
	@optimize_execution(bytes([70,77,75,46,101,120,116]).decode())
	def listing(self,fund_type=''):
		"\n        Truy xuất danh sách tất cả các quỹ mở hiện có trên Fmarket thông qua API. Xem trực tiếp tại https://fmarket.vn\n\n        Tham số:\n        ----------\n            fund_type (str): Loại quỹ cần lọc. Mặc định là rỗng để lấy tất cả các quỹ. Các loại quỹ hợp lệ bao gồm: 'BALANCED', 'BOND', 'STOCK'\n        \n        Trả về:\n        -------\n            pd.DataFrame: DataFrame chứa thông tin của tất cả các quỹ mở hiện có trên Fmarket. \n        ";B=fund_type;B=B.upper();D=_FUND_TYPE_MAPPING.get(B,[])
		if B not in{'',bytes([66,65,76,65,78,67,69,68]).decode(),bytes([66,79,78,68]).decode(),bytes([83,84,79,67,75]).decode()}:logger.warning(f"Unsupported fund type: '{B}'. Please choose from: '' to get all funds or specify one of 'BALANCED', 'BOND', or 'STOCK'.")
		E={bytes([116,121,112,101,115]).decode():[bytes([78,69,87,95,70,85,78,68]).decode(),bytes([84,82,65,68,73,78,71,95,70,85,78,68]).decode()],bytes([105,115,115,117,101,114,73,100,115]).decode():[],bytes([115,111,114,116,79,114,100,101,114]).decode():bytes([68,69,83,67]).decode(),bytes([115,111,114,116,70,105,101,108,100]).decode():bytes([110,97,118,84,111,54,77,111,110,116,104,115]).decode(),bytes([112,97,103,101]).decode():1,bytes([112,97,103,101,83,105,122,101]).decode():100,bytes([105,115,73,112,111]).decode():False,bytes([102,117,110,100,65,115,115,101,116,84,121,112,101,115]).decode():D,bytes([98,111,110,100,82,101,109,97,105,110,80,101,114,105,111,100,115]).decode():[],bytes([115,101,97,114,99,104,70,105,101,108,100]).decode():'',bytes([105,115,66,117,121,66,121,82,101,119,97,114,100]).decode():False,bytes([116,104,105,114,100,65,112,112,73,100,115]).decode():[]};F=f"{_BASE_URL}/filter"
		try:G=send_request(url=F,method=bytes([80,79,83,84]).decode(),headers=self.headers,payload=E,show_log=False);C=G;logger.info(bytes([84,111,116,97,108,32,110,117,109,98,101,114,32,111,102,32,102,117,110,100,115,32,99,117,114,114,101,110,116,108,121,32,108,105,115,116,101,100,32,111,110,32,70,109,97,114,107,101,116,58,32]).decode()+str(C[bytes([100,97,116,97]).decode()][bytes([116,111,116,97,108]).decode()]));A=json_normalize(C,record_path=[bytes([100,97,116,97]).decode(),bytes([114,111,119,115]).decode()]);A=A[_FUND_LIST_COLUMNS];A=convert_unix_to_datetime(df_to_convert=A,columns=[bytes([102,105,114,115,116,73,115,115,117,101,65,116]).decode(),bytes([112,114,111,100,117,99,116,78,97,118,67,104,97,110,103,101,46,117,112,100,97,116,101,65,116]).decode()]);A=A.sort_values(by=bytes([112,114,111,100,117,99,116,78,97,118,67,104,97,110,103,101,46,110,97,118,84,111,51,54,77,111,110,116,104,115]).decode(),ascending=False);A.rename(columns=_FUND_LIST_MAPPING,inplace=True);A=A.reset_index(drop=True);return A
		except Exception as H:logger.error(f"Error in API response: {H!s}");raise
	class FundDetails:
		def __init__(A,parent):A.parent=parent
		@optimize_execution(bytes([70,77,75,46,101,120,116]).decode())
		def top_holding(self,symbol=bytes([83,83,73,83,67,65]).decode()):return self._get_fund_details(symbol,bytes([116,111,112,95,104,111,108,100,105,110,103]).decode())
		@optimize_execution(bytes([70,77,75,46,101,120,116]).decode())
		def industry_holding(self,symbol=bytes([83,83,73,83,67,65]).decode()):return self._get_fund_details(symbol,bytes([105,110,100,117,115,116,114,121,95,104,111,108,100,105,110,103]).decode())
		@optimize_execution(bytes([70,77,75,46,101,120,116]).decode())
		def nav_report(self,symbol=bytes([83,83,73,83,67,65]).decode()):return self._get_fund_details(symbol,bytes([110,97,118,95,114,101,112,111,114,116]).decode())
		@optimize_execution(bytes([70,77,75,46,101,120,116]).decode())
		def asset_holding(self,symbol=bytes([83,83,73,83,67,65]).decode()):return self._get_fund_details(symbol,bytes([97,115,115,101,116,95,104,111,108,100,105,110,103]).decode())
		def _get_fund_details(B,symbol,section):
			"\n            Internal method to retrieve fund details for a specific section.\n\n            Parameters\n            ----------\n                symbol : str\n                    ticker of a fund. A.k.a fund short name\n                section : str\n                    section of data to retrieve. Options: 'top_holding', 'industry_holding', 'nav_report', 'asset_holding'\n\n            Returns\n            -------\n                df : pd.DataFrame\n                    DataFrame of the current top holdings of the selected fund.\n            ";C=section;A=symbol;A=A.upper()
			if A not in B.parent.fund_list:logger.error(f"Error: {A} is not a valid input. Call the listing() method for the list of valid Fund short_name.");raise ValueError(f"Invalid symbol: {A}")
			try:G=int(B.parent.filter(A)[bytes([105,100]).decode()][0]);logger.info(f"Retrieving data for {A}")
			except Exception as D:logger.error(f"An unexpected error occurred: {D!s}");raise
			E={bytes([116,111,112,95,104,111,108,100,105,110,103]).decode():B.parent.top_holding,bytes([105,110,100,117,115,116,114,121,95,104,111,108,100,105,110,103]).decode():B.parent.industry_holding,bytes([110,97,118,95,114,101,112,111,114,116]).decode():B.parent.nav_report,bytes([97,115,115,101,116,95,104,111,108,100,105,110,103]).decode():B.parent.asset_holding}
			if C in E:
				try:F=E[C](fundId=G)
				except KeyError as D:logger.error(f"Error: Missing expected columns in the response data - {D!s}");raise ValueError(f"Missing expected columns in the response data - {D!s}")
				F[bytes([115,104,111,114,116,95,110,97,109,101]).decode()]=A;return F
			else:logger.error(f"Error: {C} is not a valid input. 4 current options are: top_holding, industry_holding, nav_report, asset_holding");raise ValueError(f"Invalid section: {C}")
	@optimize_execution(bytes([70,77,75,46,101,120,116]).decode())
	def filter(self,symbol=''):
		'\n        Truy xuất danh sách quỹ theo tên viết tắt (short_name) và mã id của quỹ. Mặc định là rỗng để liệt kê tất cả các quỹ.\n\n        Tham số:\n        ----------\n            symbol (str): Tên viết tắt của quỹ cần tìm kiếm. Mặc định là rỗng để lấy tất cả các quỹ.\n\n        Trả về:\n        -------\n            pd.DataFrame: DataFrame chứa thông tin của quỹ cần tìm kiếm.\n        ';A=symbol;A=A.upper();C={bytes([115,101,97,114,99,104,70,105,101,108,100]).decode():A,bytes([116,121,112,101,115]).decode():[bytes([78,69,87,95,70,85,78,68]).decode(),bytes([84,82,65,68,73,78,71,95,70,85,78,68]).decode()],bytes([112,97,103,101,83,105,122,101]).decode():100};D=f"{_BASE_URL}/filter"
		try:
			E=send_request(url=D,method=bytes([80,79,83,84]).decode(),headers=self.headers,payload=C,show_log=False);F=E;B=json_normalize(F,record_path=[bytes([100,97,116,97]).decode(),bytes([114,111,119,115]).decode()])
			if not B.empty:G=[bytes([105,100]).decode(),bytes([115,104,111,114,116,78,97,109,101]).decode()];B=B[G];return B
			else:raise ValueError(f"No fund found with this symbol {A}. See funds_listing() for the list of valid Fund short names.")
		except Exception as H:logger.error(f"Error in API response: {H!s}");raise
	@optimize_execution(bytes([70,77,75,46,101,120,116]).decode())
	def top_holding(self,fundId=23):
		'\n        Retrieve list of top 10 holdings in the specified fund. Live data is retrieved from the Fmarket API.\n\n        Parameters\n        ----------\n            fundId : int\n                id of a fund in fmarket database\n        Returns\n        -------\n            df : pd.DataFrame\n                DataFrame of the current top 10 holdings of the selected fund.\n        ';D=fundId;F=f"{_BASE_URL}/{D}"
		try:
			G=send_request(url=F,method=bytes([71,69,84]).decode(),headers=self.headers,show_log=False);E=G;A=pd.DataFrame();B=json_normalize(E,record_path=[bytes([100,97,116,97]).decode(),bytes([112,114,111,100,117,99,116,84,111,112,72,111,108,100,105,110,103,76,105,115,116]).decode()])
			if not B.empty:B=convert_unix_to_datetime(df_to_convert=B,columns=[bytes([117,112,100,97,116,101,65,116]).decode()]);A=pd.concat([A,B])
			C=json_normalize(E,record_path=[bytes([100,97,116,97]).decode(),bytes([112,114,111,100,117,99,116,84,111,112,72,111,108,100,105,110,103,66,111,110,100,76,105,115,116]).decode()])
			if not C.empty:C=convert_unix_to_datetime(df_to_convert=C,columns=[bytes([117,112,100,97,116,101,65,116]).decode()]);A=pd.concat([A,C])
			if not A.empty:A[bytes([102,117,110,100,73,100]).decode()]=int(D);H=[bytes([115,116,111,99,107,67,111,100,101]).decode(),bytes([105,110,100,117,115,116,114,121]).decode(),bytes([110,101,116,65,115,115,101,116,80,101,114,99,101,110,116]).decode(),bytes([116,121,112,101]).decode(),bytes([117,112,100,97,116,101,65,116]).decode(),bytes([102,117,110,100,73,100]).decode()];I=[B for B in H if B in A.columns];A=A[I];J={bytes([115,116,111,99,107,67,111,100,101]).decode():bytes([115,116,111,99,107,95,99,111,100,101]).decode(),bytes([105,110,100,117,115,116,114,121]).decode():bytes([105,110,100,117,115,116,114,121]).decode(),bytes([110,101,116,65,115,115,101,116,80,101,114,99,101,110,116]).decode():bytes([110,101,116,95,97,115,115,101,116,95,112,101,114,99,101,110,116]).decode(),bytes([116,121,112,101]).decode():bytes([116,121,112,101,95,97,115,115,101,116]).decode(),bytes([117,112,100,97,116,101,65,116]).decode():bytes([117,112,100,97,116,101,95,97,116]).decode()};K={B:C for(B,C)in J.items()if B in A.columns};A.rename(columns=K,inplace=True);return A
			else:logger.warning(f"No data available for fundId {D}.");return pd.DataFrame()
		except Exception as L:logger.error(f"Error in API response: {L!s}");raise
	@optimize_execution(bytes([70,77,75,46,101,120,116]).decode())
	def industry_holding(self,fundId=23):
		'Retrieve list of industries and fund distribution for specific fundID. Live data is retrieved from the Fmarket API.\n\n        Parameters\n        ----------\n            fundId : int\n                id of a fund in fmarket database\n\n        Returns\n        -------\n            df : pd.DataFrame\n                DataFrame of the current top industries in the selected fund.\n        ';B=f"{_BASE_URL}/{fundId}"
		try:C=send_request(url=B,method=bytes([71,69,84]).decode(),headers=self.headers,show_log=False);D=C;A=json_normalize(D,record_path=[bytes([100,97,116,97]).decode(),bytes([112,114,111,100,117,99,116,73,110,100,117,115,116,114,105,101,115,72,111,108,100,105,110,103,76,105,115,116]).decode()]);E=[bytes([105,110,100,117,115,116,114,121]).decode(),bytes([97,115,115,101,116,80,101,114,99,101,110,116]).decode()];F=[B for B in E if B in A.columns];A=A[F];G={bytes([105,110,100,117,115,116,114,121]).decode():bytes([105,110,100,117,115,116,114,121]).decode(),bytes([97,115,115,101,116,80,101,114,99,101,110,116]).decode():bytes([110,101,116,95,97,115,115,101,116,95,112,101,114,99,101,110,116]).decode()};H={B:C for(B,C)in G.items()if B in A.columns};A.rename(columns=H,inplace=True);return A
		except Exception as I:logger.error(f"Error in API response: {I!s}");raise
	@optimize_execution(bytes([70,77,75,46,101,120,116]).decode())
	def nav_report(self,fundId=23):
		'Retrieve all available daily NAV data point of the specified fund. Live data is retrieved from the Fmarket API.\n\n        Parameters\n        ----------\n            fundId : int\n                id of a fund in fmarket database.\n\n        Returns\n        -------\n            df : pd.DataFrame\n                DataFrame of all avalaible daily NAV data points of the selected fund.\n        ';B=fundId;C=datetime.now().strftime(bytes([37,89,37,109,37,100]).decode());D=_BASE_URL[:-1]+bytes([47,103,101,116,45,110,97,118,45,104,105,115,116,111,114,121]).decode();E={bytes([105,115,65,108,108,68,97,116,97]).decode():1,bytes([112,114,111,100,117,99,116,73,100]).decode():B,bytes([102,114,111,109,68,97,116,101]).decode():None,bytes([116,111,68,97,116,101]).decode():C}
		try:
			F=send_request(url=D,method=bytes([80,79,83,84]).decode(),headers=self.headers,payload=E,show_log=False);G=F;A=json_normalize(G,record_path=[bytes([100,97,116,97]).decode()])
			if not A.empty:H=[bytes([110,97,118,68,97,116,101]).decode(),bytes([110,97,118]).decode()];I=[B for B in H if B in A.columns];A=A[I];J={bytes([110,97,118,68,97,116,101]).decode():bytes([100,97,116,101]).decode(),bytes([110,97,118]).decode():bytes([110,97,118,95,112,101,114,95,117,110,105,116]).decode()};K={B:C for(B,C)in J.items()if B in A.columns};A.rename(columns=K,inplace=True);return A
			else:raise ValueError(f"No data with this fund_id {B}")
		except Exception as L:logger.error(f"Error in API response: {L!s}");raise
	@optimize_execution(bytes([70,77,75,46,101,120,116]).decode())
	def asset_holding(self,fundId=23):
		'Retrieve list of assets holding allocation for specific fundID. Live data is retrieved from the Fmarket API.\n\n        Parameters\n        ----------\n            fundId : int\n                id of a fund in fmarket database.\n\n        Returns\n        -------\n            df : pd.DataFrame\n                DataFrame of assets holding allocation of the selected fund.\n        ';B=f"{_BASE_URL}/{fundId}"
		try:C=send_request(url=B,method=bytes([71,69,84]).decode(),headers=self.headers,show_log=False);D=C;A=json_normalize(D,record_path=[bytes([100,97,116,97]).decode(),bytes([112,114,111,100,117,99,116,65,115,115,101,116,72,111,108,100,105,110,103,76,105,115,116]).decode()]);E=[bytes([97,115,115,101,116,80,101,114,99,101,110,116]).decode(),bytes([97,115,115,101,116,84,121,112,101,46,110,97,109,101]).decode()];F=[B for B in E if B in A.columns];A=A[F];G={bytes([97,115,115,101,116,80,101,114,99,101,110,116]).decode():bytes([97,115,115,101,116,95,112,101,114,99,101,110,116]).decode(),bytes([97,115,115,101,116,84,121,112,101,46,110,97,109,101]).decode():bytes([97,115,115,101,116,95,116,121,112,101]).decode()};H={B:C for(B,C)in G.items()if B in A.columns};A.rename(columns=H,inplace=True);return A
		except Exception as I:logger.error(f"Error in API response: {I!s}");raise
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([102,117,110,100]).decode(),bytes([102,109,97,114,107,101,116]).decode(),Fund)