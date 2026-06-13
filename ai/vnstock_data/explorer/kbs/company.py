'Company module for KB Securities (KBS) data source.'
import pandas as pd
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake,get_asset_type
from vnstock.core.utils.transform import clean_html_dict
from vnstock_data.core.utils.client import ProxyConfig,send_request
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.kbs.const import _CHARTER_CAPITAL_MAP,_COMPANY_PROFILE_MAP,_EVENT_TYPE,_EXCHANGE_CODE_MAP,_LABOR_STRUCTURE_MAP,_LEADERS_MAP,_OWNERSHIP_MAP,_SHAREHOLDERS_MAP,_STOCK_INFO_URL,_SUBSIDIARIES_MAP
logger=get_logger(__name__)
def _parse_kbs_date(x):
	if pd.isna(x):return pd.NaT
	A=str(x);B=A.split(bytes([47]).decode())
	if len(B)==3:return pd.to_datetime(A,format=bytes([37,100,47,37,109,47,37,89]).decode(),errors=bytes([99,111,101,114,99,101]).decode())
	elif len(B)==2:return pd.to_datetime(A,format=bytes([37,109,47,37,89]).decode(),errors=bytes([99,111,101,114,99,101]).decode())
	return pd.to_datetime(A,errors=bytes([99,111,101,114,99,101]).decode())
