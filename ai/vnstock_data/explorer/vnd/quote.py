'History module for vnd.'
from datetime import datetime,timedelta
import pandas as pd,requests
from vnai import agg_execution
from vnstock.core.models import TickerModel
from vnstock.core.utils.interval import normalize_interval
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.lookback import get_start_date_from_lookback
from vnstock.core.utils.parser import get_asset_type
from vnstock_data.core.utils.user_agent import get_headers
from.const import _CHART_BASE,_INDEX_MAPPING,_INTERVAL_MAP,_OHLC_DTYPE,_OHLC_MAP
logger=get_logger(__name__)
class Quote:
	'\n    VND data source for fetching stock market data, accommodating requests with large date ranges.\n    '
	def __init__(A,symbol,random_agent=False,show_log=False):
		A.symbol=symbol.upper();A._history=None;A.asset_type=get_asset_type(A.symbol);A.base_url=_CHART_BASE;A.headers=get_headers(data_source=bytes([86,78,68]).decode(),random_agent=random_agent);A.interval_map=_INTERVAL_MAP;A.data_source=bytes([86,78,68]).decode()
		if not show_log:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
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
		if A.interval not in B.interval_map:raise ValueError(f"Giá trị interval không hỗ trợ bởi VND: {A.interval}. Các interval được hỗ trợ: 1m, 5m, 15m, 30m, 1H, 1D, 1W, 1M")
		return A
	@agg_execution(bytes([86,78,68,46,101,120,116]).decode())
	def history(self,start=None,end=None,interval=bytes([49,68]).decode(),to_df=True,show_log=False,count_back=None,length=None):
		'\n        Tải lịch sử giá của mã chứng khoán từ nguồn dữ liệu VN Direct.\n\n        Tham số:\n            - start (tùy chọn): thời gian bắt đầu lấy dữ liệu (YYYY-MM-DD). Bắt buộc nếu không có length hoặc count_back.\n            - end (tùy chọn): thời gian kết thúc lấy dữ liệu. Mặc định là None, sẽ lấy thời điểm hiện tại.\n            - interval (tùy chọn): Khung thời gian trích xuất dữ liệu. Mặc định là "1D".\n            - to_df (tùy chọn): Chuyển đổi dữ liệu lịch sử trả về dưới dạng DataFrame. Mặc định là True.\n            - show_log (tùy chọn): Hiển thị thông tin log. Mặc định là False.\n            - count_back (tùy chọn): Số lượng dữ liệu trả về từ thời điểm cuối. Mặc định là 365.\n            - length (tùy chọn): Khoảng thời gian phân tích (vd: \'3M\', 150, \'100b\').\n        ';L=length;K=show_log;F=count_back;E=interval;D=self;B=start;A=end
		if A is None:A=datetime.now().strftime(bytes([37,89,45,37,109,45,37,100]).decode())
		if B is None:
			if L is not None:
				H=str(L)
				if H.endswith(bytes([98]).decode()):F=int(H[:-1]);B=get_start_date_from_lookback(lookback_length=H,end_date=A)
				else:B=get_start_date_from_lookback(lookback_length=H,end_date=A)
			elif F is not None:
				if E==bytes([49,68]).decode():B=(datetime.strptime(A,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=F*2)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				elif E==bytes([49,72]).decode():B=(datetime.strptime(A,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=F//6)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				elif E==bytes([49,109]).decode():B=(datetime.strptime(A,bytes([37,89,45,37,109,45,37,100]).decode())-timedelta(days=1)).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
				else:B=get_start_date_from_lookback(lookback_length=bytes([49,77]).decode(),end_date=A)
			else:raise ValueError(bytes([84,104,97,109,32,115,225,187,145,32,39,115,116,97,114,116,39,32,108,195,160,32,98,225,186,175,116,32,98,117,225,187,153,99,32,110,225,186,191,117,32,107,104,195,180,110,103,32,99,117,110,103,32,99,225,186,165,112,32,39,108,101,110,103,116,104,39,32,104,111,225,186,183,99,32,39,99,111,117,110,116,95,98,97,99,107,39,46]).decode())
		C=D._input_validation(B,A,E)
		if A is None:M=int(datetime.now().timestamp())
		else:M=int(datetime.strptime(C.end,bytes([37,89,45,37,109,45,37,100]).decode()).timestamp())
		O=int(datetime.strptime(C.start,bytes([37,89,45,37,109,45,37,100]).decode()).timestamp());E=D.interval_map[C.interval];N=f"{D.base_url}/dchart/history?resolution={E}&symbol={D.symbol}&from={O}&to={M}"
		if K:logger.info(f"Tải dữ liệu từ {N}")
		I=requests.get(N,headers=D.headers)
		if I.status_code!=200:raise ConnectionError(f"Failed to fetch data: {I.status_code} - {I.reason}")
		J=I.json()
		if K:logger.info(f"Truy xuất thành công dữ liệu {C.symbol} từ {C.start} đến {C.end}, khung thời gian {C.interval}.")
		G=D._as_df(J,D.asset_type)
		if C.interval not in[bytes([49,68]).decode(),bytes([49,87]).decode(),bytes([49,77]).decode()]:G[bytes([116,105,109,101]).decode()]=G[bytes([116,105,109,101]).decode()]+pd.Timedelta(hours=7)
		if F is not None:G=G.tail(F)
		if to_df:return G
		else:J=G.to_json(orient=bytes([114,101,99,111,114,100,115]).decode());return J
	def _as_df(C,history_data,asset_type):
		'\n        Chuyển đổi dữ liệu lịch sử giá chứng khoán từ dạng JSON sang DataFrame.\n\n        Tham số:\n            - history_data: Dữ liệu lịch sử giá chứng khoán dạng JSON.\n        Trả về:\n            - DataFrame: Dữ liệu lịch sử giá chứng khoán dưới dạng DataFrame.\n        ';A=pd.DataFrame(history_data);A.drop(columns=[bytes([115]).decode()],inplace=True);A.rename(columns=_OHLC_MAP,inplace=True);A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()],unit=bytes([115]).decode())
		for(B,D)in _OHLC_DTYPE.items():A[B]=A[B].astype(D)
		A.attrs[bytes([110,97,109,101]).decode()]=C.symbol;A.attrs[bytes([99,97,116,101,103,111,114,121]).decode()]=asset_type;A.attrs[bytes([115,111,117,114,99,101]).decode()]=bytes([86,78,68]).decode();A=A[[bytes([116,105,109,101]).decode(),bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode(),bytes([118,111,108,117,109,101]).decode()]];return A
	@agg_execution(bytes([86,78,68,46,101,120,116]).decode())
	def intraday(self,page_size=100000,to_df=True,show_log=False):
		'\n        Truy xuất dữ liệu khớp lệnh của mã chứng khoán bất kỳ từ nguồn dữ liệu VCI\n\n        Tham số:\n            - page_size (tùy chọn): Số lượng dữ liệu trả về trong một lần request. Mặc định là 100. Không giới hạn số lượng tối đa. Tăng số này lên để lấy toàn bộ dữ liêu, ví dụ 10_000.\n            - trunc_time (tùy chọn): Thời gian cắt dữ liệu, dùng để lấy dữ liệu sau thời gian cắt. Mặc định là None.\n            - to_df (tùy chọn): Chuyển đổi dữ liệu lịch sử trả về dưới dạng DataFrame. Mặc định là True. Đặt là False để trả về dữ liệu dạng JSON.\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n        '
		if self.asset_type==bytes([105,110,100,101,120]).decode():raise ValueError(f"Dữ liệu intraday không được hỗ trợ cho chỉ số {self.symbol}.")
		logger.error(bytes([68,225,187,175,32,108,105,225,187,135,117,32,116,225,187,171,32,86,78,68,32,107,104,195,180,110,103,32,99,195,178,110,32,107,104,225,186,163,32,100,225,187,165,110,103,32,99,104,111,32,73,110,116,114,97,100,97,121,46,32,67,104,195,186,110,103,32,116,195,180,105,32,196,145,97,110,103,32,110,103,104,105,195,170,110,32,99,225,187,169,117,32,99,195,161,99,104,32,107,104,225,186,175,99,32,112,104,225,187,165,99,46]).decode())
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([113,117,111,116,101]).decode(),bytes([118,110,100]).decode(),Quote)