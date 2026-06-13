'History module for VCI.'
from datetime import datetime,timedelta
import pandas as pd
from vnai import agg_execution
from vnstock.core.models import TickerModel
from vnstock.core.utils.interval import normalize_interval
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.lookback import get_start_date_from_lookback
from vnstock.core.utils.market import trading_hours
from vnstock.core.utils.parser import get_asset_type
from vnstock.explorer.vci.const import _INTERVAL_MAP,_INTRADAY_DTYPE,_INTRADAY_MAP,_INTRADAY_URL,_OHLC_DTYPE,_OHLC_MAP,_RESAMPLE_MAP,_TRADING_URL
from vnstock_data.core.utils.client import ProxyConfig,send_request
from vnstock_data.core.utils.transform import intraday_to_df,ohlc_to_df
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.vci.const import _PRICE_DEPTH_MAP,_VCI_INDEX_MAPPING
logger=get_logger(__name__)
class Quote:
	'\n    Cấu hình truy cập dữ liệu lịch sử giá chứng khoán từ VCI.\n    Cho phép cấu hình proxy thông qua object ProxyConfig.\n    \n    Hỗ trợ các tính năng proxy nâng cao:\n    - auto_fetch: Tự động lấy proxy từ proxyscrape API\n    - validate_proxies: Kiểm tra tính hợp lệ của proxy\n    - prefer_speed: Ưu tiên proxy có tốc độ tốt nhất\n    '
	def __init__(A,symbol,random_agent=False,proxy_config=None,show_log=True,proxy_mode=None,proxy_list=None):
		F=proxy_mode;E=proxy_config;D=symbol;C=proxy_list;B=show_log;A.symbol=D.upper();A.data_source=bytes([86,67,73]).decode();A._history=None;A.asset_type=get_asset_type(A.symbol);A.base_url=_TRADING_URL;A.headers=get_headers(data_source=A.data_source,random_agent=random_agent);A.interval_map=_INTERVAL_MAP;A.show_log=B
		if A.symbol in _VCI_INDEX_MAPPING:
			A.symbol=_VCI_INDEX_MAPPING[A.symbol]
			if B:logger.info(f"Mã chỉ số {D.upper()} được tự động chuyển sang {A.symbol} cho nguồn VCI")
		if E is None:
			H=F if F else bytes([116,114,121]).decode();G=bytes([100,105,114,101,99,116]).decode()
			if C and len(C)>0:G=bytes([112,114,111,120,121]).decode()
			A.proxy_config=ProxyConfig(proxy_mode=H,proxy_list=C,request_mode=G)
		else:A.proxy_config=E
		if not B:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
		if bytes([73,78,68,69,88]).decode()in A.symbol and A.symbol not in _VCI_INDEX_MAPPING.values():A.symbol=A._index_validation()
	def _index_validation(A):
		'\n        Validate if symbol is a valid VCI index.\n        '
		if A.symbol not in _VCI_INDEX_MAPPING.values():
			if A.symbol in _VCI_INDEX_MAPPING:return _VCI_INDEX_MAPPING[A.symbol]
			B=sorted(list(set(list(_VCI_INDEX_MAPPING.keys())+list(_VCI_INDEX_MAPPING.values()))));raise ValueError(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,109,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32]).decode()+A.symbol+bytes([46,32,67,195,161,99,32,103,105,195,161,32,116,114,225,187,139,32,104,225,187,163,112,32,108,225,187,135,58,32]).decode()+bytes([44,32]).decode().join(B))
		return A.symbol
	def _input_validation(B,start,end,interval):
		'\n        Validate input data\n        ';C=interval
		try:D=normalize_interval(C);E=D.value
		except ValueError:raise ValueError(f"Giá trị interval không hợp lệ: {C}. Vui lòng chọn: 1m, 5m, 15m, 30m, 1H, 4h, 1D, 1W, 1M")
		A=TickerModel(symbol=B.symbol,start=start,end=end,interval=E)
		if A.interval not in B.interval_map:raise ValueError(f"Giá trị interval không hỗ trợ bởi VCI: {A.interval}. Các interval được hỗ trợ: 1m, 5m, 15m, 30m, 1H, 1D, 1W, 1M")
		return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def history(self,start=None,end=None,interval=bytes([49,68]).decode(),to_df=True,show_log=False,count_back=None,floating=2,length=None):
		'\n        Tải lịch sử giá của mã chứng khoán từ nguồn dữ liệu VCI.\n\n        Tham số:\n            - start (tùy chọn): thời gian bắt đầu lấy dữ liệu (YYYY-MM-DD). Bắt buộc nếu không có length hoặc count_back.\n            - end (tùy chọn): thời gian kết thúc lấy dữ liệu. Mặc định là None, chương trình tự động lấy thời điểm hiện tại.\n            - interval (tùy chọn): Khung thời gian trích xuất dữ liệu. Mặc định là "1D".\n            - to_df (tùy chọn): Chuyển đổi dữ liệu lịch sử trả về dưới dạng DataFrame. Mặc định là True.\n            - show_log (tùy chọn): Hiển thị thông tin log. Mặc định là False.\n            - count_back (tùy chọn): Số lượng dữ liệu trả về từ thời điểm cuối.\n            - floating (tùy chọn): Số chữ số thập phân cho giá. Mặc định là 2.\n            - length (tùy chọn): Khoảng thời gian phân tích (vd: \'3M\', 150, \'100b\').\n        ';N=length;H=interval;D=start;C=count_back;B=end;A=self
		if B is None:B=datetime.now().strftime(bytes([37,89,45,37,109,45,37,100]).decode())
		if D is None:
			if N is not None:
				I=str(N)
				if I.endswith(bytes([98]).decode()):C=int(I[:-1]);D=get_start_date_from_lookback(lookback_length=I,end_date=B)
				else:D=get_start_date_from_lookback(lookback_length=I,end_date=B)
			elif C is not None:
				if H==bytes([49,68]).decode():D=(datetime.strptime(B,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=C*2)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				elif H==bytes([49,72]).decode():D=(datetime.strptime(B,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=C//6)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				elif H==bytes([49,109]).decode():D=(datetime.strptime(B,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=1)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				else:D=get_start_date_from_lookback(lookback_length=bytes([49,77]).decode(),end_date=B)
			else:raise ValueError(bytes([84,104,97,109,32,115,225,187,145,32,39,115,116,97,114,116,39,32,108,195,160,32,98,225,186,175,116,32,98,117,225,187,153,99,32,110,225,186,191,117,32,107,104,195,180,110,103,32,99,117,110,103,32,99,225,186,165,112,32,39,108,101,110,103,116,104,39,32,104,111,225,186,183,99,32,39,99,111,117,110,116,95,98,97,99,107,39,46]).decode())
		J=A._input_validation(D,B,H);K=datetime.strptime(J.start,bytes([37,89,45,37,109,45,37,100]).decode())
		if B is not None:
			F=datetime.strptime(J.end,bytes([37,89,45,37,109,45,37,100]).decode())+pd.Timedelta(days=1)
			if K>F:raise ValueError(bytes([84,104,225,187,157,105,32,103,105,97,110,32,98,225,186,175,116,32,196,145,225,186,167,117,32,107,104,195,180,110,103,32,116,104,225,187,131,32,108,225,187,155,110,32,104,198,161,110,32,116,104,225,187,157,105,32,103,105,97,110,32,107,225,186,191,116,32,116,104,195,186,99,46]).decode())
			O=int(F.timestamp())
		else:F=datetime.now()+pd.Timedelta(days=1);O=int(F.timestamp())
		P=A.interval_map[J.interval];G=1000;L=pd.bdate_range(start=K,end=F)
		if C is None and B is not None:
			M=P
			if M==bytes([79,78,69,95,68,65,89]).decode():G=len(L)+1
			elif M==bytes([79,78,69,95,72,79,85,82]).decode():G=len(L)*6.5+1
			elif M==bytes([79,78,69,95,77,73,78,85,84,69]).decode():G=len(L)*6.5*60+1
		else:G=C if C is not None else 1000
		R=f"{A.base_url}chart/OHLCChart/gap-chart";S={bytes([116,105,109,101,70,114,97,109,101]).decode():P,bytes([115,121,109,98,111,108,115]).decode():[A.symbol],bytes([116,111]).decode():O,bytes([99,111,117,110,116,66,97,99,107]).decode():G};Q=send_request(url=R,headers=A.headers,method=bytes([80,79,83,84]).decode(),payload=S,show_log=show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode)
		if not Q:raise ValueError(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,100,225,187,175,32,108,105,225,187,135,117,46,32,86,117,105,32,108,195,178,110,103,32,107,105,225,187,131,109,32,116,114,97,32,108,225,186,161,105,32,109,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,104,111,225,186,183,99,32,116,104,225,187,157,105,32,103,105,97,110,32,116,114,117,121,32,120,117,225,186,165,116,46]).decode())
		E=ohlc_to_df(data=Q[0],column_map=_OHLC_MAP,dtype_map=_OHLC_DTYPE,asset_type=A.asset_type,symbol=A.symbol,source=A.data_source,interval=J.interval,floating=floating,resample_map=_RESAMPLE_MAP);E=E[E[bytes([116,105,109,101]).decode()]>=K].reset_index(drop=True)
		if C is not None:E=E.tail(C)
		if to_df:return E
		else:return E.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def intraday(self,page_size=100,last_time=None,to_df=True,show_log=False):
		'\n        Truy xuất dữ liệu khớp lệnh của mã chứng khoán bất kỳ từ nguồn dữ liệu VCI\n\n        Tham số:\n            - page_size (tùy chọn): Số lượng dữ liệu trả về trong một lần request. Mặc định là 100. \n            - last_time (tùy chọn): Thời gian cắt dữ liệu, dùng để lấy dữ liệu sau thời gian cắt. Mặc định là None.\n            - to_df (tùy chọn): Chuyển đổi dữ liệu lịch sử trả về dưới dạng DataFrame. Mặc định là True.\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n        ';C=page_size;A=self
		if A.asset_type==bytes([105,110,100,101,120]).decode():raise ValueError(f"Dữ liệu intraday không được hỗ trợ cho chỉ số {A.symbol}.")
		B=trading_hours(None)
		if B[bytes([105,115,95,116,114,97,100,105,110,103,95,104,111,117,114]).decode()]is False and B[bytes([100,97,116,97,95,115,116,97,116,117,115]).decode()]==bytes([112,114,101,112,97,114,105,110,103]).decode():raise ValueError(str(B[bytes([116,105,109,101]).decode()])+bytes([58,32,68,225,187,175,32,108,105,225,187,135,117,32,107,104,225,187,155,112,32,108,225,187,135,110,104,32,107,104,195,180,110,103,32,116,104,225,187,131,32,116,114,117,121,32,99,225,186,173,112,32,116,114,111,110,103,32,116,104,225,187,157,105,32,103,105,97,110,32,99,104,117,225,186,169,110,32,98,225,187,139,32,112,104,105,195,170,110,32,109,225,187,155,105,46,32,86,117,105,32,108,195,178,110,103,32,113,117,97,121,32,108,225,186,161,105,32,115,97,117,46]).decode())
		if A.symbol is None:raise ValueError(bytes([86,117,105,32,108,195,178,110,103,32,110,104,225,186,173,112,32,109,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,99,225,186,167,110,32,116,114,117,121,32,120,117,225,186,165,116,32,107,104,105,32,107,104,225,187,159,105,32,116,225,186,161,111,32,84,114,97,100,105,110,103,32,67,108,97,115,115,46]).decode())
		if C>30000:logger.warning(bytes([66,225,186,161,110,32,196,145,97,110,103,32,121,195,170,117,32,99,225,186,167,117,32,116,114,117,121,32,120,117,225,186,165,116,32,113,117,195,161,32,110,104,105,225,187,129,117,32,100,225,187,175,32,108,105,225,187,135,117,44,32,196,145,105,225,187,129,117,32,110,195,160,121,32,99,195,179,32,116,104,225,187,131,32,103,195,162,121,32,108,225,187,151,105,32,113,117,195,161,32,116,225,186,163,105,46]).decode())
		E=f"{A.base_url}{_INTRADAY_URL}/LEData/getAll";F={bytes([115,121,109,98,111,108]).decode():A.symbol,bytes([108,105,109,105,116]).decode():C,bytes([116,114,117,110,99,84,105,109,101]).decode():last_time};G=send_request(url=E,headers=A.headers,method=bytes([80,79,83,84]).decode(),payload=F,show_log=show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode,auto_fetch=A.proxy_config.auto_fetch,validate_proxies=A.proxy_config.validate_proxies,prefer_speed=A.proxy_config.prefer_speed);D=intraday_to_df(data=G,column_map=_INTRADAY_MAP,dtype_map=_INTRADAY_DTYPE,symbol=A.symbol,asset_type=A.asset_type,source=A.data_source)
		if to_df:return D
		else:return D.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def price_depth(self,to_df=True,show_log=False):
		'\n        Truy xuất thống kê độ bước giá & khối lượng khớp lệnh của mã chứng khoán bất kỳ từ nguồn dữ liệu VCI.\n\n        Tham số:\n            - to_df (tùy chọn): Chuyển đổi dữ liệu lịch sử trả về dưới dạng DataFrame. Mặc định là True.\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n        ';A=self;C=trading_hours(None)
		if C[bytes([105,115,95,116,114,97,100,105,110,103,95,104,111,117,114]).decode()]is False and C[bytes([100,97,116,97,95,115,116,97,116,117,115]).decode()]==bytes([112,114,101,112,97,114,105,110,103]).decode():raise ValueError(str(C[bytes([116,105,109,101]).decode()])+bytes([58,32,68,225,187,175,32,108,105,225,187,135,117,32,107,104,225,187,155,112,32,108,225,187,135,110,104,32,107,104,195,180,110,103,32,116,104,225,187,131,32,116,114,117,121,32,99,225,186,173,112,32,116,114,111,110,103,32,116,104,225,187,157,105,32,103,105,97,110,32,99,104,117,225,186,169,110,32,98,225,187,139,32,112,104,105,195,170,110,32,109,225,187,155,105,46,32,86,117,105,32,108,195,178,110,103,32,113,117,97,121,32,108,225,186,161,105,32,115,97,117,46]).decode())
		if A.symbol is None:raise ValueError(bytes([86,117,105,32,108,195,178,110,103,32,110,104,225,186,173,112,32,109,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,99,225,186,167,110,32,116,114,117,121,32,120,117,225,186,165,116,32,107,104,105,32,107,104,225,187,159,105,32,116,225,186,161,111,32,84,114,97,100,105,110,103,32,67,108,97,115,115,46]).decode())
		D=f"{A.base_url}{_INTRADAY_URL}/AccumulatedPriceStepVol/getSymbolData";E={bytes([115,121,109,98,111,108]).decode():A.symbol};F=send_request(url=D,headers=A.headers,method=bytes([80,79,83,84]).decode(),payload=E,show_log=show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode,auto_fetch=A.proxy_config.auto_fetch,validate_proxies=A.proxy_config.validate_proxies,prefer_speed=A.proxy_config.prefer_speed);B=pd.DataFrame(F);B=B[_PRICE_DEPTH_MAP.keys()];B.rename(columns=_PRICE_DEPTH_MAP,inplace=True);B.source=A.data_source
		if to_df:return B
		else:return B.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([113,117,111,116,101]).decode(),bytes([118,99,105]).decode(),Quote)