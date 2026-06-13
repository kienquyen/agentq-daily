'Trading module for KB Securities (KBS) data source.'
import json,pandas as pd
from vnai import agg_execution
from vnstock.core.utils.client import ProxyConfig,send_request
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import get_asset_type
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.kbs.const import _DERIVATIVE_ISS_URL,_DERIVATIVE_MAP,_DERIVATIVE_STANDARD_COLUMNS,_EXCHANGE_CODE_MAP,_EXCLUDED_COLUMNS,_IIS_BASE_URL,_INDEX_SUMMARY_MAP,_INDEX_SUMMARY_URL,_INDEX_SYMBOL_TO_CODE,_MATCHED_BY_PRICE_MAP,_ODD_LOT_MAP,_PRICE_BOARD_MAP,_PRICE_BOARD_STANDARD_COLUMNS,_PUT_THROUGH_HISTORY_URL,_PUT_THROUGH_MAP,_PUT_THROUGH_STANDARD_COLUMNS,_STOCK_ISS_URL,_STOCK_MATCHED_BY_PRICE_URL
logger=get_logger(__name__)
class Trading:
	'\n    Lớp truy cập dữ liệu giao dịch từ KB Securities (KBS).\n    '
	def __init__(A,symbol=None,random_agent=False,proxy_config=None,show_log=False,proxy_mode=None,proxy_list=None):
		"\n        Khởi tạo Trading client cho KBS.\n\n        Args:\n            symbol: Mã chứng khoán (VD: 'ACB', 'VNM'). Optional cho market-wide queries.\n            random_agent: Sử dụng user agent ngẫu nhiên. Mặc định False.\n            proxy_config: Cấu hình proxy. Mặc định None.\n            show_log: Hiển thị log debug. Mặc định False.\n            proxy_mode: Chế độ proxy (try, rotate, random, single). Mặc định None.\n            proxy_list: Danh sách proxy URLs. Mặc định None.\n        ";F=proxy_mode;E=show_log;D=proxy_config;C=proxy_list;B=symbol
		if isinstance(B,list):A.symbol=[A.upper()for A in B]
		else:A.symbol=B.upper()if B else None
		A.data_source=bytes([75,66,83]).decode();A.base_url=_IIS_BASE_URL;A.headers=get_headers(data_source=A.data_source,random_agent=random_agent);A.show_log=E
		if D is None:
			H=F if F else bytes([116,114,121]).decode();G=bytes([100,105,114,101,99,116]).decode()
			if C and len(C)>0:G=bytes([112,114,111,120,121]).decode()
			A.proxy_config=ProxyConfig(proxy_mode=H,proxy_list=C,request_mode=G)
		else:A.proxy_config=D
		if A.symbol:
			if isinstance(A.symbol,str):A.asset_type=get_asset_type(A.symbol)
			else:A.asset_type=None
		if not E:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def price_history(self,start=None,end=None,limit=1000,page=1,show_log=False):
		'\n        Truy xuất dữ liệu lịch sử giá kết hợp giao dịch khớp lệnh/thoả thuận (OHLCV + Stats)\n        Hàm này mô phỏng sát nhất với cấu trúc price_history truyền thống của VCI.\n        \n        Args:\n            start: Ngày bắt đầu (YYYY-MM-DD).\n            end: Ngày kết thúc (YYYY-MM-DD).\n            limit: Số bản ghi trả về tối đa.\n            page: Phân trang (offset/page index).\n            \n        Returns:\n            DataFrame dữ liệu lịch sử.\n        ';D=start;B=self
		if not B.symbol:raise ValueError(bytes([83,121,109,98,111,108,32,105,115,32,114,101,113,117,105,114,101,100,32,102,111,114,32,112,114,105,99,101,95,104,105,115,116,111,114,121,32,109,101,116,104,111,100,46]).decode())
		F=f"{_IIS_BASE_URL}/{B.symbol}/historical-quotes";C={bytes([108,105,109,105,116]).decode():limit,bytes([111,102,102,115,101,116]).decode():page}
		if D and end:C[bytes([115,116,97,114,116,68,97,116,101]).decode()]=D;C[bytes([101,110,100,68,97,116,101]).decode()]=end
		E=send_request(url=F,headers=B.headers,method=bytes([71,69,84]).decode(),params=C,show_log=show_log or B.show_log,proxy_list=B.proxy_config.proxy_list,proxy_mode=B.proxy_config.proxy_mode,request_mode=B.proxy_config.request_mode)
		if not E:return pd.DataFrame()
		A=pd.DataFrame(E)
		if A.empty:return A
		G={bytes([84,114,97,100,105,110,103,68,97,116,101]).decode():bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode(),bytes([83,116,111,99,107,67,111,100,101]).decode():bytes([115,121,109,98,111,108]).decode(),bytes([67,104,97,110,103,101]).decode():bytes([112,114,105,99,101,95,99,104,97,110,103,101]).decode(),bytes([80,101,114,67,104,97,110,103,101]).decode():bytes([112,101,114,99,101,110,116,95,112,114,105,99,101,95,99,104,97,110,103,101]).decode(),bytes([67,108,111,115,101,80,114,105,99,101]).decode():bytes([99,108,111,115,101]).decode(),bytes([77,84,95,84,111,116,97,108,86,111,108]).decode():bytes([109,97,116,99,104,101,100,95,118,111,108,117,109,101]).decode(),bytes([77,84,95,84,111,116,97,108,86,97,108]).decode():bytes([109,97,116,99,104,101,100,95,118,97,108,117,101]).decode(),bytes([80,84,95,84,111,116,97,108,86,111,108]).decode():bytes([100,101,97,108,95,118,111,108,117,109,101]).decode(),bytes([80,84,95,84,111,116,97,108,86,97,108]).decode():bytes([100,101,97,108,95,118,97,108,117,101]).decode(),bytes([65,118,114,80,114,105,99,101]).decode():bytes([97,118,101,114,97,103,101,95,112,114,105,99,101]).decode(),bytes([72,105,103,104,101,115,116,80,114,105,99,101]).decode():bytes([104,105,103,104]).decode(),bytes([76,111,119,101,115,116,80,114,105,99,101]).decode():bytes([108,111,119]).decode(),bytes([84,111,116,97,108,66,117,121,84,114,97,100,101]).decode():bytes([116,111,116,97,108,95,98,117,121,95,116,114,97,100,101]).decode(),bytes([84,111,116,97,108,66,117,121,86,111,108]).decode():bytes([116,111,116,97,108,95,98,117,121,95,116,114,97,100,101,95,118,111,108,117,109,101]).decode(),bytes([84,111,116,97,108,83,101,108,108,84,114,97,100,101]).decode():bytes([116,111,116,97,108,95,115,101,108,108,95,116,114,97,100,101]).decode(),bytes([84,111,116,97,108,83,101,108,108,86,111,108]).decode():bytes([116,111,116,97,108,95,115,101,108,108,95,116,114,97,100,101,95,118,111,108,117,109,101]).decode(),bytes([67,101,105,108,105,110,103,80,114,105,99,101]).decode():bytes([99,101,105,108,105,110,103,95,112,114,105,99,101]).decode(),bytes([70,108,111,111,114,80,114,105,99,101]).decode():bytes([102,108,111,111,114,95,112,114,105,99,101]).decode()};A=A.rename(columns=G)
		if bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode()in A.columns:A[bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode()]=pd.to_datetime(A[bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode()],format=bytes([37,100,47,37,109,47,37,89]).decode(),errors=bytes([99,111,101,114,99,101]).decode())
		if bytes([109,97,116,99,104,101,100,95,118,111,108,117,109,101]).decode()in A.columns and bytes([100,101,97,108,95,118,111,108,117,109,101]).decode()in A.columns:A[bytes([116,111,116,97,108,95,118,111,108,117,109,101]).decode()]=A[bytes([109,97,116,99,104,101,100,95,118,111,108,117,109,101]).decode()]+A[bytes([100,101,97,108,95,118,111,108,117,109,101]).decode()]
		if bytes([109,97,116,99,104,101,100,95,118,97,108,117,101]).decode()in A.columns and bytes([100,101,97,108,95,118,97,108,117,101]).decode()in A.columns:A[bytes([116,111,116,97,108,95,118,97,108,117,101]).decode()]=A[bytes([109,97,116,99,104,101,100,95,118,97,108,117,101]).decode()]+A[bytes([100,101,97,108,95,118,97,108,117,101]).decode()]
		if bytes([115,121,109,98,111,108]).decode()in A.columns:A=A.drop(columns=[bytes([115,121,109,98,111,108]).decode()])
		A.attrs[bytes([115,121,109,98,111,108]).decode()]=B.symbol;A.attrs[bytes([115,111,117,114,99,101]).decode()]=B.data_source;return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def order_stats(self,start=None,end=None,limit=1000,page=1,show_log=False):
		'\n        Khởi tạo alias cho thống kê cung cầu (Order Statistics).\n        Vì KBS đã trả về thông tin Tổng Lượng Mua/Bán trong dữ liệu Historical Quotes,\n        ta uỷ quyền qua price_history.\n        ';A=self.price_history(start=start,end=end,limit=limit,page=page,show_log=show_log)
		if A.empty:return A
		B=[bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode(),bytes([99,108,111,115,101]).decode(),bytes([97,118,101,114,97,103,101,95,112,114,105,99,101]).decode(),bytes([112,114,105,99,101,95,99,104,97,110,103,101]).decode(),bytes([109,97,116,99,104,101,100,95,118,111,108,117,109,101]).decode(),bytes([116,111,116,97,108,95,98,117,121,95,116,114,97,100,101,95,118,111,108,117,109,101]).decode(),bytes([116,111,116,97,108,95,115,101,108,108,95,116,114,97,100,101,95,118,111,108,117,109,101]).decode(),bytes([116,111,116,97,108,95,98,117,121,95,116,114,97,100,101]).decode(),bytes([116,111,116,97,108,95,115,101,108,108,95,116,114,97,100,101]).decode()];C=[B for B in B if B in A.columns];A=A[C];A.attrs[bytes([99,97,116,101,103,111,114,121]).decode()]=bytes([111,114,100,101,114,95,115,116,97,116,115]).decode();A.attrs[bytes([115,121,109,98,111,108]).decode()]=self.symbol;return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def foreign_trade(self,top=10,show_log=False):
		'\n        Lấy top Giao dịch của nhà đầu tư nước ngoài (Realtime Ranking).\n        API này trả về top các mã dựa trên ranking chứ không truy xuất theo từng mã (KBS không cấp).\n        Do đó nếu self.symbol đã gán, API này sẽ lờ đi và dùng `top`.\n        ';A=self;D=f"{_IIS_BASE_URL}/rtranking/foreignTotal";E={bytes([116,111,112]).decode():top};C=send_request(url=D,headers=A.headers,method=bytes([71,69,84]).decode(),params=E,show_log=show_log or A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode)
		if not C:return pd.DataFrame()
		B=pd.DataFrame(C);F={bytes([83,66]).decode():bytes([115,121,109,98,111,108]).decode(),bytes([69,88]).decode():bytes([101,120,99,104,97,110,103,101]).decode(),bytes([82,69]).decode():bytes([114,101,102,101,114,101,110,99,101,95,112,114,105,99,101]).decode(),bytes([67,76]).decode():bytes([99,101,105,108,105,110,103,95,112,114,105,99,101]).decode(),bytes([70,76]).decode():bytes([102,108,111,111,114,95,112,114,105,99,101]).decode(),bytes([67,80]).decode():bytes([109,97,116,99,104,95,112,114,105,99,101]).decode(),bytes([70,66]).decode():bytes([102,111,114,101,105,103,110,95,98,117,121,95,118,111,108,117,109,101]).decode(),bytes([70,83]).decode():bytes([102,111,114,101,105,103,110,95,115,101,108,108,95,118,111,108,117,109,101]).decode(),bytes([70,84]).decode():bytes([102,111,114,101,105,103,110,95,116,111,116,97,108,95,118,111,108,117,109,101]).decode()};B=B.rename(columns=F);B.attrs[bytes([99,97,116,101,103,111,114,121]).decode()]=bytes([102,111,114,101,105,103,110,95,116,114,97,100,101]).decode();B.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source;return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def matched_by_price(self,show_log=False):
		"\n        Truy xuất dữ liệu khớp lệnh theo từng mức giá.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa dữ liệu khớp lệnh theo giá với các cột chuẩn hóa.\n\n        Examples:\n            >>> trading = Trading('ACB')\n            >>> df = trading.matched_by_price()\n\n        Raises:\n            ValueError: Nếu không có symbol được chỉ định.\n        ";C=show_log;A=self
		if not A.symbol:raise ValueError(bytes([83,121,109,98,111,108,32,105,115,32,114,101,113,117,105,114,101,100,32,102,111,114,32,109,97,116,99,104,101,100,95,98,121,95,112,114,105,99,101,32,109,101,116,104,111,100,46]).decode())
		E=f"{_STOCK_MATCHED_BY_PRICE_URL}/{A.symbol}";D=send_request(url=E,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=C or A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode)
		if not D:return pd.DataFrame()
		B=pd.DataFrame(D);B=B.rename(columns=_MATCHED_BY_PRICE_MAP);B.attrs[bytes([115,121,109,98,111,108]).decode()]=A.symbol;B.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source
		if C or A.show_log:logger.info(f"Truy xuất thành công dữ liệu khớp lệnh theo giá cho {A.symbol}.")
		return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def index_summary(self,show_log=False):
		'\n        Truy xuất thông tin tóm tắt (Snapshot) cho các chỉ số thị trường.\n\n        Chấp nhận mã symbol (VNINDEX, VN30, ...) và tự động mapping sang mã KBS (HOSE, 30, ...).\n        Nếu không có symbol, mặc định lấy toàn bộ các chỉ số chính.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa thông tin tóm tắt chỉ số với các cột chuẩn hóa.\n        ';F=show_log;B=self;import requests as J;K=_INDEX_SUMMARY_URL
		if B.symbol:
			E=_INDEX_SYMBOL_TO_CODE.get(B.symbol)
			if not E:E=B.symbol
			G={bytes([99,111,100,101]).decode():E}
		else:G={bytes([99,111,100,101]).decode():bytes([72,79,83,69,44,51,48,44,49,48,48,44,72,78,88,44,72,78,88,51,48,44,85,80,67,79,77]).decode()}
		try:
			H=B.headers.copy();H.update({bytes([65,99,99,101,112,116,45,76,97,110,103,117,97,103,101]).decode():bytes([101,110,45,85,83,44,101,110,59,113,61,48,46,57,44,118,105,59,113,61,48,46,56]).decode(),bytes([67,111,110,110,101,99,116,105,111,110]).decode():bytes([107,101,101,112,45,97,108,105,118,101]).decode(),bytes([67,111,110,116,101,110,116,45,84,121,112,101]).decode():bytes([97,112,112,108,105,99,97,116,105,111,110,47,106,115,111,110]).decode(),bytes([68,78,84]).decode():bytes([49]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,68,101,115,116]).decode():bytes([101,109,112,116,121]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,77,111,100,101]).decode():bytes([99,111,114,115]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,83,105,116,101]).decode():bytes([115,97,109,101,45,111,114,105,103,105,110]).decode(),bytes([120,45,108,97,110,103]).decode():bytes([118,105]).decode()});I=J.post(K,headers=H,data=json.dumps(G),timeout=30)
			if I.status_code in[200,201]:D=I.json()
			else:return pd.DataFrame()
		except Exception as L:
			if F or B.show_log:logger.error(f"Failed to fetch index summary data: {L!s}")
			return pd.DataFrame()
		if not D or not isinstance(D,list):return pd.DataFrame()
		A=pd.DataFrame(D);A=A.rename(columns=_INDEX_SUMMARY_MAP);M={B:A for(A,B)in _INDEX_SYMBOL_TO_CODE.items()}
		if bytes([77,67]).decode()in D[0]:A[bytes([115,121,109,98,111,108]).decode()]=A[bytes([77,67]).decode()].map(lambda x:M.get(str(x),x))
		N=[bytes([99,108,111,115,101,95,112,114,105,99,101]).decode(),bytes([112,114,105,99,101,95,99,104,97,110,103,101]).decode(),bytes([111,112,101,110,95,112,114,105,99,101]).decode(),bytes([104,105,103,104,95,112,114,105,99,101]).decode(),bytes([108,111,119,95,112,114,105,99,101]).decode(),bytes([114,101,102,101,114,101,110,99,101,95,112,114,105,99,101]).decode(),bytes([112,114,101,118,105,111,117,115,95,99,108,111,115,101]).decode()]
		for C in N:
			if C in A.columns:A[C]=pd.to_numeric(A[C],errors=bytes([99,111,101,114,99,101]).decode())
		O=[bytes([97,99,99,117,109,117,108,97,116,101,100,95,118,111,108,117,109,101]).decode(),bytes([97,99,99,117,109,117,108,97,116,101,100,95,118,97,108,117,101]).decode(),bytes([116,111,116,97,108,95,118,111,108,117,109,101]).decode(),bytes([112,117,116,95,116,104,114,111,117,103,104,95,118,97,108,117,101]).decode(),bytes([112,117,116,95,116,104,114,111,117,103,104,95,118,111,108,117,109,101]).decode(),bytes([97,100,118,97,110,99,101,115]).decode(),bytes([100,101,99,108,105,110,101,115]).decode(),bytes([110,111,95,99,104,97,110,103,101]).decode()]
		for C in O:
			if C in A.columns:A[C]=pd.to_numeric(A[C],errors=bytes([99,111,101,114,99,101]).decode())
		if bytes([116,105,109,101,115,116,97,109,112]).decode()in A.columns:A[bytes([116,105,109,101,115,116,97,109,112]).decode()]=pd.to_datetime(A[bytes([116,105,109,101,115,116,97,109,112]).decode()],unit=bytes([109,115]).decode(),errors=bytes([99,111,101,114,99,101]).decode())
		A.attrs[bytes([115,111,117,114,99,101]).decode()]=B.data_source
		if B.symbol:A.attrs[bytes([115,121,109,98,111,108]).decode()]=B.symbol
		if F or B.show_log:logger.info(f"Truy xuất thành công tóm tắt cho {len(A)} chỉ số.")
		return A
	def _fetch_stock_board(D,symbols_list,show_log=False):
		'\n        Fetch stock board (lô chẵn) data from /stock/iss endpoint.\n        \n        Args:\n            symbols_list: List of stock symbols.\n            show_log: Show debug logs.\n            \n        Returns:\n            DataFrame with stock board data.\n        ';B=symbols_list;import requests as G
		if isinstance(B,str):B=[B]
		H=_STOCK_ISS_URL;I={bytes([99,111,100,101]).decode():bytes([44]).decode().join(B)}
		try:
			E=D.headers.copy();E.update({bytes([65,99,99,101,112,116,45,76,97,110,103,117,97,103,101]).decode():bytes([101,110,45,85,83,44,101,110,59,113,61,48,46,57,44,118,105,59,113,61,48,46,56]).decode(),bytes([67,111,110,110,101,99,116,105,111,110]).decode():bytes([107,101,101,112,45,97,108,105,118,101]).decode(),bytes([67,111,110,116,101,110,116,45,84,121,112,101]).decode():bytes([97,112,112,108,105,99,97,116,105,111,110,47,106,115,111,110]).decode(),bytes([68,78,84]).decode():bytes([49]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,68,101,115,116]).decode():bytes([101,109,112,116,121]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,77,111,100,101]).decode():bytes([99,111,114,115]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,83,105,116,101]).decode():bytes([115,97,109,101,45,111,114,105,103,105,110]).decode(),bytes([120,45,108,97,110,103]).decode():bytes([118,105]).decode()});F=G.post(H,headers=E,data=json.dumps(I),timeout=30)
			if F.status_code in[200,201]:C=F.json()
			else:return pd.DataFrame()
		except Exception as J:
			if show_log or D.show_log:logger.error(f"Failed to fetch stock board data: {J!s}")
			return pd.DataFrame()
		if not C or not isinstance(C,list):return pd.DataFrame()
		A=pd.DataFrame(C);A=A.rename(columns=_PRICE_BOARD_MAP)
		if bytes([116,105,109,101,115,116,97,109,112]).decode()in A.columns:A[bytes([116,105,109,101,115,116,97,109,112]).decode()]=pd.to_datetime(A[bytes([116,105,109,101,115,116,97,109,112]).decode()],unit=bytes([109,115]).decode(),errors=bytes([99,111,101,114,99,101]).decode())
		return A
	def _fetch_put_through_board(C,symbols_list,show_log=False):
		"\n        Fetch put-through board (thỏa thuận) data.\n        \n        Note: The put-through ISS endpoint doesn't exist. Use put_through() method instead\n        which fetches from /put-through/trade/history endpoint and returns all put-through data.\n        \n        Args:\n            symbols_list: List of stock symbols.\n            show_log: Show debug logs.\n            \n        Returns:\n            DataFrame with put-through board data filtered by symbols.\n        ";B=symbols_list;A=C.put_through(exchange=bytes([72,79,83,69]).decode(),page=1,show_log=show_log)
		if isinstance(B,str):B=[B]
		A=A.loc[:,~A.columns.duplicated(keep=bytes([102,105,114,115,116]).decode())]
		if bytes([115,121,109,98,111,108]).decode()in A.columns and len(A)>0:A=A[A[bytes([115,121,109,98,111,108]).decode()].isin(B)].reset_index(drop=True)
		return A
	def _fetch_derivative_board(D,symbols_list,show_log=False):
		'\n        Fetch derivative board data.\n        \n        Args:\n            symbols_list: List of derivative symbols.\n            show_log: Show debug logs.\n            \n        Returns:\n            DataFrame with derivative board data.\n        ';C=symbols_list;import requests as G
		if isinstance(C,str):C=[C]
		H=_DERIVATIVE_ISS_URL;I={bytes([99,111,100,101]).decode():bytes([44]).decode().join(C)}
		try:
			E=D.headers.copy();E.update({bytes([65,99,99,101,112,116,45,76,97,110,103,117,97,103,101]).decode():bytes([101,110,45,85,83,44,101,110,59,113,61,48,46,57,44,118,105,59,113,61,48,46,56]).decode(),bytes([67,111,110,110,101,99,116,105,111,110]).decode():bytes([107,101,101,112,45,97,108,105,118,101]).decode(),bytes([67,111,110,116,101,110,116,45,84,121,112,101]).decode():bytes([97,112,112,108,105,99,97,116,105,111,110,47,106,115,111,110]).decode(),bytes([68,78,84]).decode():bytes([49]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,68,101,115,116]).decode():bytes([101,109,112,116,121]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,77,111,100,101]).decode():bytes([99,111,114,115]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,83,105,116,101]).decode():bytes([115,97,109,101,45,111,114,105,103,105,110]).decode(),bytes([120,45,108,97,110,103]).decode():bytes([118,105]).decode()});F=G.post(H,headers=E,data=json.dumps(I),timeout=30)
			if F.status_code in[200,201]:A=F.json()
			else:return pd.DataFrame()
		except Exception as J:
			if show_log or D.show_log:logger.error(f"Failed to fetch derivative board data: {J!s}")
			return pd.DataFrame()
		if not A:return pd.DataFrame()
		if isinstance(A,dict)and bytes([100,97,116,97]).decode()in A:A=A[bytes([100,97,116,97]).decode()]
		if not isinstance(A,list):return pd.DataFrame()
		B=pd.DataFrame(A);B=B.rename(columns=_DERIVATIVE_MAP)
		if bytes([116,105,109,101]).decode()in B.columns:B[bytes([116,105,109,101]).decode()]=pd.to_datetime(B[bytes([116,105,109,101]).decode()],unit=bytes([109,115]).decode(),errors=bytes([99,111,101,114,99,101]).decode())
		return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def price_board(self,symbols_list,board=bytes([115,116,111,99,107]).decode(),exchange=bytes([72,79,83,69]).decode(),show_log=False,get_all=False):
		"\n        Fetch real-time price board for a list of symbols.\n\n        Unified interface for fetching price data from various board types:\n        - stock: Standard board (even lots)\n        - odd_lot: Odd-lot trades\n        - put_through: Negotiated/Put-through trades\n        - derivatives: Index futures\n\n        Args:\n            symbols_list (List[str]): List of symbols (e.g., ['ACB', 'VNM']).\n            board (str): Board type ('stock', 'odd_lot', 'put_through', 'derivatives').\n            exchange (str): Exchange ('HOSE', 'HNX', 'UPCOM').\n            show_log (bool): Display debug logs.\n            get_all (bool): If True, return all raw columns. Otherwise, standard columns.\n        ";R=get_all;H=board;E=show_log;C=self;B=symbols_list
		if not B:raise ValueError(bytes([115,121,109,98,111,108,115,95,108,105,115,116,32,107,104,195,180,110,103,32,196,145,198,176,225,187,163,99,32,196,145,225,187,131,32,116,114,225,187,145,110,103,46]).decode())
		if isinstance(B,str):B=[B]
		S=[bytes([115,116,111,99,107]).decode(),bytes([111,100,100,95,108,111,116]).decode(),bytes([112,117,116,95,116,104,114,111,117,103,104]).decode(),bytes([100,101,114,105,118,97,116,105,118,101,115]).decode()]
		if H not in S:raise ValueError(f"board không hợp lệ. Các giá trị hợp lệ: {S}")
		B=[A.upper()for A in B];F=[]
		if H==bytes([115,116,111,99,107]).decode():
			from vnstock.core.utils.parser import get_asset_type as U;from vnstock_data.core.utils.parser import safe_convert_derivative_symbol as N;I=[];J=[];K=[]
			for L in B:
				T=U(L)
				if T==bytes([100,101,114,105,118,97,116,105,118,101]).decode():J.append(L)
				elif T==bytes([105,110,100,101,120]).decode():K.append(L)
				else:I.append(L)
			if I:V=C._fetch_stock_board(I,E);F.append((V,_PRICE_BOARD_STANDARD_COLUMNS))
			if J:O=[N(A)for A in J];P=C._fetch_derivative_board(O,E);F.append((P,_DERIVATIVE_STANDARD_COLUMNS))
			if K:
				D=C.index_summary(show_log=E)
				if not D.empty and bytes([115,121,109,98,111,108]).decode()in D.columns:W=[A.upper()for A in K];D=D[D[bytes([115,121,109,98,111,108]).decode()].isin(W)].reset_index(drop=True)
				if not D.empty:F.append((D,list(D.columns)))
			G=[]
			if I:G.append(bytes([99,198,161,32,115,225,187,159]).decode())
			if J:G.append(bytes([112,104,195,161,105,32,115,105,110,104]).decode())
			if K:G.append(bytes([99,104,225,187,137,32,115,225,187,145]).decode())
			M=bytes([104,225,187,151,110,32,104,225,187,163,112,32,40]).decode()+bytes([32,38,32]).decode().join(G)+bytes([41]).decode()if len(G)>1 else G[0]if G else bytes([108,195,180,32,99,104,225,186,181,110]).decode()
		elif H==bytes([111,100,100,95,108,111,116]).decode():X=C.odd_lot(symbols_list=B,exchange=exchange,show_log=E);F.append((X,_PRICE_BOARD_STANDARD_COLUMNS));M=bytes([108,195,180,32,108,225,186,187]).decode()
		elif H==bytes([100,101,114,105,118,97,116,105,118,101,115]).decode():from vnstock_data.core.utils.parser import safe_convert_derivative_symbol as N;O=[N(A)for A in B];P=C._fetch_derivative_board(O,E);F.append((P,_DERIVATIVE_STANDARD_COLUMNS));M=bytes([112,104,195,161,105,32,115,105,110,104]).decode()
		else:Y=C._fetch_put_through_board(B,E);F.append((Y,_PUT_THROUGH_STANDARD_COLUMNS));M=bytes([116,104,225,187,143,97,32,116,104,117,225,186,173,110]).decode()
		Q=[]
		for(A,Z)in F:
			if len(A)>0:
				if not R:a=[B for B in Z if B in A.columns];A=A[a]
				else:b=[A for A in A.columns if A not in _EXCLUDED_COLUMNS];A=A[b]
				Q.append(A)
		if Q:
			A=pd.concat(Q,ignore_index=True)
			if bytes([101,120,99,104,97,110,103,101]).decode()in A.columns:A[bytes([101,120,99,104,97,110,103,101]).decode()]=A[bytes([101,120,99,104,97,110,103,101]).decode()].map(lambda x:_EXCHANGE_CODE_MAP.get(x,x)if pd.notna(x)else x)
		else:A=pd.DataFrame()
		A.attrs[bytes([115,121,109,98,111,108,115]).decode()]=B;A.attrs[bytes([98,111,97,114,100]).decode()]=H;A.attrs[bytes([115,111,117,114,99,101]).decode()]=C.data_source;A.attrs[bytes([103,101,116,95,97,108,108]).decode()]=R
		if E or C.show_log:logger.info(f"Truy xuất thành công bảng giá {M} cho {len(B)} mã chứng khoán.")
		return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def odd_lot(self,symbols_list=None,exchange=bytes([72,79,83,69]).decode(),show_log=False):
		"\n        Truy xuất dữ liệu giao dịch lô lẻ (odd-lot) cho danh sách mã chứng khoán.\n\n        Note: Phương thức này là alias cho price_board() với data_type='odd_lot'.\n        Khuyến nghị sử dụng price_board(symbols_list, data_type='odd_lot') thay vì phương thức này.\n\n        Args:\n            symbols_list: Danh sách mã chứng khoán. Nếu None, truy xuất toàn bộ sàn.\n            exchange: Sàn giao dịch ('HOSE', 'HNX', 'UPCOM'). Mặc định 'HOSE'.\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa dữ liệu giao dịch lô lẻ với các cột chuẩn hóa.\n\n        Examples:\n            >>> trading = Trading()\n            >>> df = trading.odd_lot(symbols_list=['AAA', 'AAM'])\n            >>> df_all = trading.odd_lot(exchange='HOSE')\n\n        Raises:\n            ValueError: Nếu exchange không hợp lệ.\n        ";F=show_log;D=exchange;C=self;A=symbols_list;G=[bytes([72,79,83,69]).decode(),bytes([72,78,88]).decode(),bytes([85,80,67,79,77]).decode()]
		if D not in G:raise ValueError(f"Exchange không hợp lệ. Các giá trị hợp lệ: {G}")
		K=f"{_IIS_BASE_URL}/odd-lot/iss"
		if A:
			if isinstance(A,str):A=[A]
			A=[A.upper()for A in A];H={bytes([99,111,100,101]).decode():bytes([44]).decode().join(A)}
		else:H={bytes([101,120,99,104,97,110,103,101]).decode():D}
		import requests as L
		try:
			I=C.headers.copy();I.update({bytes([65,99,99,101,112,116,45,76,97,110,103,117,97,103,101]).decode():bytes([101,110,45,85,83,44,101,110,59,113,61,48,46,57,44,118,105,59,113,61,48,46,56]).decode(),bytes([67,111,110,110,101,99,116,105,111,110]).decode():bytes([107,101,101,112,45,97,108,105,118,101]).decode(),bytes([67,111,110,116,101,110,116,45,84,121,112,101]).decode():bytes([97,112,112,108,105,99,97,116,105,111,110,47,106,115,111,110]).decode(),bytes([68,78,84]).decode():bytes([49]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,68,101,115,116]).decode():bytes([101,109,112,116,121]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,77,111,100,101]).decode():bytes([99,111,114,115]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,83,105,116,101]).decode():bytes([115,97,109,101,45,111,114,105,103,105,110]).decode(),bytes([120,45,108,97,110,103]).decode():bytes([118,105]).decode()});J=L.post(K,headers=I,data=json.dumps(H),timeout=30)
			if J.status_code in[200,201]:E=J.json()
			else:return pd.DataFrame()
		except Exception as M:
			if F or C.show_log:logger.error(f"Failed to fetch odd_lot data: {M!s}")
			return pd.DataFrame()
		if not E:return pd.DataFrame()
		if not isinstance(E,list):return pd.DataFrame()
		B=pd.DataFrame(E);B=B.rename(columns=_ODD_LOT_MAP)
		if bytes([116,105,109,101,115,116,97,109,112]).decode()in B.columns:B[bytes([116,105,109,101,115,116,97,109,112]).decode()]=pd.to_datetime(B[bytes([116,105,109,101,115,116,97,109,112]).decode()],errors=bytes([99,111,101,114,99,101]).decode())
		if A:B.attrs[bytes([115,121,109,98,111,108,115]).decode()]=A
		B.attrs[bytes([101,120,99,104,97,110,103,101]).decode()]=D;B.attrs[bytes([115,111,117,114,99,101]).decode()]=C.data_source
		if F or C.show_log:
			if A:logger.info(f"Truy xuất thành công {len(B)} bản ghi giao dịch lô lẻ cho {len(A)} mã chứng khoán.")
			else:logger.info(f"Truy xuất thành công {len(B)} bản ghi giao dịch lô lẻ cho sàn {D}.")
		return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def put_through(self,exchange=bytes([72,79,83,69]).decode(),symbol=None,page=1,page_size=1000,show_log=False):
		"\n        Truy xuất dữ liệu giao dịch thỏa thuận (put-through) theo sàn.\n\n        Args:\n            exchange: Sàn giao dịch ('HOSE', 'HNX', 'UPCOM'). Mặc định 'HOSE'.\n            symbol: Mã chứng khoán để lọc (VD: 'ACB'). Nếu None, lấy toàn bộ sàn.\n            page: Số trang. Mặc định 1.\n            page_size: Số lượng bản ghi mỗi trang. Mặc định 1000.\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa dữ liệu giao dịch thỏa thuận với các cột chuẩn hóa.\n\n        Examples:\n            >>> trading = Trading()\n            >>> df = trading.put_through(exchange='HOSE', page=1)\n\n        Raises:\n            ValueError: Nếu exchange không hợp lệ.\n        ";E=show_log;D=exchange;B=self;F=[bytes([72,79,83,69]).decode(),bytes([72,78,88]).decode(),bytes([85,80,67,79,77]).decode()]
		if D not in F:raise ValueError(f"Exchange không hợp lệ. Các giá trị hợp lệ: {F}")
		H=f"{_PUT_THROUGH_HISTORY_URL}/{D}";I={bytes([112,97,103,101]).decode():page,bytes([112,97,103,101,83,105,122,101]).decode():page_size};C=send_request(url=H,headers=B.headers,method=bytes([71,69,84]).decode(),params=I,show_log=E or B.show_log,proxy_list=B.proxy_config.proxy_list,proxy_mode=B.proxy_config.proxy_mode,request_mode=B.proxy_config.request_mode)
		if not C:return pd.DataFrame()
		if isinstance(C,dict)and bytes([100,97,116,97]).decode()in C:C=C[bytes([100,97,116,97]).decode()]
		if not C or not isinstance(C,list):return pd.DataFrame()
		A=pd.DataFrame(C);A=A.rename(columns=_PUT_THROUGH_MAP);A=A.loc[:,~A.columns.duplicated()]
		if bytes([116,105,109,101,115,116,97,109,112]).decode()in A.columns:A[bytes([116,105,109,101,115,116,97,109,112]).decode()]=pd.to_datetime(A[bytes([116,105,109,101,115,116,97,109,112]).decode()],errors=bytes([99,111,101,114,99,101]).decode())
		G=symbol or B.symbol
		if G and bytes([115,121,109,98,111,108]).decode()in A.columns:A=A[A[bytes([115,121,109,98,111,108]).decode()]==G.upper()].reset_index(drop=True)
		A.attrs[bytes([101,120,99,104,97,110,103,101]).decode()]=D;A.attrs[bytes([115,111,117,114,99,101]).decode()]=B.data_source;A.attrs[bytes([112,97,103,101]).decode()]=page
		if E or B.show_log:logger.info(f"Truy xuất thành công {len(A)} bản ghi giao dịch thỏa thuận cho sàn {D}.")
		return A
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([116,114,97,100,105,110,103]).decode(),bytes([107,98,115]).decode(),Trading)