class Company:
	'\n    Lớp truy cập thông tin công ty từ KB Securities (KBS).\n    \n    Tính năng:\n    - Fetch dữ liệu công ty từ API (một lần)\n    - Cache dữ liệu để tránh gọi lại\n    - Xử lý và trả về từng nhóm dữ liệu theo method được gọi\n    - Tương tự cấu trúc của VCI Company\n    '
	def __init__(A,symbol,random_agent=False,proxy_config=None,show_log=False,proxy_mode=None,proxy_list=None):
		"\n        Khởi tạo Company client cho KBS.\n\n        Args:\n            symbol: Mã chứng khoán (VD: 'ACB', 'VNM').\n            random_agent: Sử dụng user agent ngẫu nhiên. Mặc định False.\n            proxy_config: Cấu hình proxy. Mặc định None.\n            show_log: Hiển thị log debug. Mặc định False.\n            proxy_mode: Chế độ proxy (try, rotate, random, single). Mặc định None.\n            proxy_list: Danh sách proxy URLs. Mặc định None.\n\n        Raises:\n            ValueError: Nếu mã không phải là cổ phiếu.\n        ";E=proxy_mode;D=show_log;C=proxy_config;B=proxy_list;A.symbol=symbol.upper();A.asset_type=get_asset_type(A.symbol)
		if A.asset_type not in[bytes([115,116,111,99,107]).decode()]:raise ValueError(bytes([77,195,163,32,67,75,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,32,104,111,225,186,183,99,32,107,104,195,180,110,103,32,112,104,225,186,163,105,32,99,225,187,149,32,112,104,105,225,186,191,117,46]).decode())
		A.data_source=bytes([75,66,83]).decode();A.headers=get_headers(data_source=A.data_source,random_agent=random_agent);A.show_log=D
		if C is None:
			G=E if E else bytes([116,114,121]).decode();F=bytes([100,105,114,101,99,116]).decode()
			if B and len(B)>0:F=bytes([112,114,111,120,121]).decode()
			A.proxy_config=ProxyConfig(proxy_mode=G,proxy_list=B,request_mode=F)
		else:A.proxy_config=C
		if not D:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
		A._raw_data=None;A._cache_loaded=False
	def _load_cache(A,show_log=False):
		'\n        Fetch và cache dữ liệu công ty từ API (một lần).\n        \n        Returns:\n            Dictionary chứa tất cả dữ liệu công ty.\n        '
		if A._cache_loaded and A._raw_data is not None:return A._raw_data
		C=f"{_STOCK_INFO_URL}/profile/{A.symbol}";D={bytes([108]).decode():1};B=send_request(url=C,headers=A.headers,method=bytes([71,69,84]).decode(),params=D,show_log=show_log or A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode,auto_fetch=A.proxy_config.auto_fetch,validate_proxies=A.proxy_config.validate_proxies,prefer_speed=A.proxy_config.prefer_speed);A._raw_data=B;A._cache_loaded=True;return B
	def _fetch_profile(A,show_log=False):'\n        Lấy thông tin profile công ty từ cache hoặc API.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            Dictionary chứa thông tin profile công ty.\n        ';return A._load_cache(show_log=show_log)
	def _process_profile_data(E,raw_data):
		'\n        Xử lý dữ liệu profile thô từ API.\n        \n        Args:\n            raw_data: Dữ liệu thô từ API\n            \n        Returns:\n            DataFrame chứa thông tin profile chuẩn hoá\n        ';B=raw_data
		if not B:return pd.DataFrame()
		C={}
		for(F,H)in _COMPANY_PROFILE_MAP.items():
			if F in B:C[H]=B[F]
		C=clean_html_dict(C)
		if B.get(bytes([76,97,98,111,114,83,116,114,117,99,116,117,114,101]).decode()):
			D=B[bytes([76,97,98,111,114,83,116,114,117,99,116,117,114,101]).decode()]
			if isinstance(D,list)and len(D)>0:
				G=sum(int(A.get(bytes([86,97,108,117,101]).decode(),0))for A in D if isinstance(A.get(bytes([86,97,108,117,101]).decode()),(int,str)))
				if G>0:C[bytes([110,117,109,98,101,114,95,111,102,95,101,109,112,108,111,121,101,101,115]).decode()]=G
		A=pd.DataFrame([C])
		if bytes([101,120,99,104,97,110,103,101]).decode()in A.columns:A[bytes([101,120,99,104,97,110,103,101]).decode()]=A[bytes([101,120,99,104,97,110,103,101]).decode()].map(lambda x:_EXCHANGE_CODE_MAP.get(x,x)if pd.notna(x)else x)
		A.attrs[bytes([115,121,109,98,111,108]).decode()]=E.symbol;A.attrs[bytes([115,111,117,114,99,101]).decode()]=E.data_source;return A
	def _process_subsidiaries(D,raw_data):
		'\n        Xử lý dữ liệu công ty con từ API.\n        \n        Args:\n            raw_data: Dữ liệu thô từ API\n            \n        Returns:\n            DataFrame chứa thông tin công ty con\n        ';B=raw_data
		if bytes([83,117,98,115,105,100,105,97,114,105,101,115]).decode()not in B or not B[bytes([83,117,98,115,105,100,105,97,114,105,101,115]).decode()]:return pd.DataFrame()
		A=pd.DataFrame(B[bytes([83,117,98,115,105,100,105,97,114,105,101,115]).decode()]);A=A.rename(columns=_SUBSIDIARIES_MAP)
		for C in[bytes([100,97,116,101]).decode()]:
			if C in A.columns:A[C]=A[C].apply(_parse_kbs_date)
		A.attrs[bytes([115,121,109,98,111,108]).decode()]=D.symbol;A.attrs[bytes([115,111,117,114,99,101]).decode()]=D.data_source;return A
	def _process_leaders(C,raw_data):
		'\n        Xử lý dữ liệu ban lãnh đạo từ API.\n        \n        Args:\n            raw_data: Dữ liệu thô từ API\n            \n        Returns:\n            DataFrame chứa thông tin ban lãnh đạo\n        ';B=raw_data
		if bytes([76,101,97,100,101,114,115]).decode()not in B or not B[bytes([76,101,97,100,101,114,115]).decode()]:return pd.DataFrame()
		A=pd.DataFrame(B[bytes([76,101,97,100,101,114,115]).decode()]);A=A.rename(columns=_LEADERS_MAP);A.attrs[bytes([115,121,109,98,111,108]).decode()]=C.symbol;A.attrs[bytes([115,111,117,114,99,101]).decode()]=C.data_source;return A
	def _process_ownership(D,raw_data):
		'\n        Xử lý dữ liệu cơ cấu cổ đông từ API.\n        \n        Args:\n            raw_data: Dữ liệu thô từ API\n            \n        Returns:\n            DataFrame chứa thông tin cơ cấu cổ đông\n        ';B=raw_data
		if bytes([79,119,110,101,114,115,104,105,112]).decode()not in B or not B[bytes([79,119,110,101,114,115,104,105,112]).decode()]:return pd.DataFrame()
		A=pd.DataFrame(B[bytes([79,119,110,101,114,115,104,105,112]).decode()]);A=A.rename(columns=_OWNERSHIP_MAP)
		for C in[bytes([100,97,116,101]).decode()]:
			if C in A.columns:A[C]=A[C].apply(_parse_kbs_date)
		A.attrs[bytes([115,121,109,98,111,108]).decode()]=D.symbol;A.attrs[bytes([115,111,117,114,99,101]).decode()]=D.data_source;return A
	def _process_shareholders(D,raw_data):
		'\n        Xử lý dữ liệu cổ đông lớn từ API.\n        \n        Args:\n            raw_data: Dữ liệu thô từ API\n            \n        Returns:\n            DataFrame chứa thông tin cổ đông lớn\n        ';B=raw_data
		if bytes([83,104,97,114,101,104,111,108,100,101,114,115]).decode()not in B or not B[bytes([83,104,97,114,101,104,111,108,100,101,114,115]).decode()]:return pd.DataFrame()
		A=pd.DataFrame(B[bytes([83,104,97,114,101,104,111,108,100,101,114,115]).decode()]);A=A.rename(columns=_SHAREHOLDERS_MAP)
		for C in[bytes([100,97,116,101]).decode()]:
			if C in A.columns:A[C]=A[C].apply(_parse_kbs_date)
		A.attrs[bytes([115,121,109,98,111,108]).decode()]=D.symbol;A.attrs[bytes([115,111,117,114,99,101]).decode()]=D.data_source;return A
	def _process_charter_capital(D,raw_data):
		'\n        Xử lý dữ liệu lịch sử vốn điều lệ từ API.\n        \n        Args:\n            raw_data: Dữ liệu thô từ API\n            \n        Returns:\n            DataFrame chứa lịch sử vốn điều lệ\n        ';B=raw_data
		if bytes([67,104,97,114,116,101,114,67,97,112,105,116,97,108]).decode()not in B or not B[bytes([67,104,97,114,116,101,114,67,97,112,105,116,97,108]).decode()]:return pd.DataFrame()
		A=pd.DataFrame(B[bytes([67,104,97,114,116,101,114,67,97,112,105,116,97,108]).decode()]);A=A.rename(columns=_CHARTER_CAPITAL_MAP)
		for C in[bytes([100,97,116,101]).decode()]:
			if C in A.columns:A[C]=A[C].apply(_parse_kbs_date)
		A.attrs[bytes([115,121,109,98,111,108]).decode()]=D.symbol;A.attrs[bytes([115,111,117,114,99,101]).decode()]=D.data_source;return A
	def _process_labor_structure(C,raw_data):
		'\n        Xử lý dữ liệu cơ cấu lao động từ API.\n        \n        Args:\n            raw_data: Dữ liệu thô từ API\n            \n        Returns:\n            DataFrame chứa cơ cấu lao động\n        ';B=raw_data
		if bytes([76,97,98,111,114,83,116,114,117,99,116,117,114,101]).decode()not in B or not B[bytes([76,97,98,111,114,83,116,114,117,99,116,117,114,101]).decode()]:return pd.DataFrame()
		A=pd.DataFrame(B[bytes([76,97,98,111,114,83,116,114,117,99,116,117,114,101]).decode()]);A=A.rename(columns=_LABOR_STRUCTURE_MAP);A.attrs[bytes([115,121,109,98,111,108]).decode()]=C.symbol;A.attrs[bytes([115,111,117,114,99,101]).decode()]=C.data_source;return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def overview(self,show_log=False):
		"\n        Truy xuất thông tin tổng quan của công ty.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa thông tin tổng quan công ty.\n\n        Examples:\n            >>> company = Company('ACB')\n            >>> df = company.overview()\n            >>> print(df.columns.tolist()[:5])\n            ['business_model', 'symbol', 'founded_date', 'charter_capital', 'num_employees']\n        ";B=show_log;A=self;C=A._fetch_profile(show_log=B)
		if not C:raise ValueError(f"Không tìm thấy dữ liệu profile cho mã {A.symbol}.")
		D=A._process_profile_data(C)
		if B or A.show_log:logger.info(f"Truy xuất thành công thông tin tổng quan cho {A.symbol}.")
		return D
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def officers(self,show_log=False):
		"\n        Truy xuất thông tin lãnh đạo công ty (officers).\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa thông tin lãnh đạo.\n\n        Examples:\n            >>> company = Company('ACB')\n            >>> df = company.officers()\n            >>> print(df.columns.tolist())\n            ['from_date', 'position_name_vn', 'name', 'position_en', 'position_id']\n        ";B=show_log;A=self;C=A._fetch_profile(show_log=B)
		if not C:return pd.DataFrame()
		D=A._process_leaders(C)
		if B or A.show_log:logger.info(f"Truy xuất thành công {len(D)} lãnh đạo công ty cho {A.symbol}.")
		return D
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def shareholders(self,show_log=False):
		"\n        Truy xuất thông tin cổ đông của công ty.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa thông tin cổ đông.\n\n        Examples:\n            >>> company = Company('ACB')\n            >>> df = company.shareholders()\n            >>> print(df.columns.tolist())\n            ['name', 'date', 'shares', 'ownership_ratio']\n        ";B=show_log;A=self;C=A._fetch_profile(show_log=B)
		if not C:return pd.DataFrame()
		D=A._process_shareholders(C)
		if B or A.show_log:logger.info(f"Truy xuất thành công {len(D)} cổ đông cho {A.symbol}.")
		return D
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def ownership(self,show_log=False):
		"\n        Truy xuất cơ cấu cổ đông của công ty.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa cơ cấu cổ đông.\n\n        Examples:\n            >>> company = Company('ACB')\n            >>> df = company.ownership()\n            >>> print(df.columns.tolist())\n            ['owner_type', 'ownership_ratio', 'shares', 'date']\n        ";B=show_log;A=self;C=A._fetch_profile(show_log=B)
		if not C:return pd.DataFrame()
		D=A._process_ownership(C)
		if B or A.show_log:logger.info(f"Truy xuất thành công cơ cấu cổ đông cho {A.symbol}.")
		return D
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def subsidiaries(self,show_log=False):
		"\n        Truy xuất thông tin công ty con và công ty liên kết của công ty.\n        \n        Bao gồm cả công ty con (ownership > 50%) và công ty liên kết (ownership ≤ 50%),\n        với cột 'type' để phân biệt.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa thông tin công ty con và công ty liên kết.\n\n        Examples:\n            >>> company = Company('ACB')\n            >>> df = company.subsidiaries()\n            >>> print(df.columns.tolist())\n            ['date', 'name', 'charter_capital', 'ownership_ratio', 'currency', 'type']\n        ";C=show_log;B=self;D=B._fetch_profile(show_log=C)
		if not D:return pd.DataFrame()
		A=B._process_subsidiaries(D)
		if len(A)>0:A[bytes([116,121,112,101]).decode()]=A[bytes([111,119,110,101,114,115,104,105,112,95,112,101,114,99,101,110,116]).decode()].apply(lambda x:bytes([99,195,180,110,103,32,116,121,32,99,111,110]).decode()if x>50 else bytes([99,195,180,110,103,32,116,121,32,108,105,195,170,110,32,107,225,186,191,116]).decode())
		if C or B.show_log:logger.info(f"Truy xuất thành công {len(A)} công ty con/liên kết cho {B.symbol}.")
		return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def affiliate(self,show_log=False):
		'\n        Truy xuất thông tin công ty liên kết của công ty (ownership ≤ 50%).\n        \n        Công ty liên kết được định nghĩa là các công ty có tỷ lệ sở hữu tối đa 50%.\n        Dữ liệu được lọc từ danh sách công ty con.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa thông tin công ty liên kết.\n        ';D=show_log;A=self;E=A._fetch_profile(show_log=D)
		if not E:return pd.DataFrame()
		B=A._process_subsidiaries(E)
		if len(B)==0:return B
		C=B[B[bytes([111,119,110,101,114,115,104,105,112,95,112,101,114,99,101,110,116]).decode()]<=50].copy();C[bytes([116,121,112,101]).decode()]=bytes([99,195,180,110,103,32,116,121,32,108,105,195,170,110,32,107,225,186,191,116]).decode()
		if D or A.show_log:logger.info(f"Truy xuất thành công {len(C)} công ty liên kết cho {A.symbol}.")
		return C
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def capital_history(self,show_log=False):
		"\n        Truy xuất lịch sử vốn điều lệ của công ty.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa lịch sử vốn điều lệ.\n\n        Examples:\n            >>> company = Company('ACB')\n            >>> df = company.capital_history()\n            >>> print(df.columns.tolist())\n            ['date', 'value', 'currency']\n        ";B=show_log;A=self;C=A._fetch_profile(show_log=B)
		if not C:return pd.DataFrame()
		D=A._process_charter_capital(C)
		if B or A.show_log:logger.info(f"Truy xuất thành công lịch sử vốn điều lệ cho {A.symbol}.")
		return D
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def events(self,event_type=None,page=1,page_size=10,show_log=False):
		"\n        Truy xuất danh sách sự kiện của công ty.\n\n        Args:\n            event_type: Loại sự kiện (1-5). None để lấy tất cả. \n                        1: Đại hội cổ đông, 2: Trả cổ tức, 3: Phát hành,\n                        4: Giao dịch cổ đông nội bộ, 5: Sự kiện khác.\n            page: Số trang. Mặc định 1.\n            page_size: Số lượng bản ghi mỗi trang. Mặc định 10.\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa danh sách sự kiện.\n\n        Examples:\n            >>> company = Company('ACB')\n            >>> df = company.events(event_type=2)  # Sự kiện trả cổ tức\n        ";D=show_log;C=event_type;A=self;G=f"{_STOCK_INFO_URL}/event/{A.symbol}";E={bytes([108]).decode():1,bytes([112]).decode():page,bytes([115]).decode():page_size}
		if C is not None:
			if C not in _EVENT_TYPE:raise ValueError(f"event_type không hợp lệ. Các giá trị hợp lệ: {list(_EVENT_TYPE.keys())}")
			E[bytes([101,73,68]).decode()]=C
		F=send_request(url=G,headers=A.headers,method=bytes([71,69,84]).decode(),params=E,show_log=D or A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode,auto_fetch=A.proxy_config.auto_fetch,validate_proxies=A.proxy_config.validate_proxies,prefer_speed=A.proxy_config.prefer_speed)
		if not F:return pd.DataFrame()
		B=pd.DataFrame(F);B.columns=[camel_to_snake(A)for A in B.columns];B.attrs[bytes([115,121,109,98,111,108]).decode()]=A.symbol;B.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source
		if C:B.attrs[bytes([101,118,101,110,116,95,116,121,112,101]).decode()]=_EVENT_TYPE[C]
		if D or A.show_log:logger.info(f"Truy xuất thành công {len(B)} sự kiện cho {A.symbol}.")
		return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def news(self,page=1,page_size=10,show_log=False):
		"\n        Truy xuất tin tức liên quan đến công ty.\n\n        Args:\n            page: Số trang. Mặc định 1.\n            page_size: Số lượng bản ghi mỗi trang. Mặc định 10.\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa danh sách tin tức.\n\n        Examples:\n            >>> company = Company('ACB')\n            >>> df = company.news(page=1, page_size=20)\n        ";C=show_log;A=self;E=f"{_STOCK_INFO_URL}/news/{A.symbol}";F={bytes([108]).decode():1,bytes([112]).decode():page,bytes([115]).decode():page_size};D=send_request(url=E,headers=A.headers,method=bytes([71,69,84]).decode(),params=F,show_log=C or A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode,auto_fetch=A.proxy_config.auto_fetch,validate_proxies=A.proxy_config.validate_proxies,prefer_speed=A.proxy_config.prefer_speed)
		if not D:return pd.DataFrame()
		B=pd.DataFrame(D);B.columns=[camel_to_snake(A)for A in B.columns];B.attrs[bytes([115,121,109,98,111,108]).decode()]=A.symbol;B.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source
		if C or A.show_log:logger.info(f"Truy xuất thành công {len(B)} tin tức cho {A.symbol}.")
		return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def insider_trading(self,page=1,page_size=10,show_log=False):
		"\n        Truy xuất thông tin giao dịch nội bộ.\n\n        Args:\n            page: Số trang. Mặc định 1.\n            page_size: Số lượng bản ghi mỗi trang. Mặc định 10.\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa thông tin giao dịch nội bộ.\n\n        Examples:\n            >>> company = Company('ACB')\n            >>> df = company.insider_trading()\n        ";C=show_log;A=self;E=f"{_STOCK_INFO_URL}/news/internal-trading/{A.symbol}";F={bytes([108]).decode():1,bytes([112]).decode():page,bytes([115]).decode():page_size};D=send_request(url=E,headers=A.headers,method=bytes([71,69,84]).decode(),params=F,show_log=C or A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode,auto_fetch=A.proxy_config.auto_fetch,validate_proxies=A.proxy_config.validate_proxies,prefer_speed=A.proxy_config.prefer_speed)
		if not D:return pd.DataFrame()
		B=pd.DataFrame(D);B.columns=[camel_to_snake(A)for A in B.columns];B.attrs[bytes([115,121,109,98,111,108]).decode()]=A.symbol;B.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source
		if C or A.show_log:logger.info(f"Truy xuất thành công {len(B)} bản ghi giao dịch nội bộ cho {A.symbol}.")
		return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def margin_ratio(self,show_log=False):
		"\n        Truy xuất thông tin tỷ lệ cho vay ký quỹ (margin) của mã chứng khoán tại các CTCK.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa thông tin tỷ lệ margin.\n\n        Examples:\n            >>> company = Company('ACB')\n            >>> df = company.margin_ratio()\n        ";C=show_log;A=self;E=bytes([104,116,116,112,115,58,47,47,107,98,98,117,100,100,121,119,116,115,46,107,98,115,101,99,46,99,111,109,46,118,110,47,115,97,115,47,107,98,115,118,45,115,116,111,99,107,45,100,97,116,97,45,115,116,111,114,101,47,115,116,111,99,107,47,116,114,97,100,105,110,103,45,109,97,114,103,105,110]).decode();F={bytes([99,111,100,101]).decode():A.symbol,bytes([108,97,110,103,117,97,103,101,73,68]).decode():1};D=send_request(url=E,headers=A.headers,method=bytes([71,69,84]).decode(),params=F,show_log=C or A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode)
		if not D:return pd.DataFrame()
		B=pd.DataFrame(D)
		if bytes([67,108,111,115,101,100,68,97,116,101]).decode()in B.columns:B[bytes([67,108,111,115,101,100,68,97,116,101]).decode()]=B[bytes([67,108,111,115,101,100,68,97,116,101]).decode()].apply(_parse_kbs_date).dt.normalize()
		B.attrs[bytes([115,121,109,98,111,108]).decode()]=A.symbol;B.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source
		if C or A.show_log:logger.info(f"Truy xuất thành công tỷ lệ margin cho {A.symbol} tại {len(B)} CTCK.")
		return B
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([99,111,109,112,97,110,121]).decode(),bytes([107,98,115]).decode(),Company)