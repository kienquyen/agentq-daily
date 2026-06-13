'Quote module for KB Securities (KBS) data source.'
import json
from datetime import datetime,timedelta
import pandas as pd
from vnai import agg_execution
from vnstock.core.models import TickerModel
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.lookback import get_start_date_from_lookback
from vnstock.core.utils.parser import get_asset_type
from vnstock_data.core.utils.client import ProxyConfig,send_request
from vnstock_data.core.utils.parser import convert_derivative_symbol
from vnstock_data.core.utils.transform import process_match_types
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.kbs.const import _IIS_BASE_URL,_INDEX_MAPPING,_INTERVAL_MAP,_INTRADAY_DTYPE,_INTRADAY_MAP,_OHLC_DTYPE,_OHLC_MAP
logger=get_logger(__name__)
class Quote:
	'\n    Lớp truy cập dữ liệu giá lịch sử từ KB Securities (KBS).\n    '
	def __init__(A,symbol,random_agent=False,proxy_config=None,show_log=False,proxy_mode=None,proxy_list=None):
		"\n        Khởi tạo Quote client cho KBS.\n\n        Args:\n            symbol: Mã chứng khoán (VD: 'ACB', 'VNM').\n            random_agent: Sử dụng user agent ngẫu nhiên. Mặc định False.\n            proxy_config: Cấu hình proxy. Mặc định None.\n            show_log: Hiển thị log debug. Mặc định False.\n            proxy_mode: Chế độ proxy (try, rotate, random, single). Mặc định None.\n            proxy_list: Danh sách proxy URLs. Mặc định None.\n        ";E=proxy_mode;D=show_log;C=proxy_config;B=proxy_list;A.symbol=symbol.upper();A.data_source=bytes([75,66,83]).decode();A.asset_type=get_asset_type(A.symbol)
		if A.asset_type==bytes([100,101,114,105,118,97,116,105,118,101]).decode():
			try:F=convert_derivative_symbol(A.symbol);logger.info(f"Converted derivative symbol {A.symbol} to {F} (KRX format)");A.symbol=F
			except Exception as H:logger.debug(f"Symbol conversion skipped for {A.symbol}: {H}")
		A.base_url=_IIS_BASE_URL;A.headers=get_headers(data_source=A.data_source,random_agent=random_agent);A.show_log=D;A.interval_map=_INTERVAL_MAP
		if C is None:
			I=E if E else bytes([116,114,121]).decode();G=bytes([100,105,114,101,99,116]).decode()
			if B and len(B)>0:G=bytes([112,114,111,120,121]).decode()
			A.proxy_config=ProxyConfig(proxy_mode=I,proxy_list=B,request_mode=G)
		else:A.proxy_config=C
		if not D:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
		if A.asset_type==bytes([105,110,100,101,120]).decode():
			if A.symbol not in _INDEX_MAPPING:J=bytes([44,32]).decode().join(_INDEX_MAPPING.keys());raise ValueError(f"Mã chỉ số '{A.symbol}' không được hỗ trợ bởi KBS. Các chỉ số hợp lệ: {J}")
	def _input_validation(A,start,end,interval):
		'\n        Validate input parameters.\n\n        Args:\n            start: Ngày bắt đầu (YYYY-MM-DD hoặc DD-MM-YYYY).\n            end: Ngày kết thúc (YYYY-MM-DD hoặc DD-MM-YYYY).\n            interval: Khung thời gian (1m, 5m, 15m, 30m, 1H, 1D, 1W, 1M).\n\n        Returns:\n            TickerModel instance với dữ liệu đã validate.\n\n        Raises:\n            ValueError: Nếu interval không hợp lệ.\n        ';B=interval;C=TickerModel(symbol=A.symbol,start=start,end=end,interval=B)
		if B not in A.interval_map:D=bytes([44,32]).decode().join(A.interval_map.keys());raise ValueError(f"Giá trị interval không hợp lệ: {B}. Vui lòng chọn: {D}")
		return C
	def _format_date_for_api(C,date_str):
		'\n        Chuyển đổi ngày từ YYYY-MM-DD sang DD-MM-YYYY cho API KBS.\n\n        Args:\n            date_str: Ngày dạng YYYY-MM-DD.\n\n        Returns:\n            Ngày dạng DD-MM-YYYY.\n        ';A=date_str
		try:B=datetime.strptime(A,bytes([37,89,45,37,109,45,37,100]).decode());return B.strftime(bytes([37,100,45,37,109,45,37,89]).decode())
		except ValueError:return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def history(self,start=None,end=None,interval=bytes([49,68]).decode(),to_df=True,show_log=False,count_back=None,floating=2,length=None,get_all=False):
		'\n        Tải lịch sử giá của mã chứng khoán từ KBS.\n\n        Args:\n            start: Ngày bắt đầu (YYYY-MM-DD hoặc DD-MM-YYYY). Bắt buộc nếu không có length hoặc count_back.\n            end: Ngày kết thúc (YYYY-MM-DD hoặc DD-MM-YYYY). Mặc định None (lấy đến hiện tại).\n            interval: Khung thời gian trích xuất dữ liệu. Giá trị nhận: 1m, 5m, 15m, 30m, 1H, 1D, 1W, 1M. Mặc định "1D".\n            to_df: Trả về DataFrame. Mặc định True. False để trả về JSON.\n            show_log: Hiển thị log debug.\n            count_back: Số lượng nến (bars) cần lấy.\n            floating: Số chữ số thập phân cho giá. Mặc định 2.\n            length: Khoảng thời gian phân tích (vd: \'3M\', 150, \'150\'). Nhận giá trị chuỗi (vd 3M), số ngày (int/str), hoặc số bars (vd \'100b\').\n            get_all: Lấy tất cả các cột từ API response. Mặc định False (chỉ lấy cột chuẩn hóa).\n\n        Returns:\n            DataFrame hoặc JSON string chứa dữ liệu OHLCV.\n\n        Examples:\n            >>> quote = Quote(\'ACB\')\n            >>> df = quote.history(start=\'2024-01-01\', end=\'2024-12-31\', interval=\'1D\')\n            >>> print(df.columns.tolist())\n            [\'time\', \'open\', \'high\', \'low\', \'close\', \'volume\']\n            \n            >>> # Sử dụng length để lấy dữ liệu 1 tháng gần nhất\n            >>> df_1m = quote.history(length=\'1M\', interval=\'1D\')\n            \n            >>> # Lấy 100 nến dữ liệu\n            >>> df_100 = quote.history(count_back=100, interval=\'1D\')\n            \n            >>> # Lấy dữ liệu 150 ngày\n            >>> df_150d = quote.history(length=150, interval=\'1D\')\n            \n            >>> # Lấy dữ liệu 3 tháng với kết thúc vào ngày cụ thể\n            >>> df_3m = quote.history(end=\'2024-12-31\', length=\'3M\', interval=\'1D\')\n            \n            >>> # Lấy tất cả các cột (bao gồm cả cột value)\n            >>> df_all = quote.history(length=\'1M\', interval=\'1D\', get_all=True)\n        ';Q=get_all;P=floating;O=show_log;N=to_df;I=length;G=count_back;F=interval;D=end;C=start;B=self
		if D is None:D=datetime.now().strftime(bytes([37,89,45,37,109,45,37,100]).decode())
		if C is None:
			if I is not None:
				H=str(I)
				if H.endswith(bytes([98]).decode()):G=int(H[:-1]);C=get_start_date_from_lookback(lookback_length=H,end_date=D)
				else:C=get_start_date_from_lookback(lookback_length=H,end_date=D)
			elif G is not None:
				if F==bytes([49,68]).decode():C=(datetime.strptime(D,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=G*2)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				elif F==bytes([49,72]).decode():C=(datetime.strptime(D,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=G//6)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				elif F==bytes([49,109]).decode():C=(datetime.strptime(D,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=1)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				else:C=get_start_date_from_lookback(lookback_length=bytes([49,77]).decode(),end_date=D)
			else:raise ValueError(bytes([84,104,97,109,32,115,225,187,145,32,39,115,116,97,114,116,39,32,108,195,160,32,98,225,186,175,116,32,98,117,225,187,153,99,32,110,225,186,191,117,32,107,104,195,180,110,103,32,99,117,110,103,32,99,225,186,165,112,32,39,108,101,110,103,116,104,39,32,104,111,225,186,183,99,32,39,99,111,117,110,116,95,98,97,99,107,39,46]).decode())
		if C is not None:R=B._input_validation(C,D,F)
		else:R=TickerModel(symbol=B.symbol,start=D,end=D,interval=F);R.start=C
		S=B._format_date_for_api(C);T=B._format_date_for_api(D);J=B.interval_map[F]
		if B.asset_type==bytes([105,110,100,101,120]).decode():U=f"{_IIS_BASE_URL}/index/{B.symbol}/data_{J}"
		else:U=f"{_IIS_BASE_URL}/stocks/{B.symbol}/data_{J}"
		X={bytes([115,100,97,116,101]).decode():S,bytes([101,100,97,116,101]).decode():T};K=send_request(url=U,headers=B.headers,method=bytes([71,69,84]).decode(),params=X,show_log=O or B.show_log,proxy_list=B.proxy_config.proxy_list,proxy_mode=B.proxy_config.proxy_mode,request_mode=B.proxy_config.request_mode)
		if not K:raise ValueError(f"Không tìm thấy dữ liệu cho mã {B.symbol}. Vui lòng kiểm tra lại mã chứng khoán hoặc khoảng thời gian.")
		V=f"data_{J}"
		if V not in K:raise ValueError(f"Không tìm thấy dữ liệu cho interval {F}. Vui lòng kiểm tra lại khoảng thời gian hoặc interval.")
		L=K[V]
		if not L:
			if N:return pd.DataFrame()
			else:return json.dumps([])
		if not N:return json.dumps(L)
		A=pd.DataFrame(L);M=None
		if bytes([118,97]).decode()in A.columns:
			M=A[bytes([118,97]).decode()].copy()
			if not Q:A=A.drop(columns=[bytes([118,97]).decode()])
		A=A.rename(columns=_OHLC_MAP)
		if Q and M is not None:A[bytes([118,97,108,117,101]).decode()]=M
		A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()]);A=A.sort_values(bytes([116,105,109,101]).decode()).reset_index(drop=True)
		for(E,W)in _OHLC_DTYPE.items():
			if E in A.columns:
				try:A[E]=A[E].astype(W)
				except ValueError:A[E]=A[E].astype(float).astype(W)
		if bytes([118,97,108,117,101]).decode()in A.columns:A[bytes([118,97,108,117,101]).decode()]=A[bytes([118,97,108,117,101]).decode()].astype(bytes([102,108,111,97,116,54,52]).decode())
		Y=[bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode()]
		for E in Y:
			if E in A.columns:
				if B.asset_type not in[bytes([105,110,100,101,120]).decode(),bytes([100,101,114,105,118,97,116,105,118,101]).decode()]:A[E]=A[E]/1000
				if P is not None:A[E]=A[E].round(P)
		A=A[A[bytes([116,105,109,101]).decode()]>=pd.to_datetime(C)].reset_index(drop=True)
		if G is not None:A=A.tail(G).reset_index(drop=True)
		A.attrs[bytes([115,121,109,98,111,108]).decode()]=B.symbol;A.attrs[bytes([115,111,117,114,99,101]).decode()]=B.data_source;A.attrs[bytes([105,110,116,101,114,118,97,108]).decode()]=F;A.attrs[bytes([115,116,97,114,116]).decode()]=C;A.attrs[bytes([101,110,100]).decode()]=D;A.attrs[bytes([108,101,110,103,116,104]).decode()]=I
		if O or B.show_log:logger.info(f"Truy xuất thành công {len(A)} bản ghi giá cho {B.symbol} ({F}) từ {S} đến {T}.")
		return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def intraday(self,page_size=1000,page=1,to_df=True,get_all=False,show_log=False,floating=2):
		"\n        Truy xuất dữ liệu khớp lệnh intraday (real-time matching data) của mã chứng khoán từ KBS.\n        \n        Mặc định trả về các cột chuẩn hóa (time, price, volume, match_type, id).\n        Sử dụng get_all=True để lấy tất cả các cột từ API response.\n\n        Args:\n            page_size: Số lượng bản ghi trên mỗi trang (mặc định 1000).\n                       Thường 1 ngày có thể lên đến 100K dòng (VN30 derivatives) hoặc 50-70K (cổ phiếu cơ sở).\n            page: Trang dữ liệu (mặc định 1).\n            to_df: Trả về DataFrame. Mặc định True. False để trả về JSON.\n            get_all: Lấy tất cả các cột từ API response. Mặc định False (chỉ lấy cột chuẩn hóa).\n            show_log: Hiển thị log debug.\n            floating: Số chữ số thập phân cho giá. Mặc định 2. Nếu None sẽ không làm tròn.\n\n        Returns:\n            DataFrame hoặc JSON string chứa dữ liệu khớp lệnh intraday.\n            \n            **Cột chuẩn hóa (Core columns):**\n            - time: Thời gian giao dịch (YYYY-MM-DD HH:MM:SS)\n            - price: Giá khớp\n            - volume: Khối lượng khớp\n            - match_type: Loại khớp lệnh (buy, sell, atc, ato)\n            - id: ID giao dịch (từ KBS: timestamp + price + volume)\n            \n            **Cột bổ sung (nếu get_all=True):**\n            - trading_date: Ngày giao dịch (DD/MM/YYYY)\n            - symbol: Mã chứng khoán\n            - price_change: Thay đổi giá so với lần trước\n            - accumulated_volume: Khối lượng tích lũy\n            - accumulated_value: Giá trị tích lũy\n\n        Examples:\n            >>> quote = Quote('ACB')\n            \n            >>> # Lấy 1000 bản ghi (cột chuẩn hóa)\n            >>> df = quote.intraday(page_size=1000)\n            \n            >>> # Lấy trang thứ 2\n            >>> df_page2 = quote.intraday(page=2, page_size=100)\n            \n            >>> # Lấy tất cả các cột\n            >>> df_all = quote.intraday(get_all=True)\n        ";L=floating;K=show_log;J=get_all;G=page;F=page_size;C=self
		if C.asset_type==bytes([105,110,100,101,120]).decode():raise ValueError(f"Dữ liệu intraday không được hỗ trợ cho chỉ số {C.symbol}.")
		M=f"{_IIS_BASE_URL}/trade/history/{C.symbol}";N={bytes([112,97,103,101]).decode():G,bytes([108,105,109,105,116]).decode():F};H=send_request(url=M,headers=C.headers,method=bytes([71,69,84]).decode(),params=N,show_log=K or C.show_log,proxy_list=C.proxy_config.proxy_list,proxy_mode=C.proxy_config.proxy_mode,request_mode=C.proxy_config.request_mode)
		if not H or bytes([100,97,116,97]).decode()not in H:raise ValueError(f"Không tìm thấy dữ liệu intraday cho mã {C.symbol}. Vui lòng kiểm tra lại mã chứng khoán hoặc thử lại sau.")
		I=H.get(bytes([100,97,116,97]).decode(),[])
		if not I:raise ValueError(f"Dữ liệu intraday trống cho mã {C.symbol}.")
		if not to_df:return json.dumps(I)
		A=pd.DataFrame(I);A=A.rename(columns=_INTRADAY_MAP)
		if bytes([116,105,109,101,115,116,97,109,112]).decode()in A.columns:A[bytes([116,105,109,101,115,116,97,109,112]).decode()]=A[bytes([116,105,109,101,115,116,97,109,112]).decode()].apply(lambda x:pd.to_datetime(x.rsplit(bytes([58]).decode(),1)[0])if isinstance(x,str)else x)
		for(E,O)in _INTRADAY_DTYPE.items():
			if E in A.columns:
				try:A[E]=A[E].astype(O)
				except(ValueError,TypeError):pass
		A=A.sort_values(bytes([116,105,109,101,115,116,97,109,112]).decode(),ascending=False).reset_index(drop=True);B=pd.DataFrame()
		if bytes([116,105,109,101,115,116,97,109,112]).decode()in A.columns:B[bytes([116,105,109,101]).decode()]=A[bytes([116,105,109,101,115,116,97,109,112]).decode()]
		if bytes([112,114,105,99,101]).decode()in A.columns:
			if C.asset_type not in[bytes([105,110,100,101,120]).decode(),bytes([100,101,114,105,118,97,116,105,118,101]).decode()]:B[bytes([112,114,105,99,101]).decode()]=A[bytes([112,114,105,99,101]).decode()]/1000
			else:B[bytes([112,114,105,99,101]).decode()]=A[bytes([112,114,105,99,101]).decode()]
			if L is not None:B[bytes([112,114,105,99,101]).decode()]=B[bytes([112,114,105,99,101]).decode()].round(L)
		if bytes([109,97,116,99,104,95,118,111,108,117,109,101]).decode()in A.columns:B[bytes([118,111,108,117,109,101]).decode()]=A[bytes([109,97,116,99,104,95,118,111,108,117,109,101]).decode()]
		if bytes([115,105,100,101]).decode()in A.columns:B[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=A[bytes([115,105,100,101]).decode()].fillna('')
		if bytes([109,97,116,99,104,95,116,121,112,101]).decode()in B.columns:B[bytes([116,105,109,101]).decode()]=pd.to_datetime(B[bytes([116,105,109,101]).decode()]);B=process_match_types(B,asset_type=C.asset_type,source=bytes([75,66,83]).decode());B[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=B[bytes([109,97,116,99,104,95,116,121,112,101]).decode()].str.lower()
		if bytes([116,105,109,101,115,116,97,109,112]).decode()in A.columns:B[bytes([105,100]).decode()]=A[bytes([116,105,109,101,115,116,97,109,112]).decode()].astype(str).str.replace(bytes([32]).decode(),bytes([95]).decode()).str.replace(bytes([58]).decode(),'')+bytes([95]).decode()+A[bytes([112,114,105,99,101]).decode()].astype(str).str.replace(bytes([46]).decode(),'')+bytes([95]).decode()+A[bytes([109,97,116,99,104,95,118,111,108,117,109,101]).decode()].astype(str)
		if J:
			P=[bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode(),bytes([115,121,109,98,111,108]).decode(),bytes([112,114,105,99,101,95,99,104,97,110,103,101]).decode(),bytes([97,99,99,117,109,117,108,97,116,101,100,95,118,111,108,117,109,101]).decode(),bytes([97,99,99,117,109,117,108,97,116,101,100,95,118,97,108,117,101]).decode()]
			for E in P:
				if E in A.columns:B[E]=A[E]
			D=B
		else:D=B[[bytes([116,105,109,101]).decode(),bytes([112,114,105,99,101]).decode(),bytes([118,111,108,117,109,101]).decode(),bytes([109,97,116,99,104,95,116,121,112,101]).decode(),bytes([105,100]).decode()]]
		D.attrs[bytes([115,121,109,98,111,108]).decode()]=C.symbol;D.attrs[bytes([115,111,117,114,99,101]).decode()]=C.data_source;D.attrs[bytes([112,97,103,101]).decode()]=G;D.attrs[bytes([112,97,103,101,95,115,105,122,101]).decode()]=F;D.attrs[bytes([103,101,116,95,97,108,108]).decode()]=J
		if K or C.show_log:logger.info(f"Truy xuất thành công {len(D)} bản ghi khớp lệnh intraday cho {C.symbol} (trang {G}, page_size={F}).")
		return D
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def price_depth(self,show_log=False):
		'\n        Lấy thông tin độ sâu giá (price depth/order book) của mã chứng khoán.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa thông tin độ sâu giá.\n\n        Note:\n            API endpoint này có thể cần authentication hoặc chưa được công khai.\n        ';C=show_log;A=self;E=f"{_IIS_BASE_URL}/stock/matched-by-price/{A.symbol}";D=send_request(url=E,headers=A.headers,method=bytes([71,69,84]).decode(),show_log=C or A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode,auto_fetch=A.proxy_config.auto_fetch,validate_proxies=A.proxy_config.validate_proxies,prefer_speed=A.proxy_config.prefer_speed)
		if not D:raise ValueError(f"Không tìm thấy dữ liệu độ sâu giá cho mã {A.symbol}.")
		B=pd.DataFrame(D);B.attrs[bytes([115,121,109,98,111,108]).decode()]=A.symbol;B.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source
		if C or A.show_log:logger.info(f"Truy xuất thành công dữ liệu độ sâu giá cho {A.symbol}.")
		return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def summary(self,show_log=False,to_df=True):
		'\n        Lấy thông tin tóm tắt (Snapshot) của mã chứng khoán.\n\n        Args:\n            show_log: Hiển thị log debug.\n            to_df: Trả về DataFrame. Mặc định True. False để trả về JSON (dict chuỗi).\n\n        Returns:\n            DataFrame hoặc JSON string chứa thông tin tóm tắt.\n        ';D=show_log;A=self;from vnstock_data.explorer.kbs.const import _STOCK_INFO_URL as E;F=f"{E}/info/{A.symbol}";G={bytes([108]).decode():bytes([49]).decode()};B=send_request(url=F,headers=A.headers,method=bytes([71,69,84]).decode(),params=G,show_log=D or A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode)
		if not B:raise ValueError(f"Không tìm thấy dữ liệu tóm tắt cho mã {A.symbol}.")
		if not to_df:return json.dumps(B)
		C=pd.DataFrame([B]);C.attrs[bytes([115,121,109,98,111,108]).decode()]=A.symbol;C.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source
		if D or A.show_log:logger.info(f"Truy xuất thành công dữ liệu tóm tắt cho {A.symbol}.")
		return C
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([113,117,111,116,101]).decode(),bytes([107,98,115]).decode(),Quote)