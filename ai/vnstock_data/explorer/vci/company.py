'\nModule quản lý thông tin công ty từ nguồn dữ liệu VCI.\n'
from datetime import datetime,timedelta
import pandas as pd
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake,get_asset_type
from vnstock.core.utils.transform import drop_cols_by_pattern,reorder_cols
from vnstock_data.core.utils.client import send_request
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.vci.const import _VCI_COMPANY_URL,_VCIQ_URL
logger=get_logger(__name__)
class Company:
	'\n    Class (lớp) quản lý các thông tin liên quan đến công ty từ nguồn dữ liệu VCI.\n\n    Tham số:\n        - symbol (str): Mã chứng khoán của công ty cần truy xuất thông tin.\n        - random_agent (bool): Sử dụng user-agent ngẫu nhiên hoặc không. Mặc định là False.\n        - to_df (bool): Chuyển đổi dữ liệu thành DataFrame hoặc không. Mặc định là True.\n        - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là False.\n    '
	def __init__(A,symbol,random_agent=False,to_df=True,show_log=False):
		'\n        Khởi tạo đối tượng Company với các tham số cho việc truy xuất dữ liệu.\n        ';B=show_log;A.symbol=symbol.upper();A.asset_type=get_asset_type(A.symbol)
		if A.asset_type not in[bytes([115,116,111,99,107]).decode()]:raise ValueError(bytes([77,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,225,187,149,32,112,104,105,225,186,191,117,32,109,225,187,155,105,32,99,195,179,32,116,104,195,180,110,103,32,116,105,110,46]).decode())
		A.headers=get_headers(data_source=bytes([86,67,73]).decode(),random_agent=random_agent);A.show_log=B;A.to_df=to_df;A.base_url=_VCI_COMPANY_URL;A.cms_base_url=bytes([104,116,116,112,115,58,47,47,119,119,119,46,118,105,101,116,99,97,112,46,99,111,109,46,118,110,47,97,112,105,47,99,109,115,45,115,101,114,118,105,99,101,47,118,50]).decode()
		if not B:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	def _fetch_company_details(A):
		'\n        Fetch company overview details from REST API.\n        \n        Returns:\n            Dict: Company details data.\n        ';B=f"{A.base_url}/details?ticker={A.symbol}"
		if A.show_log:logger.debug(f"Requesting company details for {A.symbol} from {B}")
		C=send_request(url=B,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=A.show_log);return C.get(bytes([100,97,116,97]).decode(),{})
	def _fetch_shareholders(A):
		'\n        Fetch shareholder structure from REST API.\n        \n        Returns:\n            Dict: Shareholder data.\n        ';B=f"{A.base_url}/{A.symbol}/shareholder-structure"
		if A.show_log:logger.debug(f"Requesting shareholder structure for {A.symbol} from {B}")
		C=send_request(url=B,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=A.show_log);return C.get(bytes([100,97,116,97]).decode(),{})
	def _fetch_shareholder_list(A):
		'\n        Fetch shareholder list from REST API (includes both individuals and organizations).\n        \n        Returns:\n            Dict: Shareholder list data.\n        ';B=f"{A.base_url}/{A.symbol}/shareholder"
		if A.show_log:logger.debug(f"Requesting shareholder list for {A.symbol} from {B}")
		C=send_request(url=B,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=A.show_log);return C.get(bytes([100,97,116,97]).decode(),[])
	def _fetch_relationships(A):
		'\n        Fetch subsidiary and affiliate relationships from REST API.\n        \n        Returns:\n            Dict: Relationship data.\n        ';B=f"{A.base_url}/{A.symbol}/relationship"
		if A.show_log:logger.debug(f"Requesting relationships for {A.symbol} from {B}")
		C=send_request(url=B,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=A.show_log);return C.get(bytes([100,97,116,97]).decode(),{})
	def _fetch_news_events(A,from_date=None,to_date=None,event_codes=None):
		'\n        Fetch news and events from REST API.\n        \n        Returns:\n            List: News and events data.\n        ';D=event_codes;C=to_date;B=from_date
		if B is None:B=(datetime.now()-timedelta(days=120)).strftime(bytes([37,89,37,109,37,100]).decode())
		if C is None:C=datetime.now().strftime(bytes([37,89,37,109,37,100]).decode())
		if D is None:D=bytes([68,73,86,44,73,83,83]).decode()
		E=f"{_VCIQ_URL}/v1/news-events-for-chart?ticker={A.symbol}&fromDate={B}&toDate={C}&languageId=1&eventCode={D}"
		if A.show_log:logger.debug(f"Requesting news and events for {A.symbol} from {E}")
		F=send_request(url=E,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=A.show_log);return F.get(bytes([100,97,116,97]).decode(),[])
	def _fetch_news(A,from_date=None,to_date=None,page=0,size=50):
		'\n        Fetch news from REST API (alternative endpoint with more data).\n        \n        Returns:\n            List: News data.\n        ';C=to_date;B=from_date
		if B is None:B=(datetime.now()-timedelta(days=3650)).strftime(bytes([37,89,37,109,37,100]).decode())
		if C is None:C=datetime.now().strftime(bytes([37,89,37,109,37,100]).decode())
		D=f"{_VCIQ_URL}/v1/news?ticker={A.symbol}&fromDate={B}&toDate={C}&languageId=1&page={page}&size={size}"
		if A.show_log:logger.debug(f"Requesting news for {A.symbol} from {D}")
		F=send_request(url=D,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=A.show_log);E=F.get(bytes([100,97,116,97]).decode(),{})
		if isinstance(E,dict):return E.get(bytes([99,111,110,116,101,110,116]).decode(),[])
		return[]
	def _fetch_financial_statistics(A):
		'\n        Fetch financial statistics summary from REST API.\n        \n        Returns:\n            Dict: Financial statistics data.\n        ';B=f"{A.base_url}/{A.symbol}/statistics-financial"
		if A.show_log:logger.debug(f"Requesting financial statistics for {A.symbol} from {B}")
		C=send_request(url=B,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=A.show_log);return C.get(bytes([100,97,116,97]).decode(),{})
	def _fetch_analysis_reports(A,company_id=None):
		'\n        Fetch analysis reports from CMS API.\n        \n        Args:\n            company_id (str): Company ID for the CMS API. If None, will try to fetch from company details.\n        \n        Returns:\n            List: Analysis reports data.\n        ';B=company_id
		if B is None:
			try:F=A._fetch_company_details();B=F.get(bytes([105,100]).decode(),bytes([49,51,51]).decode())
			except:B=bytes([49,51,51]).decode()
		C=f"{A.cms_base_url}/page/analysis?is-all=false&page=0&size=20&direction=DESC&sortBy=date&companyId={B}&page-ids=144&page-ids=141&language=1"
		if A.show_log:logger.debug(f"Requesting analysis reports from {C}")
		G=send_request(url=C,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=A.show_log);D=G.get(bytes([100,97,116,97]).decode(),{})
		if isinstance(D,dict):
			E=D.get(bytes([112,97,103,105,110,103,71,101,110,101,114,97,108,82,101,115,112,111,110,115,101,115]).decode(),{})
			if isinstance(E,dict):return E.get(bytes([99,111,110,116,101,110,116]).decode(),[])
		return[]
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def info(self):
		'\n        Truy xuất thông tin công ty theo chuẩn schema mapping.\n        \n        Returns:\n            pd.DataFrame: DataFrame chứa thông tin công ty với columns chuẩn hóa.\n        ';D=self._fetch_company_details()
		if not D:return pd.DataFrame()
		A=pd.DataFrame([D]);B={}
		if bytes([116,105,99,107,101,114]).decode()in A.columns:B[bytes([115,121,109,98,111,108]).decode()]=A[bytes([116,105,99,107,101,114]).decode()].iloc[0]
		if bytes([118,105,79,114,103,97,110,78,97,109,101]).decode()in A.columns:B[bytes([110,97,109,101]).decode()]=A[bytes([118,105,79,114,103,97,110,78,97,109,101]).decode()].iloc[0]
		elif bytes([101,110,79,114,103,97,110,78,97,109,101]).decode()in A.columns:B[bytes([110,97,109,101]).decode()]=A[bytes([101,110,79,114,103,97,110,78,97,109,101]).decode()].iloc[0]
		if bytes([118,105,79,114,103,97,110,83,104,111,114,116,78,97,109,101]).decode()in A.columns:B[bytes([115,104,111,114,116,95,110,97,109,101]).decode()]=A[bytes([118,105,79,114,103,97,110,83,104,111,114,116,78,97,109,101]).decode()].iloc[0]
		elif bytes([101,110,79,114,103,97,110,83,104,111,114,116,78,97,109,101]).decode()in A.columns:B[bytes([115,104,111,114,116,95,110,97,109,101]).decode()]=A[bytes([101,110,79,114,103,97,110,83,104,111,114,116,78,97,109,101]).decode()].iloc[0]
		if bytes([115,101,99,116,111,114,86,110]).decode()in A.columns:B[bytes([115,101,99,116,111,114]).decode()]=A[bytes([115,101,99,116,111,114,86,110]).decode()].iloc[0]
		elif bytes([115,101,99,116,111,114]).decode()in A.columns:B[bytes([115,101,99,116,111,114]).decode()]=A[bytes([115,101,99,116,111,114]).decode()].iloc[0]
		if bytes([112,114,111,102,105,108,101]).decode()in A.columns:B[bytes([112,114,111,102,105,108,101]).decode()]=A[bytes([112,114,111,102,105,108,101]).decode()].iloc[0]
		elif bytes([101,110,80,114,111,102,105,108,101]).decode()in A.columns:B[bytes([112,114,111,102,105,108,101]).decode()]=A[bytes([101,110,80,114,111,102,105,108,101]).decode()].iloc[0]
		if bytes([108,105,115,116,105,110,103,68,97,116,101]).decode()in A.columns:B[bytes([108,105,115,116,105,110,103,95,100,97,116,101]).decode()]=A[bytes([108,105,115,116,105,110,103,68,97,116,101]).decode()].iloc[0]
		C=pd.DataFrame([B]);E=[bytes([115,121,109,98,111,108]).decode(),bytes([110,97,109,101]).decode(),bytes([115,104,111,114,116,95,110,97,109,101]).decode(),bytes([115,101,99,116,111,114]).decode(),bytes([112,114,111,102,105,108,101]).decode(),bytes([108,105,115,116,105,110,103,95,100,97,116,101]).decode()];F=[A for A in E if A in C.columns];C=C[F];return C
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def overview(self):
		'\n        Truy xuất thông tin tổng quan của công ty (raw data từ API).\n        \n        Returns:\n            pd.DataFrame: DataFrame chứa thông tin tổng quan của công ty.\n        ';B=self._fetch_company_details()
		if not B:return pd.DataFrame()
		A=pd.DataFrame([B]);A.columns=[camel_to_snake(A)for A in A.columns];A=drop_cols_by_pattern(A,[bytes([101,110,95]).decode(),bytes([95,95]).decode()])
		if bytes([115,101,99,116,111,114,95,118,110]).decode()in A.columns and bytes([115,101,99,116,111,114]).decode()in A.columns:A=A.drop(columns=[bytes([115,101,99,116,111,114,95,118,110]).decode()])
		D={bytes([118,105,95,111,114,103,97,110,95,110,97,109,101]).decode():bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([118,105,95,111,114,103,97,110,95,115,104,111,114,116,95,110,97,109,101]).decode():bytes([111,114,103,97,110,95,115,104,111,114,116,95,110,97,109,101]).decode(),bytes([112,114,111,102,105,108,101]).decode():bytes([99,111,109,112,97,110,121,95,112,114,111,102,105,108,101]).decode(),bytes([110,117,109,98,101,114,95,111,102,95,115,104,97,114,101,115,95,109,107,116,95,99,97,112]).decode():bytes([105,115,115,117,101,95,115,104,97,114,101]).decode(),bytes([116,105,99,107,101,114]).decode():bytes([115,121,109,98,111,108]).decode()};C={B:C for(B,C)in D.items()if B in A.columns}
		if C:A=A.rename(columns=C)
		if bytes([99,111,109,112,97,110,121,95,112,114,111,102,105,108,101]).decode()in A.columns:
			import re
			def E(text):
				A=text
				if not isinstance(A,str):return A
				A=re.sub(bytes([60,91,94,62,93,43,62]).decode(),'',A);import html;A=html.unescape(A);A=bytes([32]).decode().join(A.split());return A
			A[bytes([99,111,109,112,97,110,121,95,112,114,111,102,105,108,101]).decode()]=A[bytes([99,111,109,112,97,110,121,95,112,114,111,102,105,108,101]).decode()].apply(E)
		A=reorder_cols(A,[bytes([115,121,109,98,111,108]).decode()],position=bytes([102,105,114,115,116]).decode());return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def shareholders(self,mode=bytes([100,101,116,97,105,108,101,100]).decode()):
		"\n        Truy xuất thông tin cổ đông của công ty.\n        \n        Tham số:\n            - mode (str): Chế độ hiển thị\n                - 'summary': Tóm tắt cơ cấu cổ đông (mặc định)\n                - 'detailed': Danh sách chi tiết tất cả cổ đông\n        \n        Returns:\n            pd.DataFrame: DataFrame chứa thông tin cổ đông của công ty.\n        ";E=mode;D=self
		if E==bytes([115,117,109,109,97,114,121]).decode():
			B=D._fetch_shareholders()
			if not B:return pd.DataFrame()
			A=pd.DataFrame(B)if isinstance(B,list)else pd.DataFrame([B]);A.columns=[camel_to_snake(A)for A in A.columns];A=drop_cols_by_pattern(A,[bytes([95,95,116,121,112,101,110,97,109,101]).decode(),bytes([116,105,99,107,101,114]).decode(),bytes([101,110,95]).decode()])
			if bytes([117,112,100,97,116,101,95,100,97,116,101]).decode()in A.columns and A[bytes([117,112,100,97,116,101,95,100,97,116,101]).decode()].dtype in[int,float]:A[bytes([117,112,100,97,116,101,95,100,97,116,101]).decode()]=pd.to_datetime(A[bytes([117,112,100,97,116,101,95,100,97,116,101]).decode()],unit=bytes([109,115]).decode()).dt.strftime(bytes([37,89,45,37,109,45,37,100]).decode())
			C={}
			if bytes([111,119,110,101,114,95,102,117,108,108,95,110,97,109,101]).decode()in A.columns:C[bytes([111,119,110,101,114,95,102,117,108,108,95,110,97,109,101]).decode()]=bytes([115,104,97,114,101,95,104,111,108,100,101,114]).decode()
			if bytes([112,101,114,99,101,110,116,97,103,101]).decode()in A.columns:C[bytes([112,101,114,99,101,110,116,97,103,101]).decode()]=bytes([115,104,97,114,101,95,111,119,110,95,112,101,114,99,101,110,116]).decode()
			if C:A=A.rename(columns=C)
			return A
		elif E==bytes([100,101,116,97,105,108,101,100]).decode():
			B=D._fetch_shareholder_list()
			if not B:return pd.DataFrame()
			A=pd.DataFrame(B);A.columns=[camel_to_snake(A)for A in A.columns];A=drop_cols_by_pattern(A,[bytes([95,95,116,121,112,101,110,97,109,101]).decode(),bytes([116,105,99,107,101,114]).decode(),bytes([101,110,95]).decode(),bytes([111,119,110,101,114,95,116,121,112,101]).decode(),bytes([111,119,110,101,114,95,99,111,100,101]).decode(),bytes([112,111,115,105,116,105,111,110,95,110,97,109,101]).decode(),bytes([112,117,98,108,105,99,95,100,97,116,101]).decode()]);C={bytes([111,119,110,101,114,95,110,97,109,101]).decode():bytes([115,104,97,114,101,95,104,111,108,100,101,114]).decode(),bytes([112,101,114,99,101,110,116,97,103,101]).decode():bytes([115,104,97,114,101,95,111,119,110,95,112,101,114,99,101,110,116]).decode()};F={B:C for(B,C)in C.items()if B in A.columns}
			if F:A=A.rename(columns=F)
			A.insert(0,bytes([115,121,109,98,111,108]).decode(),D.symbol);G=[bytes([115,121,109,98,111,108]).decode(),bytes([115,104,97,114,101,95,104,111,108,100,101,114]).decode(),bytes([113,117,97,110,116,105,116,121]).decode(),bytes([115,104,97,114,101,95,111,119,110,95,112,101,114,99,101,110,116]).decode(),bytes([117,112,100,97,116,101,95,100,97,116,101]).decode()];H=[B for B in G if B in A.columns];A=A[H];return A
		else:raise ValueError(f"Invalid mode: {E}. Use 'summary' or 'detailed'")
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def officers(self,filter_by=bytes([119,111,114,107,105,110,103]).decode()):
		"\n        Truy xuất thông tin lãnh đạo công ty (cá nhân có vị trí).\n\n        Tham số:\n            - filter_by (str): Lọc lãnh đạo đang làm việc hoặc đã từ nhiệm hoặc tất cả.\n                - 'working': Lọc lãnh đạo đang làm việc (mặc định).\n                - 'resigned': Lọc lãnh đạo đã từ nhiệm.\n                - 'all': Lọc tất cả lãnh đạo.\n\n        Returns:\n            pd.DataFrame: DataFrame chứa thông tin lãnh đạo của công ty.\n        "
		if filter_by not in[bytes([119,111,114,107,105,110,103]).decode(),bytes([114,101,115,105,103,110,101,100]).decode(),bytes([97,108,108]).decode()]:raise ValueError(bytes([102,105,108,116,101,114,95,98,121,32,99,104,225,187,137,32,110,104,225,186,173,110,32,103,105,195,161,32,116,114,225,187,139,32,39,119,111,114,107,105,110,103,39,32,104,111,225,186,183,99,32,39,114,101,115,105,103,110,101,100,39,32,104,111,225,186,183,99,32,39,97,108,108,39]).decode())
		B=self._fetch_shareholder_list()
		if not B:return pd.DataFrame()
		A=pd.DataFrame(B)if isinstance(B,list)else pd.DataFrame([B]);A.columns=[camel_to_snake(A)for A in A.columns]
		if bytes([111,119,110,101,114,95,116,121,112,101]).decode()in A.columns:A=A[A[bytes([111,119,110,101,114,95,116,121,112,101]).decode()]==bytes([73,78,68,73,86,73,68,85,65,76]).decode()]
		if bytes([112,111,115,105,116,105,111,110,95,110,97,109,101]).decode()in A.columns:A=A[A[bytes([112,111,115,105,116,105,111,110,95,110,97,109,101]).decode()].notna()]
		A=drop_cols_by_pattern(A,[bytes([101,110,95]).decode(),bytes([95,95]).decode(),bytes([111,119,110,101,114,95,99,111,100,101]).decode(),bytes([111,119,110,101,114,95,116,121,112,101]).decode(),bytes([112,117,98,108,105,99,95,100,97,116,101]).decode()]);D={bytes([111,119,110,101,114,95,110,97,109,101]).decode():bytes([111,102,102,105,99,101,114,95,110,97,109,101]).decode(),bytes([112,111,115,105,116,105,111,110,95,110,97,109,101]).decode():bytes([111,102,102,105,99,101,114,95,112,111,115,105,116,105,111,110]).decode(),bytes([112,101,114,99,101,110,116,97,103,101]).decode():bytes([111,102,102,105,99,101,114,95,111,119,110,95,112,101,114,99,101,110,116]).decode(),bytes([113,117,97,110,116,105,116,121]).decode():bytes([111,102,102,105,99,101,114,95,111,119,110,95,113,117,97,110,116,105,116,121]).decode()};C={B:C for(B,C)in D.items()if B in A.columns}
		if C:A=A.rename(columns=C)
		A.insert(0,bytes([115,121,109,98,111,108]).decode(),self.symbol)
		if bytes([117,112,100,97,116,101,95,100,97,116,101]).decode()in A.columns and A[bytes([117,112,100,97,116,101,95,100,97,116,101]).decode()].dtype in[int,float]:A[bytes([117,112,100,97,116,101,95,100,97,116,101]).decode()]=pd.to_datetime(A[bytes([117,112,100,97,116,101,95,100,97,116,101]).decode()],unit=bytes([109,115]).decode()).dt.strftime(bytes([37,89,45,37,109,45,37,100]).decode())
		E=[bytes([115,121,109,98,111,108]).decode(),bytes([111,102,102,105,99,101,114,95,110,97,109,101]).decode(),bytes([111,102,102,105,99,101,114,95,112,111,115,105,116,105,111,110]).decode(),bytes([111,102,102,105,99,101,114,95,111,119,110,95,112,101,114,99,101,110,116]).decode(),bytes([111,102,102,105,99,101,114,95,111,119,110,95,113,117,97,110,116,105,116,121]).decode(),bytes([117,112,100,97,116,101,95,100,97,116,101]).decode()];F=[B for B in E if B in A.columns];A=A[F];return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def subsidiaries(self,filter_by=bytes([97,108,108]).decode()):
		"\n        Truy xuất thông tin công ty con của công ty.\n\n        Tham số:\n            - filter_by (str): Lọc công ty con hoặc công ty liên kết.\n                - 'all': Lọc tất cả.\n                - 'subsidiary': Lọc công ty con.\n                - 'affiliate': Lọc công ty liên kết.\n\n        Returns:\n            pd.DataFrame: DataFrame chứa thông tin công ty con.\n        ";H=filter_by;G=self
		if H not in[bytes([97,108,108]).decode(),bytes([115,117,98,115,105,100,105,97,114,121]).decode(),bytes([97,102,102,105,108,105,97,116,101]).decode()]:raise ValueError(bytes([102,105,108,116,101,114,95,98,121,32,99,104,225,187,137,32,110,104,225,186,173,110,32,103,105,195,161,32,116,114,225,187,139,32,39,97,108,108,39,32,104,111,225,186,183,99,32,39,115,117,98,115,105,100,105,97,114,121,39,32,104,111,225,186,183,99,32,39,97,102,102,105,108,105,97,116,101,39]).decode())
		D=G._fetch_relationships()
		if not D:return pd.DataFrame()
		if isinstance(D,dict):I=D.get(bytes([115,117,98,115,105,100,105,97,114,105,101,115]).decode(),[]);J=D.get(bytes([97,102,102,105,108,105,97,116,101,115]).decode(),[])
		else:I=[];J=[]
		E=[]
		if H in[bytes([97,108,108]).decode(),bytes([115,117,98,115,105,100,105,97,114,121]).decode()]and I:
			A=pd.DataFrame(I);A.columns=[camel_to_snake(A)for A in A.columns];A=drop_cols_by_pattern(A,[bytes([95,95,116,121,112,101,110,97,109,101]).decode(),bytes([101,110,95]).decode()]);K={bytes([114,105,103,104,116,95,111,114,103,97,110,95,110,97,109,101,95,118,105]).decode():bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([114,105,103,104,116,95,111,114,103,97,110,95,99,111,100,101]).decode():bytes([115,117,98,95,111,114,103,97,110,95,99,111,100,101]).decode(),bytes([111,119,110,101,100,95,112,101,114,99,101,110,116,97,103,101]).decode():bytes([111,119,110,101,114,115,104,105,112,95,112,101,114,99,101,110,116]).decode()};C={B:C for(B,C)in K.items()if B in A.columns}
			if C:A=A.rename(columns=C)
			if bytes([111,114,103,97,110,95,99,111,100,101]).decode()in A.columns:A=A.drop(columns=[bytes([111,114,103,97,110,95,99,111,100,101]).decode()])
			A.insert(0,bytes([115,121,109,98,111,108]).decode(),G.symbol);E.append(A)
		if H in[bytes([97,108,108]).decode(),bytes([97,102,102,105,108,105,97,116,101]).decode()]and J:
			B=pd.DataFrame(J);B.columns=[camel_to_snake(A)for A in B.columns];B=drop_cols_by_pattern(B,[bytes([95,95,116,121,112,101,110,97,109,101]).decode(),bytes([101,110,95]).decode()]);K={bytes([114,105,103,104,116,95,111,114,103,97,110,95,110,97,109,101,95,118,105]).decode():bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([114,105,103,104,116,95,111,114,103,97,110,95,99,111,100,101]).decode():bytes([115,117,98,95,111,114,103,97,110,95,99,111,100,101]).decode(),bytes([111,119,110,101,100,95,112,101,114,99,101,110,116,97,103,101]).decode():bytes([111,119,110,101,114,115,104,105,112,95,112,101,114,99,101,110,116]).decode()};C={A:C for(A,C)in K.items()if A in B.columns}
			if C:B=B.rename(columns=C)
			if bytes([111,114,103,97,110,95,99,111,100,101]).decode()in B.columns:B=B.drop(columns=[bytes([111,114,103,97,110,95,99,111,100,101]).decode()])
			B.insert(0,bytes([115,121,109,98,111,108]).decode(),G.symbol);E.append(B)
		if E:F=pd.concat(E,ignore_index=True);L=[bytes([115,121,109,98,111,108]).decode(),bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([111,119,110,101,114,115,104,105,112,95,112,101,114,99,101,110,116]).decode(),bytes([115,117,98,95,111,114,103,97,110,95,99,111,100,101]).decode(),bytes([116,121,112,101]).decode()];M=[A for A in L if A in F.columns];F=F[M];return F
		else:return pd.DataFrame()
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def affiliate(self):
		'\n        Truy xuất thông tin công ty liên kết của công ty.\n        \n        Returns:\n            pd.DataFrame: DataFrame chứa thông tin công ty liên kết.\n        ';B=self._fetch_relationships()
		if not B:return pd.DataFrame()
		if isinstance(B,dict):C=B.get(bytes([97,102,102,105,108,105,97,116,101,115]).decode(),[])
		else:C=[]
		if not C:return pd.DataFrame()
		A=pd.DataFrame(C);A.columns=[camel_to_snake(A)for A in A.columns];A=drop_cols_by_pattern(A,[bytes([101,110,95]).decode(),bytes([95,95,116,121,112,101,110,97,109,101]).decode()])
		if bytes([111,114,103,97,110,95,99,111,100,101]).decode()in A.columns:A=A.drop(columns=[bytes([111,114,103,97,110,95,99,111,100,101]).decode()])
		if bytes([112,101,114,99,101,110,116,97,103,101]).decode()in A.columns:A=A.rename(columns={bytes([112,101,114,99,101,110,116,97,103,101]).decode():bytes([111,119,110,101,114,115,104,105,112,95,112,101,114,99,101,110,116]).decode()})
		return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def news(self):
		'\n        Truy xuất tin tức liên quan đến công ty.\n        \n        Returns:\n            pd.DataFrame: DataFrame chứa tin tức liên quan đến công ty.\n        ';B=self._fetch_news()
		if not B:return pd.DataFrame()
		A=pd.DataFrame(B);A.columns=[camel_to_snake(A)for A in A.columns];C=[B for B in[bytes([111,114,103,97,110,95,99,111,100,101]).decode(),bytes([115,121,109,98,111,108]).decode(),bytes([95,95,116,121,112,101,110,97,109,101]).decode(),bytes([105,115,95,101,118,101,110,116]).decode(),bytes([101,118,101,110,116]).decode(),bytes([99,114,101,97,116,101,95,98,121]).decode(),bytes([117,112,100,97,116,101,95,98,121]).decode(),bytes([115,116,97,116,117,115]).decode(),bytes([99,114,101,97,116,101,95,100,97,116,101]).decode(),bytes([117,112,100,97,116,101,95,100,97,116,101]).decode(),bytes([115,111,117,114,99,101,95,99,111,100,101]).decode(),bytes([101,120,112,101,114,116,95,105,100]).decode(),bytes([105,115,95,116,114,97,110,102,101,114]).decode()]if B in A.columns]
		if C:A=A.drop(columns=C)
		return A
	def _fetch_events(A,event_codes=None,from_date=None,to_date=None,page=0,size=50):
		"\n        Fetch events from REST API.\n        \n        Args:\n            event_codes (str): Event codes to fetch (comma-separated)\n                - 'DIV,ISS': Trả cổ tức & phát hành thêm\n                - 'DDIND,DDINS,DDRP': Giao dịch cổ đông lớn & cổ đông nội bộ\n                - 'AGME,AGMR,EGME': Đại hội cổ đông\n                - 'AIS,MA,MOVE,NLIS,OTHE,RETU,SUSP': Sự kiện khác\n            from_date (str): Start date in YYYYMMDD format\n            to_date (str): End date in YYYYMMDD format\n            page (int): Page number (0-indexed)\n            size (int): Number of items per page\n        \n        Returns:\n            List: Events data.\n        ";D=to_date;C=from_date;B=event_codes
		if B is None:B=bytes([68,73,86,44,73,83,83,44,68,68,73,78,68,44,68,68,73,78,83,44,68,68,82,80,44,65,71,77,69,44,65,71,77,82,44,69,71,77,69,44,65,73,83,44,77,65,44,77,79,86,69,44,78,76,73,83,44,79,84,72,69,44,82,69,84,85,44,83,85,83,80]).decode()
		if C is None:C=(datetime.now()-timedelta(days=3650)).strftime(bytes([37,89,37,109,37,100]).decode())
		if D is None:D=datetime.now().strftime(bytes([37,89,37,109,37,100]).decode())
		E=f"{_VCIQ_URL}/v1/events?ticker={A.symbol}&fromDate={C}&toDate={D}&eventCode={B}&page={page}&size={size}"
		if A.show_log:logger.debug(f"Requesting events for {A.symbol} from {E}")
		G=send_request(url=E,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=A.show_log);F=G.get(bytes([100,97,116,97]).decode(),{})
		if isinstance(F,dict):return F.get(bytes([99,111,110,116,101,110,116]).decode(),[])
		return[]
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def events(self):
		'\n        Truy xuất các sự kiện của công ty.\n        \n        Returns:\n            pd.DataFrame: DataFrame chứa các sự kiện của công ty.\n        ';C=self._fetch_events()
		if not C:return pd.DataFrame()
		A=pd.DataFrame(C);A.columns=[camel_to_snake(A)for A in A.columns];D=[B for B in[bytes([111,114,103,97,110,95,99,111,100,101]).decode(),bytes([115,121,109,98,111,108]).decode(),bytes([95,95,116,121,112,101,110,97,109,101]).decode(),bytes([105,115,95,101,118,101,110,116]).decode(),bytes([101,118,101,110,116]).decode(),bytes([111,114,103,97,110,95,110,97,109,101,95,101,110]).decode(),bytes([111,114,103,97,110,95,110,97,109,101,95,118,105]).decode()]if B in A.columns]
		if D:A=A.drop(columns=D)
		E=[bytes([112,117,98,108,105,99,95,100,97,116,101]).decode(),bytes([105,115,115,117,101,95,100,97,116,101]).decode(),bytes([114,101,99,111,114,100,95,100,97,116,101]).decode(),bytes([101,120,114,105,103,104,116,95,100,97,116,101]).decode(),bytes([100,105,115,112,108,97,121,95,100,97,116,101]).decode()]
		for B in E:
			if B in A.columns:
				if A[B].dtype in[int,float]:A[B]=pd.to_datetime(A[B],unit=bytes([109,115]).decode()).dt.strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				elif A[B].dtype==bytes([111,98,106,101,99,116]).decode():
					try:A[B]=pd.to_datetime(A[B]).dt.strftime(bytes([37,89,45,37,109,45,37,100]).decode())
					except:pass
		return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def reports(self):
		'\n        Truy xuất báo cáo phân tích về công ty.\n        \n        Returns:\n            pd.DataFrame: DataFrame chứa các báo cáo phân tích về công ty.\n        ';B=self._fetch_analysis_reports()
		if not B:return pd.DataFrame()
		A=pd.DataFrame(B);A.columns=[camel_to_snake(A)for A in A.columns];C=[B for B in[bytes([95,95,116,121,112,101,110,97,109,101]).decode(),bytes([112,97,103,101,95,105,100]).decode()]if B in A.columns]
		if C:A=A.drop(columns=C)
		if bytes([100,97,116,101]).decode()in A.columns:
			if A[bytes([100,97,116,101]).decode()].dtype in[int,float]:A[bytes([100,97,116,101]).decode()]=pd.to_datetime(A[bytes([100,97,116,101]).decode()],unit=bytes([109,115]).decode()).dt.strftime(bytes([37,89,45,37,109,45,37,100]).decode())
			elif A[bytes([100,97,116,101]).decode()].dtype==bytes([111,98,106,101,99,116]).decode():
				try:A[bytes([100,97,116,101]).decode()]=pd.to_datetime(A[bytes([100,97,116,101]).decode()]).dt.strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				except:pass
		return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def trading_stats(self):
		'\n        Truy xuất thống kê giao dịch của công ty.\n        \n        Returns:\n            pd.DataFrame: DataFrame chứa thống kê giao dịch của công ty.\n        ';B=self._fetch_company_details()
		if not B:return pd.DataFrame()
		A=pd.DataFrame([B]);A.columns=[camel_to_snake(A)for A in A.columns];A=drop_cols_by_pattern(A,[bytes([95,95,116,121,112,101,110,97,109,101]).decode()]);A[bytes([115,121,109,98,111,108]).decode()]=self.symbol;A=reorder_cols(A,[bytes([115,121,109,98,111,108]).decode()],position=bytes([102,105,114,115,116]).decode());return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def ratio_summary(self):
		'\n        Truy xuất tóm tắt các tỷ lệ tài chính của công ty.\n        \n        Returns:\n            pd.DataFrame: DataFrame chứa tóm tắt các tỷ lệ tài chính của công ty.\n        ';B=self._fetch_financial_statistics()
		if not B:return pd.DataFrame()
		if isinstance(B,list):
			if len(B)==0:return pd.DataFrame()
			A=pd.DataFrame(B)
		else:A=pd.DataFrame([B])
		A.columns=[camel_to_snake(str(A))for A in A.columns];A=drop_cols_by_pattern(A,[bytes([95,95,116,121,112,101,110,97,109,101]).decode()]);A[bytes([115,121,109,98,111,108]).decode()]=self.symbol;A=reorder_cols(A,cols=[bytes([115,121,109,98,111,108]).decode()],position=bytes([102,105,114,115,116]).decode());return A
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([99,111,109,112,97,110,121]).decode(),bytes([118,99,105]).decode(),Company)