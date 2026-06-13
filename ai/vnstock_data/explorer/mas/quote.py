'History module for MAS.'
from datetime import datetime,timedelta
import pandas as pd
from vnai import agg_execution
from vnstock.core.models import TickerModel
from vnstock.core.utils.interval import normalize_interval
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.lookback import get_start_date_from_lookback
from vnstock.core.utils.market import trading_hours
from vnstock.core.utils.parser import get_asset_type
from vnstock_data.core.utils.client import ProxyConfig,send_request
from vnstock_data.core.utils.transform import intraday_to_df,ohlc_to_df
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.mas.const import _CHART_URL,_INDEX_MAPPING,_INTERVAL_MAP,_INTRADAY_DTYPE,_INTRADAY_MAP,_OHLC_DTYPE,_OHLC_MAP,_PRICE_DEPTH_MAP,_RESAMPLE_MAP
logger=get_logger(__name__)
class Quote:
	'\n    Cấu hình truy cập dữ liệu lịch sử giá chứng khoán từ MAS.\n    \n    Hỗ trợ các tính năng proxy nâng cao:\n    - auto_fetch: Tự động lấy proxy từ proxyscrape API\n    - validate_proxies: Kiểm tra tính hợp lệ của proxy\n    - prefer_speed: Ưu tiên proxy có tốc độ tốt nhất\n    '
	def __init__(A,symbol,random_agent=False,proxy_config=None,show_log=True,proxy_mode=None,proxy_list=None):
		E=proxy_mode;D=show_log;C=proxy_config;B=proxy_list;A.symbol=symbol.upper();A.data_source=bytes([77,65,83]).decode();A._history=None;A.asset_type=get_asset_type(A.symbol);A.base_url=_CHART_URL;A.headers=get_headers(data_source=A.data_source,random_agent=random_agent);A.interval_map=_INTERVAL_MAP;A.show_log=D
		if C is None:
			G=E if E else bytes([116,114,121]).decode();F=bytes([100,105,114,101,99,116]).decode()
			if B and len(B)>0:F=bytes([112,114,111,120,121]).decode()
			A.proxy_config=ProxyConfig(proxy_mode=G,proxy_list=B,request_mode=F)
		else:A.proxy_config=C
		if not D:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
		if bytes([73,78,68,69,88]).decode()in A.symbol:A.symbol=A._index_validation()
	def _index_validation(A):
		"\n        If symbol contains 'INDEX' substring, validate it with _INDEX_MAPPING.\n        "
		if A.symbol not in _INDEX_MAPPING.keys():raise ValueError(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,109,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32]).decode()+A.symbol+bytes([46,32,67,195,161,99,32,103,105,195,161,32,116,114,225,187,139,32,104,225,187,163,112,32,108,225,187,135,58,32]).decode()+bytes([44,32]).decode().join(_INDEX_MAPPING.keys()))
		return _INDEX_MAPPING[A.symbol]
	def _input_validation(B,start,end,interval):
		'\n        Validate input data\n        ';C=interval
		try:D=normalize_interval(C);E=D.value
		except ValueError:raise ValueError(f"Giá trị interval không hợp lệ: {C}. Vui lòng chọn: 1m, 5m, 15m, 30m, 1H, 4h, 1D, 1W, 1M")
		A=TickerModel(symbol=B.symbol,start=start,end=end,interval=E)
		if A.interval not in B.interval_map:raise ValueError(f"Giá trị interval không hỗ trợ bởi MAS: {A.interval}. Các interval được hỗ trợ: 1m, 5m, 15m, 30m, 1H, 1D, 1W, 1M")
		return A
	@agg_execution(bytes([77,65,83,46,101,120,116]).decode())
	def history(self,start=None,end=None,interval=bytes([49,68]).decode(),to_df=True,show_log=False,count_back=None,floating=2,length=None):
		'\n        Tải lịch sử giá của mã chứng khoán từ nguồn dữ liệu MAS.\n\n        Tham số:\n            - start (tùy chọn): thời gian bắt đầu lấy dữ liệu (YYYY-MM-DD). Bắt buộc nếu không có length hoặc count_back.\n            - end (tùy chọn): thời gian kết thúc lấy dữ liệu. Mặc định là None, chương trình tự động lấy thời điểm hiện tại.\n            - interval (tùy chọn): Khung thời gian trích xuất dữ liệu. Mặc định là "1D".\n            - to_df (tùy chọn): Chuyển đổi dữ liệu lịch sử trả về dưới dạng DataFrame. Mặc định là True.\n            - show_log (tùy chọn): Hiển thị thông tin log. Mặc định là False.\n            - count_back (tùy chọn): Số lượng dữ liệu trả về từ thời điểm cuối.\n            - floating (tùy chọn): Số chữ số thập phân cho giá. Mặc định là 2.\n            - length (tùy chọn): Khoảng thời gian phân tích (vd: \'3M\', 150, \'100b\').\n        ';I=length;E=interval;D=count_back;C=start;B=self;A=end
		if A is None:A=datetime.now().strftime(bytes([37,89,45,37,109,45,37,100]).decode())
		if C is None:
			if I is not None:
				F=str(I)
				if F.endswith(bytes([98]).decode()):D=int(F[:-1]);C=get_start_date_from_lookback(lookback_length=F,end_date=A)
				else:C=get_start_date_from_lookback(lookback_length=F,end_date=A)
			elif D is not None:
				if E==bytes([49,68]).decode():C=(datetime.strptime(A,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=D*2)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				elif E==bytes([49,72]).decode():C=(datetime.strptime(A,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=D//6)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				elif E==bytes([49,109]).decode():C=(datetime.strptime(A,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=1)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				else:C=get_start_date_from_lookback(lookback_length=bytes([49,77]).decode(),end_date=A)
			else:raise ValueError(bytes([84,104,97,109,32,115,225,187,145,32,39,115,116,97,114,116,39,32,108,195,160,32,98,225,186,175,116,32,98,117,225,187,153,99,32,110,225,186,191,117,32,107,104,195,180,110,103,32,99,117,110,103,32,99,225,186,165,112,32,39,108,101,110,103,116,104,39,32,104,111,225,186,183,99,32,39,99,111,117,110,116,95,98,97,99,107,39,46]).decode())
		G=B._input_validation(C,A,E);J=datetime.strptime(G.start,bytes([37,89,45,37,109,45,37,100]).decode())
		if A is not None:
			K=datetime.strptime(G.end,bytes([37,89,45,37,109,45,37,100]).decode())+pd.Timedelta(days=1)
			if J>K:raise ValueError(bytes([84,104,225,187,157,105,32,103,105,97,110,32,98,225,186,175,116,32,196,145,225,186,167,117,32,107,104,195,180,110,103,32,116,104,225,187,131,32,108,225,187,155,110,32,104,198,161,110,32,116,104,225,187,157,105,32,103,105,97,110,32,107,225,186,191,116,32,116,104,195,186,99,46]).decode())
			L=int(K.timestamp())
		else:L=int((datetime.now()+pd.Timedelta(days=1)).timestamp())
		N=int(J.timestamp());O=B.interval_map[G.interval];P=B.base_url+bytes([116,114,97,100,105,110,103,118,105,101,119,47,104,105,115,116,111,114,121]).decode();Q={bytes([115,121,109,98,111,108]).decode():[B.symbol],bytes([114,101,115,111,108,117,116,105,111,110]).decode():O,bytes([102,114,111,109]).decode():N,bytes([116,111]).decode():L};M=send_request(url=P,headers=B.headers,method=bytes([71,69,84]).decode(),params=Q,payload=None,show_log=show_log)
		if not M:raise ValueError(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,100,225,187,175,32,108,105,225,187,135,117,46,32,86,117,105,32,108,195,178,110,103,32,107,105,225,187,131,109,32,116,114,97,32,108,225,186,161,105,32,109,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,104,111,225,186,183,99,32,116,104,225,187,157,105,32,103,105,97,110,32,116,114,117,121,32,120,117,225,186,165,116,46]).decode())
		H=ohlc_to_df(data=M,column_map=_OHLC_MAP,dtype_map=_OHLC_DTYPE,asset_type=B.asset_type,symbol=B.symbol,source=B.data_source,interval=G.interval,floating=floating,resample_map=_RESAMPLE_MAP)
		if D is not None:H=H.tail(D)
		if to_df:return H
		else:return H.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
	@agg_execution(bytes([77,65,83,46,101,120,116]).decode())
	def intraday(self,page_size=100,last_time=None,to_df=True,get_all=False,show_log=False):
		'\n        Truy xuất dữ liệu khớp lệnh của mã chứng khoán bất kỳ từ nguồn dữ liệu MAS\n\n        Tham số:\n            - page_size (tùy chọn): Số lượng dữ liệu trả về trong một lần request. Mặc định là 100. \n            - last_time (tùy chọn): Thời gian cắt dữ liệu, dùng để lấy dữ liệu sau thời gian cắt. Mặc định là None.\n            - to_df (tùy chọn): Chuyển đổi dữ liệu lịch sử trả về dưới dạng DataFrame. Mặc định là True.\n            - get_all (tùy chọn): Lấy tất cả các cột trả về từ API thay vì chỉ các cột chuẩn hoá. Mặc định là False.\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n        ';D=page_size;A=self
		if A.asset_type==bytes([105,110,100,101,120]).decode():raise ValueError(f"Dữ liệu intraday không được hỗ trợ cho chỉ số {A.symbol}.")
		C=trading_hours(None)
		if C[bytes([105,115,95,116,114,97,100,105,110,103,95,104,111,117,114]).decode()]is False and C[bytes([100,97,116,97,95,115,116,97,116,117,115]).decode()]==bytes([112,114,101,112,97,114,105,110,103]).decode():raise ValueError(str(C[bytes([116,105,109,101]).decode()])+bytes([58,32,68,225,187,175,32,108,105,225,187,135,117,32,107,104,225,187,155,112,32,108,225,187,135,110,104,32,107,104,195,180,110,103,32,116,104,225,187,131,32,116,114,117,121,32,99,225,186,173,112,32,116,114,111,110,103,32,116,104,225,187,157,105,32,103,105,97,110,32,99,104,117,225,186,169,110,32,98,225,187,139,32,112,104,105,195,170,110,32,109,225,187,155,105,46,32,86,117,105,32,108,195,178,110,103,32,113,117,97,121,32,108,225,186,161,105,32,115,97,117,46]).decode())
		if A.symbol is None:raise ValueError(bytes([86,117,105,32,108,195,178,110,103,32,110,104,225,186,173,112,32,109,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,99,225,186,167,110,32,116,114,117,121,32,120,117,225,186,165,116,32,107,104,105,32,107,104,225,187,159,105,32,116,225,186,161,111,32,84,114,97,100,105,110,103,32,67,108,97,115,115,46]).decode())
		if D>30000:logger.warning(bytes([66,225,186,161,110,32,196,145,97,110,103,32,121,195,170,117,32,99,225,186,167,117,32,116,114,117,121,32,120,117,225,186,165,116,32,113,117,195,161,32,110,104,105,225,187,129,117,32,100,225,187,175,32,108,105,225,187,135,117,44,32,196,145,105,225,187,129,117,32,110,195,160,121,32,99,195,179,32,116,104,225,187,131,32,103,195,162,121,32,108,225,187,151,105,32,113,117,195,161,32,116,225,186,163,105,46]).decode())
		E=A.base_url+f"market/{A.symbol}/quote";F={bytes([115,121,109,98,111,108]).decode():A.symbol,bytes([102,101,116,99,104,67,111,117,110,116]).decode():D};G=send_request(url=E,headers=A.headers,method=bytes([71,69,84]).decode(),params=F,payload=None,show_log=show_log);B=intraday_to_df(data=G[bytes([100,97,116,97]).decode()],column_map=_INTRADAY_MAP,dtype_map=_INTRADAY_DTYPE,symbol=A.symbol,asset_type=A.asset_type,source=A.data_source)
		if get_all:return B
		else:H=[bytes([116,105,109,101]).decode(),bytes([112,114,105,99,101]).decode(),bytes([118,111,108,117,109,101]).decode(),bytes([109,97,116,99,104,95,116,121,112,101]).decode()];B=B[H]
		if to_df:return B
		else:return B.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
	@agg_execution(bytes([77,65,83,46,101,120,116]).decode())
	def price_depth(self,get_all=False,to_df=True,show_log=False):
		'\n        Truy xuất thống kê độ bước giá & khối lượng khớp lệnh của mã chứng khoán bất kỳ từ nguồn dữ liệu MAS.\n\n        Tham số:\n            - get_all (tùy chọn): Lấy tất cả các cột trả về từ API thay vì chỉ các cột chuẩn hoá. Mặc định là False.\n            - to_df (tùy chọn): Chuyển đổi dữ liệu lịch sử trả về dưới dạng DataFrame. Mặc định là True.\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n        ';B=self;C=trading_hours(None)
		if C[bytes([105,115,95,116,114,97,100,105,110,103,95,104,111,117,114]).decode()]is False and C[bytes([100,97,116,97,95,115,116,97,116,117,115]).decode()]==bytes([112,114,101,112,97,114,105,110,103]).decode():raise ValueError(str(C[bytes([116,105,109,101]).decode()])+bytes([58,32,68,225,187,175,32,108,105,225,187,135,117,32,107,104,225,187,155,112,32,108,225,187,135,110,104,32,107,104,195,180,110,103,32,116,104,225,187,131,32,116,114,117,121,32,99,225,186,173,112,32,116,114,111,110,103,32,116,104,225,187,157,105,32,103,105,97,110,32,99,104,117,225,186,169,110,32,98,225,187,139,32,112,104,105,195,170,110,32,109,225,187,155,105,46,32,86,117,105,32,108,195,178,110,103,32,113,117,97,121,32,108,225,186,161,105,32,115,97,117,46]).decode())
		if B.symbol is None:raise ValueError(bytes([86,117,105,32,108,195,178,110,103,32,110,104,225,186,173,112,32,109,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,99,225,186,167,110,32,116,114,117,121,32,120,117,225,186,165,116,32,107,104,105,32,107,104,225,187,159,105,32,116,225,186,161,111,32,84,114,97,100,105,110,103,32,67,108,97,115,115,46]).decode())
		D=B.base_url+bytes([109,97,114,107,101,116,47,113,117,111,116,101,83,117,109,109,97,114,121]).decode();E={bytes([115,121,109,98,111,108]).decode():B.symbol};F=send_request(url=D,headers=B.headers,method=bytes([71,69,84]).decode(),params=E,payload=None,show_log=show_log);A=pd.DataFrame(F);A=A[_PRICE_DEPTH_MAP.keys()];A.rename(columns=_PRICE_DEPTH_MAP,inplace=True)
		if get_all==False:G=[bytes([112,114,105,99,101]).decode(),bytes([118,111,108,117,109,101]).decode(),bytes([98,117,121,95,118,111,108,117,109,101]).decode(),bytes([115,101,108,108,95,118,111,108,117,109,101]).decode(),bytes([117,110,100,101,102,105,110,101,100,95,118,111,108,117,109,101]).decode()];A=A[G]
		A.source=B.data_source
		if to_df:return A
		else:return A.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([113,117,111,116,101]).decode(),bytes([109,97,115]).decode(),Quote)