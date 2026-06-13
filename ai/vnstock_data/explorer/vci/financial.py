'\nModule quản lý thông tin báo cáo tài chính từ nguồn dữ liệu VCI.\n'
import json,pandas as pd
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake,get_asset_type
from vnstock.core.utils.transform import reorder_cols
from vnstock.explorer.vci.const import _GRAPHQL_URL,_UNIT_MAP,SUPPORTED_LANGUAGES
from vnstock_data.core.utils.client import ProxyConfig,send_request
from vnstock_data.core.utils.parser import vn_to_snake_case
from vnstock_data.core.utils.transform import generate_period,remove_pattern_columns
from vnstock_data.core.utils.user_agent import get_headers
from.const import _IQ_FINANCE_REPORT,_VCIQ_URL
logger=get_logger(__name__)
class Finance:
	"\n    Truy xuất thông tin báo cáo tài chính của một công ty theo mã chứng khoán từ nguồn dữ liệu VCI.\n\n    Tham số:\n        - symbol (str): Mã chứng khoán của công ty cần truy xuất thông tin.\n        - period (str): Chu kỳ báo cáo tài chính cần truy xuất. Mặc định là 'quarter'.\n        - get_all (bool): Trả về tất cả các trường dữ liệu hoặc chỉ các trường chọn lọc. Mặc định là True.\n        - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là True.\n    "
	def __init__(A,symbol,period=None,get_all=True,proxy_config=None,show_log=False):
		'\n        Khởi tạo đối tượng Finance với các tham số cho việc truy xuất dữ liệu báo cáo tài chính.\n        ';D=show_log;C=proxy_config;B=period;A.symbol=symbol.upper();A.asset_type=get_asset_type(A.symbol);A.headers=get_headers(data_source=bytes([86,67,73]).decode());A.base_url=_VCIQ_URL;A.show_log=D;A.proxy_config=C if C is not None else ProxyConfig()
		if not D:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
		if B not in[bytes([121,101,97,114]).decode(),bytes([113,117,97,114,116,101,114]).decode()]and B!=None:raise ValueError(bytes([75,225,187,179,32,98,195,161,111,32,99,195,161,111,32,116,195,160,105,32,99,104,195,173,110,104,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,104,225,186,165,112,32,110,104,225,186,173,110,32,39,121,101,97,114,39,32,104,111,225,186,183,99,32,39,113,117,97,114,116,101,114,39,32,104,111,225,186,183,99,32,78,111,110,101,46]).decode())
		if A.asset_type not in[bytes([115,116,111,99,107]).decode()]:raise ValueError(bytes([77,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,225,187,149,32,112,104,105,225,186,191,117,32,109,225,187,155,105,32,99,195,179,32,116,104,195,180,110,103,32,116,105,110,46]).decode())
		A.period=B;A.get_all=get_all
	@staticmethod
	def duplicated_columns_handling(df_or_mapping,target_col_name=None):
		"\n        Handle duplicated column names in a DataFrame or column mapping DataFrame.\n        \n        Parameters:\n            - df_or_mapping (pd.DataFrame): Either a DataFrame with potentially duplicated columns\n            or a mapping DataFrame with columns that may have duplicated values.\n            - target_col_name (str, optional): When handling a mapping DataFrame, this is the column\n            to check for duplicates. When None, assumes we're handling DataFrame columns directly.\n        \n        Returns:\n            pd.DataFrame: DataFrame with resolved column duplications.\n        ";C=target_col_name;A=df_or_mapping
		if C is not None:H=A[A[C].duplicated()].copy();J=A[~A[C].duplicated()].copy();H[C]=A[bytes([110,97,109,101]).decode()]+bytes([32,45,32]).decode()+A[bytes([102,105,101,108,100,95,110,97,109,101]).decode()];return pd.concat([J,H])
		else:
			B=A.copy();K=B.columns.duplicated(keep=False);I=B.columns[K].unique()
			if len(I)>0:
				D=B.columns.tolist()
				for F in I:
					L=[A for(A,B)in enumerate(D)if B==F]
					for(E,M)in enumerate(L):
						if E==0:continue
						G=bytes([95]).decode()*E+F
						while G in D:E+=1;G=bytes([95]).decode()*E+F
						D[M]=G
				B.columns=D
			return B
	def _get_ratio_dict(B,lang=bytes([118,105]).decode(),format=bytes([100,105,99,116]).decode(),style=bytes([114,101,97,100,97,98,108,101]).decode(),show_log=False):
		"\n        Lấy từ điển ánh xạ cho tất cả các chỉ số tài chính từ nguồn VCI.\n\n        Tham số:\n            - lang (str): Ngôn ngữ của báo cáo. Mặc định là 'en'.\n            - format (str): Định dạng trả về. Mặc định là 'dict', lựa chọn khác có thể là 'dataframe'.\n            - style (str): Định dạng trả về. Mặc định là 'readable', lựa chọn khác có thể là 'code'.\n            - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là False.\n            \n        Returns:\n            pd.DataFrame: DataFrame chứa ánh xạ giữa 'field_name', 'name', 'en_name', 'type', 'order', 'unit'.\n        ";E=show_log;D=style;C=lang
		if C not in SUPPORTED_LANGUAGES:raise ValueError(bytes([78,103,195,180,110,32,110,103,225,187,175,32,39]).decode()+C+bytes([39,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,104,225,186,165,112,32,110,104,225,186,173,110,32]).decode()+bytes([44,32]).decode().join(SUPPORTED_LANGUAGES)+bytes([46]).decode())
		if format not in[bytes([100,105,99,116]).decode(),bytes([100,97,116,97,102,114,97,109,101]).decode()]:raise ValueError(bytes([196,144,225,187,139,110,104,32,100,225,186,161,110,103,32,39]).decode()+str(format)+bytes([39,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,104,225,186,165,112,32,110,104,225,186,173,110,32,39,100,105,99,116,39,32,104,111,225,186,183,99,32,39,100,97,116,97,102,114,97,109,101,39,46]).decode())
		F=f"{B.base_url}/v1/company/{B.symbol}/financial-statement/metrics"
		if E:logger.debug(f"Requesting financial ratio data from {F}")
		J=send_request(url=F,headers=B.headers,method=bytes([71,69,84]).decode(),payload=None,show_log=E,proxy_list=B.proxy_config.proxy_list,proxy_mode=B.proxy_config.proxy_mode,request_mode=B.proxy_config.request_mode);G=J[bytes([100,97,116,97]).decode()];H=[]
		for I in G.keys():A=pd.DataFrame(G[I]);A[bytes([114,101,112,111,114,116,95,110,97,109,101]).decode()]=I;A=A[[bytes([114,101,112,111,114,116,95,110,97,109,101]).decode(),bytes([102,105,101,108,100]).decode(),bytes([112,97,114,101,110,116]).decode(),bytes([116,105,116,108,101,69,110]).decode(),bytes([116,105,116,108,101,86,105]).decode(),bytes([102,117,108,108,84,105,116,108,101,86,105]).decode(),bytes([102,117,108,108,84,105,116,108,101,69,110]).decode()]];H.append(A)
		A=pd.concat(H);A=A.rename(columns={bytes([102,105,101,108,100]).decode():bytes([102,105,101,108,100,95,110,97,109,101]).decode(),bytes([116,105,116,108,101,86,105]).decode():bytes([110,97,109,101]).decode(),bytes([116,105,116,108,101,69,110]).decode():bytes([101,110,95,110,97,109,101]).decode(),bytes([102,117,108,108,84,105,116,108,101,86,105]).decode():bytes([102,117,108,108,95,110,97,109,101]).decode(),bytes([102,117,108,108,84,105,116,108,101,69,110]).decode():bytes([101,110,95,102,117,108,108,95,110,97,109,101]).decode()})
		if format==bytes([100,105,99,116]).decode():
			if C==bytes([118,105]).decode():
				if D==bytes([114,101,97,100,97,98,108,101]).decode():return A.set_index(bytes([102,105,101,108,100,95,110,97,109,101]).decode())[bytes([110,97,109,101]).decode()].to_dict()
				elif D==bytes([99,111,100,101]).decode():return{vn_to_snake_case(str(A).lower()):vn_to_snake_case(str(B).lower())for(A,B)in A.set_index(bytes([102,105,101,108,100,95,110,97,109,101]).decode())[bytes([110,97,109,101]).decode()].to_dict().items()if pd.notna(A)and pd.notna(B)}
			elif C==bytes([101,110]).decode():
				if D==bytes([99,111,100,101]).decode():return{str(A).lower():str(B).lower().replace(bytes([32]).decode(),bytes([95]).decode())for(A,B)in A.set_index(bytes([102,105,101,108,100,95,110,97,109,101]).decode())[bytes([101,110,95,110,97,109,101]).decode()].to_dict().items()if pd.notna(A)and pd.notna(B)}
				elif D==bytes([114,101,97,100,97,98,108,101]).decode():return{A:B for(A,B)in A.set_index(bytes([102,105,101,108,100,95,110,97,109,101]).decode())[bytes([101,110,95,102,117,108,108,95,110,97,109,101]).decode()].to_dict().items()if pd.notna(A)and pd.notna(B)}
		else:return A
	def _get_old_ratio_dict(B,show_log=False,get_all=False):
		"\n        Lấy từ điển ánh xạ cho tất cả các chỉ số tài chính từ nguồn VCI.\n\n        Tham số:\n            - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là False.\n            - get_all (bool): Lấy tất cả cột hoặc không. Mặc định là False.\n            \n        Returns:\n            pd.DataFrame: DataFrame chứa ánh xạ giữa 'field_name', 'name', 'en_name', 'type', 'order', 'unit'.\n        ";D=get_all;C=show_log;E=bytes([123,34,113,117,101,114,121,34,58,34,113,117,101,114,121,32,81,117,101,114,121,32,123,92,110,32,32,76,105,115,116,70,105,110,97,110,99,105,97,108,82,97,116,105,111,32,123,92,110,32,32,32,32,105,100,92,110,32,32,32,32,116,121,112,101,92,110,32,32,32,32,110,97,109,101,92,110,32,32,32,32,117,110,105,116,92,110,32,32,32,32,105,115,68,101,102,97,117,108,116,92,110,32,32,32,32,102,105,101,108,100,78,97,109,101,92,110,32,32,32,32,101,110,95,84,121,112,101,92,110,32,32,32,32,101,110,95,78,97,109,101,92,110,32,32,32,32,116,97,103,78,97,109,101,92,110,32,32,32,32,99,111,109,84,121,112,101,67,111,100,101,92,110,32,32,32,32,111,114,100,101,114,92,110,32,32,32,32,95,95,116,121,112,101,110,97,109,101,92,110,32,32,125,92,110,125,92,110,34,44,34,118,97,114,105,97,98,108,101,115,34,58,123,125,125]).decode();F=json.loads(E)
		if C:logger.debug(f"Requesting financial ratio data from {_GRAPHQL_URL}. payload: {E}")
		G=send_request(url=_GRAPHQL_URL,headers=B.headers,method=bytes([80,79,83,84]).decode(),payload=F,show_log=C,proxy_list=B.proxy_config.proxy_list,proxy_mode=B.proxy_config.proxy_mode,request_mode=B.proxy_config.request_mode);H=G[bytes([100,97,116,97]).decode()][bytes([76,105,115,116,70,105,110,97,110,99,105,97,108,82,97,116,105,111]).decode()];A=pd.DataFrame(H);A.columns=[camel_to_snake(A).replace(bytes([95,95]).decode(),bytes([95]).decode())for A in A.columns];I=D if D is not None else B.get_all;J=[bytes([102,105,101,108,100,95,110,97,109,101]).decode(),bytes([110,97,109,101]).decode(),bytes([101,110,95,110,97,109,101]).decode(),bytes([116,121,112,101]).decode(),bytes([111,114,100,101,114]).decode(),bytes([117,110,105,116]).decode(),bytes([99,111,109,95,116,121,112,101,95,99,111,100,101]).decode()];A[bytes([117,110,105,116]).decode()]=A[bytes([117,110,105,116]).decode()].map(_UNIT_MAP)
		if I is False:A=A[J]
		A.columns=[A.replace(bytes([95,95]).decode(),bytes([95]).decode())for A in A.columns];return A
	def _get_report(D,report_type=None,lang=bytes([101,110]).decode(),show_log=False,mode=bytes([102,105,110,97,108]).decode(),style=bytes([114,101,97,100,97,98,108,101]).decode(),get_all=False):
		"\n        Lấy dữ liệu báo cáo tài chính cho một công ty từ nguồn VCI.\n        \n        Tham số:\n            - report_type (str): Loại báo cáo tài chính bao gồm 'income_statement', 'balance_sheet', 'cash_flow' và 'note'\n            - lang (str): Ngôn ngữ của báo cáo. Mặc định là 'en'.\n            - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là False.\n            - mode (str): Chế độ báo cáo. Mặc định là 'final' trả về dữ liệu đã xử lý sau quá trình ánh xạ. \n              Chế độ khác là 'raw' trả về dữ liệu thô chứa tên mã cho tất cả các trường.\n            - style (str): Chế độ tên cột. Mặc định là 'readable' trả về tên cột dễ đọc. \n              Chế độ khác là 'code' trả về tên cột mã hóa.\n            - get_all (bool): Trả về tất cả các trường dữ liệu hoặc chỉ các trường chọn lọc. Mặc định là False.\n              \n        Returns:\n            Union[Tuple[Dict[str, pd.DataFrame], pd.DataFrame], pd.DataFrame]: \n                Nếu mode='final': Trả về tuple gồm dictionary các báo cáo chính và DataFrame cho các báo cáo khác\n                Nếu mode='raw': Trả về DataFrame dữ liệu thô\n        ";I=mode;H=lang;E=report_type;C=show_log
		if H not in SUPPORTED_LANGUAGES:O=bytes([44,32]).decode().join(SUPPORTED_LANGUAGES);raise ValueError(f"Ngôn ngữ không hợp lệ: '{H}'. Các ngôn ngữ được hỗ trợ: {O}.")
		if E not in _IQ_FINANCE_REPORT.keys():raise ValueError(bytes([76,111,225,186,161,105,32,98,195,161,111,32,99,195,161,111,32,116,195,160,105,32,99,104,195,173,110,104,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,58,32,39]).decode()+str(E)+bytes([39,46,32,67,195,161,99,32,108,111,225,186,161,105,32,98,195,161,111,32,99,195,161,111,32,116,195,160,105,32,99,104,195,173,110,104,32,196,145,198,176,225,187,163,99,32,104,225,187,151,32,116,114,225,187,163,58,32]).decode()+bytes([44,32]).decode().join(_IQ_FINANCE_REPORT.keys())+bytes([46]).decode())
		else:E=_IQ_FINANCE_REPORT[E]
		if E==bytes([82,65,84,73,79]).decode():J={};K=f"https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/{D.symbol}/statistics-financial"
		else:K=f"https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/{D.symbol}/financial-statement";J={bytes([115,101,99,116,105,111,110]).decode():E}
		if C:logger.debug(f"Requesting financial report data from {K}. payload: {J}")
		G=send_request(url=K,headers=D.headers,method=bytes([71,69,84]).decode(),params=J,payload=None,show_log=C,proxy_list=D.proxy_config.proxy_list,proxy_mode=D.proxy_config.proxy_mode,request_mode=D.proxy_config.request_mode)
		try:
			if G is None or bytes([100,97,116,97]).decode()not in G or G[bytes([100,97,116,97]).decode()]is None:
				A=bytes([78,111,32,100,97,116,97,32,114,101,99,101,105,118,101,100,32,102,114,111,109,32,116,104,101,32,65,80,73]).decode()
				if C:logger.error(f"{A}. Response: {G}")
				raise ValueError(A)
			B=G[bytes([100,97,116,97]).decode()]
			if E==bytes([82,65,84,73,79]).decode():
				if not isinstance(B,list):
					A=f"Unexpected data format for ratio. Expected list, got {type(B).__name__}"
					if C:logger.error(f"{A}. Data: {B}")
					raise ValueError(A)
				F=pd.DataFrame(B)
				if F.empty:
					A=bytes([78,111,32,118,97,108,105,100,32,114,97,116,105,111,32,100,97,116,97,32,102,111,117,110,100,32,105,110,32,116,104,101,32,114,101,115,112,111,110,115,101]).decode()
					if C:logger.error(f"{A}. Data: {B}")
					raise ValueError(A)
				L=F
			else:
				if not isinstance(B,dict):
					A=f"Unexpected data format. Expected dict, got {type(B).__name__}"
					if C:logger.error(f"{A}. Data: {B}")
					raise ValueError(A)
				M=[]
				for(P,N)in B.items():
					if N:
						F=pd.DataFrame(N)
						if not F.empty:F[bytes([114,101,112,111,114,116,95,112,101,114,105,111,100]).decode()]=P[:-1];M.append(F)
				if not M:
					A=bytes([78,111,32,118,97,108,105,100,32,100,97,116,97,32,102,111,117,110,100,32,105,110,32,116,104,101,32,114,101,115,112,111,110,115,101]).decode()
					if C:logger.error(f"{A}. Data: {B}")
					raise ValueError(A)
				L=pd.concat(M,ignore_index=True)
			if I==bytes([102,105,110,97,108]).decode():Q=D._ratio_mapping(report_df=L,lang=H,style=style,get_all=get_all,show_log=C);return Q
			elif I==bytes([114,97,119]).decode():return L
			else:A=f"Invalid mode: {I}. Must be 'final' or 'raw'.";logger.error(A);raise ValueError(A)
		except Exception as R:logger.error(f"Error processing financial report data: {R}",exc_info=True);raise
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def _ratio_mapping(self,report_df,lang=bytes([118,105]).decode(),style=bytes([114,101,97,100,97,98,108,101]).decode(),get_all=False,show_log=False):
		"\n        A dedicated method to map the financial ratio DataFrame columns to the dictionary ratio_dict.\n\n        Parameters:\n            - report_df (pd.DataFrame): The DataFrame containing the financial ratio from the function _get_report().\n            - lang (str): The language of the report. Default is 'vi'.\n            - style (str): The style of the report. Default is 'readable'.\n            - get_all (bool): Whether to get all raw columns or just essential columns. Default is False for removing optional columns.\n            - show_log (bool): Whether to show log messages. Default is False.\n\n        Returns:\n            - pd.DataFrame: A DataFrame containing the financial ratio data.\n        ";D=style;C=lang;A=report_df
		if C not in SUPPORTED_LANGUAGES:G=bytes([44,32]).decode().join(SUPPORTED_LANGUAGES);raise ValueError(bytes([78,103,195,180,110,32,110,103,225,187,175,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,58,32,39]).decode()+str(C)+bytes([39,46,32,67,195,161,99,32,110,103,195,180,110,32,110,103,225,187,175,32,196,145,198,176,225,187,163,99,32,104,225,187,151,32,116,114,225,187,163,58,32]).decode()+G+bytes([46]).decode())
		if D not in[bytes([114,101,97,100,97,98,108,101]).decode(),bytes([99,111,100,101]).decode()]:raise ValueError(bytes([67,104,225,186,191,32,196,145,225,187,153,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,58,32,39]).decode()+str(D)+bytes([39,46,32,67,104,225,186,191,32,196,145,225,187,153,32,196,145,198,176,225,187,163,99,32,104,225,187,151,32,116,114,225,187,163,58,32,39,114,101,97,100,97,98,108,101,39,32,99,104,111,32,116,195,170,110,32,104,105,225,187,131,110,32,116,104,225,187,139,32,104,111,225,186,183,99,32,39,99,111,100,101,39,32,99,104,111,32,116,195,170,110,32,109,195,163,46]).decode())
		F=self._get_ratio_dict(lang=C,style=D,format=bytes([100,105,99,116]).decode());A.columns=[F[A]if A in F else A for A in A.columns]
		if bytes([108,101,110,103,116,104,82,101,112,111,114,116]).decode()not in A.columns and bytes([113,117,97,114,116,101,114]).decode()in A.columns:A[bytes([108,101,110,103,116,104,82,101,112,111,114,116]).decode()]=A[bytes([113,117,97,114,116,101,114]).decode()]
		if bytes([121,101,97,114,82,101,112,111,114,116]).decode()not in A.columns and bytes([121,101,97,114]).decode()in A.columns:A[bytes([121,101,97,114,82,101,112,111,114,116]).decode()]=A[bytes([121,101,97,114]).decode()]
		if bytes([114,101,112,111,114,116,95,112,101,114,105,111,100]).decode()not in A.columns:
			if bytes([113,117,97,114,116,101,114]).decode()in A.columns:A[bytes([114,101,112,111,114,116,95,112,101,114,105,111,100]).decode()]=A[bytes([113,117,97,114,116,101,114]).decode()].apply(lambda x:bytes([121,101,97,114]).decode()if x==5 else bytes([113,117,97,114,116,101,114]).decode())
			else:A[bytes([114,101,112,111,114,116,95,112,101,114,105,111,100]).decode()]=bytes([121,101,97,114]).decode()
		if bytes([113,117,97,114,116,101,114]).decode()in A.columns and bytes([108,101,110,103,116,104,82,101,112,111,114,116]).decode()in A.columns:H=A[bytes([113,117,97,114,116,101,114]).decode()]==5;A.loc[H,bytes([108,101,110,103,116,104,82,101,112,111,114,116]).decode()]=4
		A=generate_period(A);A=reorder_cols(A,cols=[bytes([112,101,114,105,111,100]).decode(),bytes([114,101,112,111,114,116,95,112,101,114,105,111,100]).decode(),bytes([111,114,103,97,110,67,111,100,101]).decode(),bytes([116,105,99,107,101,114]).decode(),bytes([99,114,101,97,116,101,68,97,116,101]).decode(),bytes([117,112,100,97,116,101,68,97,116,101]).decode(),bytes([121,101,97,114,82,101,112,111,114,116]).decode(),bytes([108,101,110,103,116,104,82,101,112,111,114,116]).decode(),bytes([112,117,98,108,105,99,68,97,116,101]).decode()],position=bytes([102,105,114,115,116]).decode())
		if C==bytes([101,110]).decode():A=A.set_index(bytes([112,101,114,105,111,100]).decode())
		elif C==bytes([118,105]).decode():
			if D==bytes([114,101,97,100,97,98,108,101]).decode():A=A.rename(columns={bytes([112,101,114,105,111,100]).decode():bytes([75,225,187,179,32,98,195,161,111,32,99,195,161,111]).decode(),bytes([116,105,99,107,101,114]).decode():bytes([77,195,163,32,67,80]).decode()});A=A.set_index(bytes([75,225,187,179,32,98,195,161,111,32,99,195,161,111]).decode())
			elif D==bytes([99,111,100,101]).decode():A=A.rename(columns={bytes([112,101,114,105,111,100]).decode():bytes([107,121,95,98,97,111,95,99,97,111]).decode(),bytes([116,105,99,107,101,114]).decode():bytes([99,112]).decode()});A=A.set_index(bytes([107,121,95,98,97,111,95,99,97,111]).decode())
		if get_all==False:
			I=[bytes([111,114,103,97,110,67,111,100,101]).decode(),bytes([99,114,101,97,116,101,68,97,116,101]).decode(),bytes([117,112,100,97,116,101,68,97,116,101]).decode(),bytes([121,101,97,114,82,101,112,111,114,116]).decode(),bytes([108,101,110,103,116,104,82,101,112,111,114,116]).decode(),bytes([112,117,98,108,105,99,68,97,116,101]).decode()];B=[B for B in I if B in A.columns]
			if B:A=A.drop(columns=B)
			try:
				A=remove_pattern_columns(A,[bytes([98,115,97]).decode(),bytes([98,115,98]).decode(),bytes([98,115,105]).decode(),bytes([98,115,115]).decode(),bytes([110,111,98]).decode(),bytes([110,111,115]).decode(),bytes([99,102,97]).decode(),bytes([99,102,115]).decode(),bytes([99,102,105]).decode(),bytes([105,115,97]).decode(),bytes([105,115,98]).decode(),bytes([105,115,105]).decode(),bytes([105,115,115]).decode()]);import re;J=re.compile(bytes([94,91,97,45,122,93,123,50,44,51,125,92,100,43,36]).decode(),re.IGNORECASE);B=[]
				for E in A.columns:
					if J.match(str(E)):
						if A[E].isna().all()or True:B.append(E)
				if B:A=A.drop(columns=B)
			except Exception as K:logger.error(f"Error removing pattern columns: {K}");raise
			finally:return A
		else:return A
	def _get_financial_report(C,report_type,period=None,lang=bytes([101,110]).decode(),mode=bytes([102,105,110,97,108]).decode(),style=bytes([114,101,97,100,97,98,108,101]).decode(),get_all=False,dropna=True,show_log=False):
		'\n        Internal method to retrieve and filter financial reports by type and period.\n        ';F=lang;E=period;B=report_type
		if F not in SUPPORTED_LANGUAGES:raise ValueError(bytes([78,103,195,180,110,32,110,103,225,187,175,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,58,32,39]).decode()+str(F)+bytes([39,46,32,67,195,161,99,32,110,103,195,180,110,32,110,103,225,187,175,32,196,145,198,176,225,187,163,99,32,104,225,187,151,32,116,114,225,187,163,58,32]).decode()+bytes([44,32]).decode().join(SUPPORTED_LANGUAGES)+bytes([46]).decode())
		if B not in[bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode(),bytes([105,110,99,111,109,101,95,115,116,97,116,101,109,101,110,116]).decode(),bytes([99,97,115,104,95,102,108,111,119]).decode(),bytes([110,111,116,101]).decode(),bytes([114,97,116,105,111]).decode()]:raise ValueError(bytes([76,111,225,186,161,105,32,98,195,161,111,32,99,195,161,111,32,116,195,160,105,32,99,104,195,173,110,104,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,58,32,39]).decode()+str(B)+bytes([39,46,32,67,195,161,99,32,108,111,225,186,161,105,32,98,195,161,111,32,99,195,161,111,32,116,195,160,105,32,99,104,195,173,110,104,32,196,145,198,176,225,187,163,99,32,104,225,187,151,32,116,114,225,187,163,58,32,39,98,97,108,97,110,99,101,95,115,104,101,101,116,39,44,32,39,105,110,99,111,109,101,95,115,116,97,116,101,109,101,110,116,39,44,32,39,99,97,115,104,95,102,108,111,119,39,44,32,39,110,111,116,101,39,46]).decode())
		A=C._get_report(report_type=B,lang=F,mode=mode,style=style,get_all=get_all,show_log=show_log)
		if E is None or E not in[bytes([121,101,97,114]).decode(),bytes([113,117,97,114,116,101,114]).decode()]:
			if B==bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode():A=C.duplicated_columns_handling(A)
			return A
		G=E
		if bytes([114,101,112,111,114,116,95,112,101,114,105,111,100]).decode()in A.columns:
			H=A[bytes([114,101,112,111,114,116,95,112,101,114,105,111,100]).decode()].astype(str).str.contains(G,case=False,regex=False);D=A[H].copy()
			if D.empty:logger.warning(f"Không tìm thấy kỳ báo cáo {G} trong cột report_period.")
			if B==bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode():D=C.duplicated_columns_handling(D)
			return D
		else:
			logger.error(bytes([75,104,195,180,110,103,32,116,104,225,187,131,32,108,225,187,141,99,32,116,104,101,111,32,107,225,187,179,32,98,195,161,111,32,99,195,161,111,58,32,75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,99,225,187,153,116,32,114,101,112,111,114,116,95,112,101,114,105,111,100,46]).decode())
			if B==bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode():A=C.duplicated_columns_handling(A)
			return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def balance_sheet(self,period=None,lang=bytes([101,110]).decode(),mode=bytes([102,105,110,97,108]).decode(),style=bytes([114,101,97,100,97,98,108,101]).decode(),get_all=False,dropna=True,show_log=False):
		"\n        Trích xuất dữ liệu bảng cân đối kế toán cho một công ty từ nguồn VCI.\n\n        Tham số:\n            - period (str): Kỳ báo cáo tài chính. Mặc định là None.\n            - lang (str): Ngôn ngữ của báo cáo. Mặc định là 'en'.\n            - mode (str): Chế độ trả về dữ liệu. Mặc định là 'final' cho dữ liệu đã qua xử lý tên, nếu mode='raw' thì trả về DataFrame dữ liệu thô cho lưu trữ cơ sở dữ liệu.\n            - style (str): Chế độ hiển thị tên cột. Mặc định là 'readable' cho tên hiển thị, hoặc 'code' cho tên mã dạng snake_case không dấu.\n            - get_all (bool): Có lấy tất cả các cột hay không. Mặc định là False để lấy các cột quan trọng.\n            - dropna (bool): Có loại bỏ các cột với tất cả giá trị 0 hay không. Mặc định là False.\n            - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là False.\n            \n        Returns:\n            pd.DataFrame: DataFrame chứa dữ liệu bảng cân đối kế toán.\n        ";A=self._get_financial_report(report_type=bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode(),period=period,lang=lang,mode=mode,style=style,get_all=get_all,dropna=dropna,show_log=show_log)
		if bytes([121,101,97,114,95,112,101,114,105,111,100]).decode()in A.columns:A=A.drop(columns=bytes([121,101,97,114,95,112,101,114,105,111,100]).decode())
		return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def income_statement(self,period=None,lang=bytes([101,110]).decode(),mode=bytes([102,105,110,97,108]).decode(),style=bytes([114,101,97,100,97,98,108,101]).decode(),get_all=False,dropna=True,show_log=False):"\n        Trích xuất dữ liệu báo cáo kết quả kinh doanh cho một công ty từ nguồn VCI.\n\n        Tham số:\n            - period (str): Kỳ báo cáo tài chính. Mặc định là None.\n            - lang (str): Ngôn ngữ của báo cáo. Mặc định là 'en'.\n            - mode (str): Chế độ trả về dữ liệu. Mặc định là 'final' cho dữ liệu đã qua xử lý tên, nếu mode='raw' thì trả về DataFrame dữ liệu thô cho lưu trữ cơ sở dữ liệu.\n            - style (str): Chế độ hiển thị tên cột. Mặc định là 'readable' cho tên hiển thị, hoặc 'code' cho tên mã dạng snake_case không dấu.\n            - get_all (bool): Có lấy tất cả các cột hay không. Mặc định là False để lấy các cột quan trọng.\n            - dropna (bool): Có loại bỏ các cột với tất cả giá trị 0 hay không. Mặc định là False.\n            - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là False.\n            \n        Returns:\n            pd.DataFrame: DataFrame chứa dữ liệu báo cáo kết quả kinh doanh.\n        ";return self._get_financial_report(report_type=bytes([105,110,99,111,109,101,95,115,116,97,116,101,109,101,110,116]).decode(),period=period,lang=lang,mode=mode,style=style,get_all=get_all,dropna=dropna,show_log=show_log)
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def cash_flow(self,period=None,lang=bytes([101,110]).decode(),mode=bytes([102,105,110,97,108]).decode(),style=bytes([114,101,97,100,97,98,108,101]).decode(),get_all=False,dropna=True,show_log=False):"\n        Trích xuất dữ liệu báo cáo lưu chuyển tiền tệ của công ty từ nguồn VCI.\n\n        Tham số:\n            - period (str): Kỳ báo cáo tài chính. Mặc định là None.\n            - lang (str): Ngôn ngữ của báo cáo. Mặc định là 'en'.\n            - mode (str): Chế độ trả về dữ liệu. Mặc định là 'final' cho dữ liệu đã qua xử lý tên, nếu mode='raw' thì trả về DataFrame dữ liệu thô cho lưu trữ cơ sở dữ liệu.\n            - style (str): Chế độ hiển thị tên cột. Mặc định là 'readable' cho tên hiển thị, hoặc 'code' cho tên mã dạng snake_case không dấu.\n            - get_all (bool): Có lấy tất cả các cột hay không. Mặc định là False để lấy các cột quan trọng.\n            - dropna (bool): Có loại bỏ các cột với tất cả giá trị 0 hay không. Mặc định là False.\n            - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là False.\n            \n        Returns:\n            pd.DataFrame: DataFrame chứa dữ liệu báo cáo lưu chuyển tiền tệ.\n        ";return self._get_financial_report(report_type=bytes([99,97,115,104,95,102,108,111,119]).decode(),period=period,lang=lang,mode=mode,style=style,get_all=get_all,dropna=dropna,show_log=show_log)
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def note(self,period=None,lang=bytes([101,110]).decode(),mode=bytes([102,105,110,97,108]).decode(),style=bytes([114,101,97,100,97,98,108,101]).decode(),get_all=False,dropna=True,show_log=False):"\n        Trích xuất dữ liệu thuyến minh báo cáo tài chính công ty từ nguồn VCI.\n\n        Tham số:\n            - period (str): Kỳ báo cáo tài chính. Mặc định là None.\n            - lang (str): Ngôn ngữ của báo cáo. Mặc định là 'en'.\n            - mode (str): Chế độ trả về dữ liệu. Mặc định là 'final' cho dữ liệu đã qua xử lý tên, nếu mode='raw' thì trả về DataFrame dữ liệu thô cho lưu trữ cơ sở dữ liệu.\n            - style (str): Chế độ hiển thị tên cột. Mặc định là 'readable' cho tên hiển thị, hoặc 'code' cho tên mã dạng snake_case không dấu.\n            - get_all (bool): Có lấy tất cả các cột hay không. Mặc định là False để lấy các cột quan trọng.\n            - dropna (bool): Có loại bỏ các cột với tất cả giá trị 0 hay không. Mặc định là False.\n            - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là False.\n            \n        Returns:\n            pd.DataFrame: DataFrame chứa dữ liệu thuyên minh báo cáo tài chính.\n        ";return self._get_financial_report(report_type=bytes([110,111,116,101]).decode(),period=period,lang=lang,mode=mode,style=style,get_all=get_all,dropna=dropna,show_log=show_log)
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def ratio(self,period=None,lang=bytes([101,110]).decode(),mode=bytes([102,105,110,97,108]).decode(),style=bytes([114,101,97,100,97,98,108,101]).decode(),get_all=False,dropna=True,show_log=False):
		"\n        Trích xuất dữ liệu báo cáo tỷ lệ tài chính của công ty từ nguồn VCI.\n\n        Tham số:\n            - period (str): Kỳ báo cáo tài chính. Mặc định là None.\n            - lang (str): Ngôn ngữ của báo cáo. Mặc định là 'en'.\n            - mode (str): Chế độ trả về dữ liệu. Mặc định là 'final' cho dữ liệu đã qua xử lý tên, nếu mode='raw' thì trả về DataFrame dữ liệu thô cho lưu trữ cơ sở dữ liệu.\n            - style (str): Chế độ hiển thị tên cột. Mặc định là 'readable' cho tên hiển thị, hoặc 'code' cho tên mã dạng snake_case không dấu.\n            - get_all (bool): Có lấy tất cả các cột hay không. Mặc định là False để lấy các cột quan trọng.\n            - dropna (bool): Có loại bỏ các cột với tất cả giá trị 0 hay không. Mặc định là False.\n            - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là False.\n            \n        Returns:\n            pd.DataFrame: DataFrame chứa dữ liệu báo cáo tỷ lệ tài chính.\n        ";B=style;A=self._get_financial_report(report_type=bytes([114,97,116,105,111]).decode(),period=period,lang=lang,mode=mode,style=bytes([99,111,100,101]).decode(),get_all=get_all,dropna=dropna,show_log=show_log)
		if B==bytes([99,111,100,101]).decode():from vnstock_data.core.utils.parser import vn_to_snake_case as E;A.columns=[E(str(A))for A in A.columns]
		elif B==bytes([114,101,97,100,97,98,108,101]).decode():
			from.const import RATIO_COLUMN_MAP_EN as F,RATIO_COLUMN_MAP_VI as G
			if lang==bytes([118,105]).decode():C=G
			else:C=F
			A.columns=[C.get(str(A),str(A))for A in A.columns]
		for D in[bytes([121,101,97,114]).decode(),bytes([113,117,97,114,116,101,114]).decode()]:
			if D in A.columns:A=A.drop(columns=D)
		return A
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([102,105,110,97,110,99,105,97,108]).decode(),bytes([118,99,105]).decode(),Finance)