'\nModule quản lý thông tin báo cáo tài chính từ nguồn dữ liệu MAS.\n'
import pandas as pd
from vnai import agg_execution
from vnstock.core.utils.client import send_request
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake
from vnstock.core.utils.transform import reorder_cols
from vnstock_data.core.utils.parser import get_asset_type
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.mas.const import _FINANCIAL_REPORT_MAP,_FINANCIAL_REPORT_PERIOD_MAP,_FINANCIAL_URL,SUPPORTED_LANGUAGES
logger=get_logger(__name__)
class Finance:
	"\n    Truy xuất thông tin báo cáo tài chính của một công ty theo mã chứng khoán từ nguồn dữ liệu MAS.\n\n    Tham số:\n        - symbol (str): Mã chứng khoán của công ty cần truy xuất thông tin.\n        - period (str): Chu kỳ báo cáo tài chính cần truy xuất. Mặc định là 'quarter'.\n        - get_all (bool): Trả về tất cả các trường dữ liệu hoặc chỉ các trường chọn lọc. Mặc định là True.\n        - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là True.\n    "
	def __init__(A,symbol,period=bytes([113,117,97,114,116,101,114]).decode(),get_all=True,show_log=True):
		'\n        Khởi tạo đối tượng Finance với các tham số cho việc truy xuất dữ liệu báo cáo tài chính.\n        ';C=show_log;B=period;A.symbol=symbol.upper();A.asset_type=get_asset_type(A.symbol);A.base_url=_FINANCIAL_URL;A.query_params=bytes([113,117,101,114,121,123,118,115,70,105,110,97,110,99,105,97,108,82,101,112,111,114,116,76,105,115,116,40,83,116,111,99,107,67,111,100,101,58,34,84,65,82,71,69,84,95,83,89,77,66,79,76,34,44,84,121,112,101,58,34,84,65,82,71,69,84,95,84,89,80,69,34,44,84,101,114,109,84,121,112,101,58,34,84,65,82,71,69,84,95,80,69,82,73,79,68,34,41,123,95,105,100,44,73,68,44,84,101,114,109,67,111,100,101,44,89,101,97,114,80,101,114,105,111,100,44,67,111,110,116,101,110,116,123,86,97,108,117,101,115,123,78,97,109,101,44,78,97,109,101,69,110,44,86,97,108,117,101,125,125,125,125]).decode();A.headers=get_headers(data_source=bytes([77,65,83]).decode());A.show_log=C
		if not C:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
		if B not in[bytes([121,101,97,114]).decode(),bytes([113,117,97,114,116,101,114]).decode()]:raise ValueError(bytes([75,225,187,179,32,98,195,161,111,32,99,195,161,111,32,116,195,160,105,32,99,104,195,173,110,104,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,104,225,186,165,112,32,110,104,225,186,173,110,32,39,121,101,97,114,39,32,104,111,225,186,183,99,32,39,113,117,97,114,116,101,114,39,46]).decode())
		A.raw_period=B;A.period=_FINANCIAL_REPORT_PERIOD_MAP.get(B)
		if A.asset_type not in[bytes([115,116,111,99,107]).decode()]:raise ValueError(bytes([77,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,225,187,149,32,112,104,105,225,186,191,117,32,109,225,187,155,105,32,99,195,179,32,116,104,195,180,110,103,32,116,105,110,46]).decode())
		A.get_all=get_all
	def _flatten_content(F,content,lang):
		"\n        Flatten a nested content structure based on the language.\n\n        Args:\n            content: A nested data structure (typically a list with a dict containing key 'Values').\n            lang (str): 'en' or 'vi'; uses 'NameEn' for 'en' and 'Name' for 'vi'.\n\n        Returns:\n            dict: Mapping of selected (trimmed) names to their values.\n        ";C=content
		if isinstance(C,list):
			for B in C:
				if isinstance(B,dict)and bytes([86,97,108,117,101,115]).decode()in B:
					D={}
					for A in B[bytes([86,97,108,117,101,115]).decode()]:
						if isinstance(A,dict):
							E=A.get(bytes([78,97,109,101,69,110]).decode(),'').strip()if lang.lower()==bytes([101,110]).decode()else A.get(bytes([78,97,109,101]).decode(),'').strip()
							if E:D[E]=A.get(bytes([86,97,108,117,101]).decode())
					return D
		return{}
	def _parse_nested_data(A,df,lang):"\n        Apply _flatten_content to the 'content' column, convert to DataFrame, and\n        concatenate with the original DataFrame (dropping 'content').\n\n        Args:\n            df (pd.DataFrame): DataFrame with a 'content' column.\n            lang (str): 'en' or 'vi'.\n\n        Returns:\n            pd.DataFrame: Merged DataFrame.\n        ";B=df[bytes([99,111,110,116,101,110,116]).decode()].apply(lambda content:A._flatten_content(content,lang));C=pd.DataFrame(B.tolist());D=pd.concat([df.drop(bytes([99,111,110,116,101,110,116]).decode(),axis=1,errors=bytes([105,103,110,111,114,101]).decode()),C],axis=1);return D
	def _clean_columns(E,df,period_type):
		'\n        Clean and reformat DataFrame columns by creating a \'period\' column based on period_type\n        and dropping unneeded columns.\n\n        For "year":\n          - Use \'year_period\' as \'period\'.\n          - Drop _id, id, term_code.\n        For "quarter":\n          - Create period as "year_period-term_code".\n          - Drop \'year_period\', _id, id, and term_code.\n\n        Args:\n            df (pd.DataFrame): DataFrame that may contain \'_id\', \'id\', \'term_code\', \'year_period\'.\n            period_type (str): "year" or "quarter".\n\n        Returns:\n            pd.DataFrame: Cleaned DataFrame.\n        ';B=period_type;A=df;B=B.lower()
		if B==bytes([121,101,97,114]).decode():A[bytes([112,101,114,105,111,100]).decode()]=A[bytes([121,101,97,114,95,112,101,114,105,111,100]).decode()]if bytes([121,101,97,114,95,112,101,114,105,111,100]).decode()in A.columns else None
		elif B==bytes([113,117,97,114,116,101,114]).decode():
			if bytes([121,101,97,114,95,112,101,114,105,111,100]).decode()in A.columns and bytes([116,101,114,109,95,99,111,100,101]).decode()in A.columns:A[bytes([112,101,114,105,111,100]).decode()]=A[bytes([121,101,97,114,95,112,101,114,105,111,100]).decode()].astype(str)+bytes([45]).decode()+A[bytes([116,101,114,109,95,99,111,100,101]).decode()].astype(str)
			else:A[bytes([112,101,114,105,111,100]).decode()]=None
			if bytes([121,101,97,114,95,112,101,114,105,111,100]).decode()in A.columns:A=A.drop(bytes([121,101,97,114,95,112,101,114,105,111,100]).decode(),axis=1,errors=bytes([105,103,110,111,114,101]).decode())
		else:raise ValueError(bytes([112,101,114,105,111,100,95,116,121,112,101,32,109,117,115,116,32,98,101,32,101,105,116,104,101,114,32,39,121,101,97,114,39,32,111,114,32,39,113,117,97,114,116,101,114,39]).decode())
		C=[bytes([95,105,100]).decode(),bytes([105,100]).decode(),bytes([116,101,114,109,95,99,111,100,101]).decode()];D=[B for B in C if B in A.columns];return A.drop(columns=D,errors=bytes([105,103,110,111,114,101]).decode())
	def _get_report(B,report_type,period,lang,dropna,show_log):
		"\n        A general method to query and process a financial report.\n\n        Args:\n            report_type (str): Report type such as 'balance_sheet', 'income_statement',\n                               'cash_flow', 'ratio', or 'annual_plan'.\n            period (str): Either 'year' or 'quarter'. If None, defaults to the instance period.\n            lang (str): 'en' or 'vi'.\n            dropna (bool): Whether to drop columns with all NaN values.\n            show_log (bool): Whether to show log details during the request.\n\n        Returns:\n            pd.DataFrame: Processed DataFrame with report data.\n        ";D=lang;C=period
		if D not in SUPPORTED_LANGUAGES:raise ValueError(bytes([78,103,195,180,110,32,110,103,225,187,175,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,58,32,39]).decode()+D+bytes([39,46,32,72,225,187,151,32,116,114,225,187,163,58,32]).decode()+bytes([44,32]).decode().join(SUPPORTED_LANGUAGES)+bytes([46]).decode())
		if C is None:F=B.raw_period;E=B.period
		elif C not in[bytes([121,101,97,114]).decode(),bytes([113,117,97,114,116,101,114]).decode()]:raise ValueError(bytes([75,225,187,179,32,98,195,161,111,32,99,195,161,111,32,116,195,160,105,32,99,104,195,173,110,104,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,104,225,186,165,112,32,110,104,225,186,173,110,32,39,121,101,97,114,39,32,104,111,225,186,183,99,32,39,113,117,97,114,116,101,114,39,46]).decode())
		else:F=C;E=_FINANCIAL_REPORT_PERIOD_MAP.get(C)
		G=B.base_url+bytes([102,105,110,97,110,99,105,97,108,82,101,112,111,114,116]).decode();H=B.query_params.replace(bytes([84,65,82,71,69,84,95,83,89,77,66,79,76]).decode(),B.symbol).replace(bytes([84,65,82,71,69,84,95,84,89,80,69]).decode(),_FINANCIAL_REPORT_MAP[report_type]).replace(bytes([84,65,82,71,69,84,95,80,69,82,73,79,68]).decode(),E);I={bytes([113,117,101,114,121]).decode():H};J=send_request(url=G,headers=B.headers,method=bytes([71,69,84]).decode(),params=I,payload=None,show_log=show_log);A=pd.DataFrame(J);A.columns=[camel_to_snake(A)for A in A.columns]
		if A.empty:logger.warning(bytes([78,111,32,100,97,116,97,32,102,111,117,110,100,32,102,111,114,32,115,121,109,98,111,108,32]).decode()+str(B.symbol)+bytes([32,105,110,32,112,101,114,105,111,100,32]).decode()+str(E)+bytes([46]).decode());return pd.DataFrame()
		A=B._parse_nested_data(A,D);A=B._clean_columns(A,period_type=F);A=reorder_cols(A,[bytes([112,101,114,105,111,100]).decode()],position=bytes([102,105,114,115,116]).decode())
		if dropna:A=A.dropna(axis=1,how=bytes([97,108,108]).decode())
		return A
	@agg_execution(bytes([77,65,83,46,101,120,116]).decode())
	def balance_sheet(self,period=None,lang=bytes([118,105]).decode(),dropna=True,show_log=False):'\n        Trích xuất dữ liệu bảng cân đối kế toán từ nguồn MAS.\n        ';return self._get_report(bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode(),period,lang,dropna,show_log)
	@agg_execution(bytes([77,65,83,46,101,120,116]).decode())
	def income_statement(self,period=None,lang=bytes([118,105]).decode(),dropna=True,show_log=False):'\n        Trích xuất dữ liệu báo cáo kết quả kinh doanh từ nguồn MAS.\n        ';return self._get_report(bytes([105,110,99,111,109,101,95,115,116,97,116,101,109,101,110,116]).decode(),period,lang,dropna,show_log)
	@agg_execution(bytes([77,65,83,46,101,120,116]).decode())
	def cash_flow(self,period=None,lang=bytes([118,105]).decode(),dropna=True,show_log=False):'\n        Trích xuất dữ liệu báo cáo lưu chuyển tiền tệ từ nguồn MAS.\n        ';return self._get_report(bytes([99,97,115,104,95,102,108,111,119]).decode(),period,lang,dropna,show_log)
	@agg_execution(bytes([77,65,83,46,101,120,116]).decode())
	def ratio(self,period=None,lang=bytes([118,105]).decode(),dropna=True,show_log=False):'\n        Trích xuất dữ liệu báo cáo tỉ lệ tài chính từ nguồn MAS.\n        ';return self._get_report(bytes([114,97,116,105,111]).decode(),period,lang,dropna,show_log)
	@agg_execution(bytes([77,65,83,46,101,120,116]).decode())
	def annual_plan(self,period=bytes([121,101,97,114]).decode(),lang=bytes([118,105]).decode(),dropna=True,show_log=False):
		'\n        Trích xuất dữ liệu báo cáo dự kiến từ nguồn MAS.\n        ';B=period
		if B not in[bytes([121,101,97,114]).decode()]:raise ValueError(bytes([66,195,161,111,32,99,195,161,111,32,99,104,225,187,137,32,116,105,195,170,117,32,107,225,186,191,32,104,111,225,186,161,99,104,32,99,104,225,187,137,32,99,104,225,186,165,112,32,110,104,225,186,173,110,32,103,105,195,161,32,116,114,225,187,139,32,121,101,97,114,46]).decode())
		A=self._get_report(bytes([97,110,110,117,97,108,95,112,108,97,110]).decode(),B,lang,dropna,show_log)
		if bytes([121,101,97,114,95,112,101,114,105,111,100]).decode()in A.columns:A=A.drop(bytes([121,101,97,114,95,112,101,114,105,111,100]).decode(),axis=1,errors=bytes([105,103,110,111,114,101]).decode())
		return A
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([102,105,110,97,110,99,105,97,108]).decode(),bytes([109,97,115]).decode(),Finance)