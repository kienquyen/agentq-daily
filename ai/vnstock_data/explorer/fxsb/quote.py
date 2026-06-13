'History module for ForexSB.'
import datetime,gzip,struct,pandas as pd,requests
from vnai import agg_execution
from vnstock.core.models import TickerModel
from vnstock.core.utils.interval import normalize_interval
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.lookback import get_start_date_from_lookback
from vnstock_data.core.utils.user_agent import get_headers
try:from vnstock.explorer.vci.const import _OHLC_MAP
except ImportError:_OHLC_MAP={bytes([116,105,109,101]).decode():bytes([116,105,109,101]).decode(),bytes([111,112,101,110]).decode():bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode():bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode():bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode():bytes([99,108,111,115,101]).decode(),bytes([118,111,108,117,109,101]).decode():bytes([118,111,108,117,109,101]).decode()}
logger=get_logger(__name__)
_FXSB_INTERVAL_MAP={bytes([49,109]).decode():bytes([49]).decode(),bytes([53,109]).decode():bytes([53]).decode(),bytes([49,53,109]).decode():bytes([49,53]).decode(),bytes([51,48,109]).decode():bytes([51,48]).decode(),bytes([49,72]).decode():bytes([51,48]).decode(),bytes([52,72]).decode():bytes([51,48]).decode(),bytes([49,68]).decode():bytes([51,48]).decode(),bytes([49,87]).decode():bytes([51,48]).decode()}
class Quote:
	'\n    Cấu hình truy cập dữ liệu lịch sử giá cho các cặp ngoại tệ từ ForexSB.\n    '
	def __init__(A,symbol,random_agent=False,show_log=False,**C):
		B=show_log;A.symbol=symbol.upper();A.data_source=bytes([70,88,83,66]).decode();A.base_url=bytes([104,116,116,112,115,58,47,47,100,97,116,97,46,102,111,114,101,120,115,98,46,99,111,109,47,100,97,116,97,102,101,101,100,47,100,97,116,97,47,100,117,107,97,115,99,111,112,121,47]).decode();A.interval_map=_FXSB_INTERVAL_MAP;A.show_log=B
		if not B:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	def _input_validation(B,start,end,interval):
		'\n        Validate input data format and interval.\n        ';C=interval
		try:
			if str(C).upper()in[bytes([72,52]).decode(),bytes([52,72]).decode()]:A=bytes([52,72]).decode()
			else:D=normalize_interval(C);A=D.value
		except ValueError:raise ValueError(f"Giá trị interval không hợp lệ: {C}.")
		if A not in B.interval_map:E=bytes([44,32]).decode().join(B.interval_map.keys());raise ValueError(f"Giá trị interval không được FXSB hỗ trợ: {A}. Hỗ trợ cơ bản và mở rộng: {E}")
		F=TickerModel(symbol=B.symbol,start=start,end=end,interval=A);return F
	@agg_execution(bytes([70,88,83,66,46,101,120,116]).decode())
	def history(self,start='',end='',interval=bytes([49,68]).decode(),to_df=True,show_log=False,length=100000,floating=5):
		'\n        Tải dữ liệu OHLC từ file .lb.gz của ForexSB.\n\n        Tham số:\n            - start (tùy chọn): thời gian bắt đầu lấy dữ liệu (YYYY-MM-DD). \n            - end (tùy chọn): thời gian kết thúc lấy dữ liệu.\n            - interval (tùy chọn): Khung thời gian.\n            - to_df (tùy chọn): Chuyển đổi về DataFrame.\n            - count_back (tùy chọn): Giới hạn số bars cuối cùng. Mặc định là 100,000 để an toàn,\n                                     có thể lấy toàn bộ file nếu cần.\n            - length (tùy chọn): khoảng thời gian quy ước.\n        ';L=floating;E=end;D=start;C=self;B=length
		if not E:E=datetime.datetime.now(datetime.timezone.utc).strftime(bytes([37,89,45,37,109,45,37,100]).decode())
		if not D:
			if B:
				G=str(B).lower()
				if G.endswith(bytes([98]).decode()):B=int(G[:-1])
				elif G.isdigit():B=int(G)
				else:D=get_start_date_from_lookback(lookback_length=str(B).upper(),end_date=E)
			else:B=100000
		H=C._input_validation(D if D else bytes([49,57,55,48,45,48,49,45,48,49]).decode(),E,interval);M=C.interval_map[H.interval];I=f"{C.base_url}{C.symbol}{M}.lb.gz"
		try:F=requests.get(I,headers=get_headers(bytes([70,88,83,66]).decode(),random_agent=False,browser=bytes([99,104,114,111,109,101]).decode(),platform=bytes([109,97,99,111,115]).decode()),timeout=15)
		except requests.exceptions.Timeout:raise ConnectionError(f"ForexSB request timed out sau 15 giây cho symbol {C.symbol} (interval={H.interval}). Kiểm tra kết nối mạng hoặc thử lại sau. URL: {I}")
		except requests.exceptions.RequestException as J:raise ConnectionError(f"ForexSB connection error: {J}. URL: {I}")
		if F.status_code!=200:raise ValueError(f"Không thể truy xuất dữ liệu từ ForexSB cho symbol {C.symbol} (Status {F.status_code}). URL: {I}")
		try:
			if F.content[:2]==b'\x1f\x8b':K=gzip.decompress(F.content)
			else:K=F.content
		except Exception as J:raise ValueError(f"Lỗi khi giải nén dữ liệu: {J}")
		T=[];N=28;U=len(K)//N;O=struct.iter_unpack(bytes([60,73,73,73,73,73,73,73]).decode(),K);P=[bytes([116,105,109,101]).decode(),bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode(),bytes([118,111,108,117,109,101]).decode(),bytes([101,120,116,114,97]).decode()];A=pd.DataFrame(O,columns=P);A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()],unit=bytes([109]).decode(),origin=bytes([50,48,48,48,45,48,49,45,48,49]).decode(),utc=True);A[bytes([116,105,109,101]).decode()]=A[bytes([116,105,109,101]).decode()].dt.tz_localize(None);A[bytes([111,112,101,110]).decode()]=A[bytes([111,112,101,110]).decode()]/100000;A[bytes([104,105,103,104]).decode()]=A[bytes([104,105,103,104]).decode()]/100000;A[bytes([108,111,119]).decode()]=A[bytes([108,111,119]).decode()]/100000;A[bytes([99,108,111,115,101]).decode()]=A[bytes([99,108,111,115,101]).decode()]/100000;A=A.drop(columns=[bytes([101,120,116,114,97]).decode()])
		if H.interval in[bytes([49,72]).decode(),bytes([52,72]).decode(),bytes([49,68]).decode(),bytes([49,87]).decode()]:A.set_index(bytes([116,105,109,101]).decode(),inplace=True);Q=H.interval.replace(bytes([72]).decode(),bytes([104]).decode()).replace(bytes([68]).decode(),bytes([68]).decode()).replace(bytes([87]).decode(),bytes([87]).decode());A=A.resample(Q,label=bytes([108,101,102,116]).decode(),closed=bytes([108,101,102,116]).decode()).agg({bytes([111,112,101,110]).decode():bytes([102,105,114,115,116]).decode(),bytes([104,105,103,104]).decode():bytes([109,97,120]).decode(),bytes([108,111,119]).decode():bytes([109,105,110]).decode(),bytes([99,108,111,115,101]).decode():bytes([108,97,115,116]).decode(),bytes([118,111,108,117,109,101]).decode():bytes([115,117,109]).decode()}).dropna().reset_index()
		if D is not None and D!='':R=pd.to_datetime(D);A=A[A[bytes([116,105,109,101]).decode()]>=R]
		if E is not None and E!='':S=pd.to_datetime(E)+pd.Timedelta(days=1);A=A[A[bytes([116,105,109,101]).decode()]<S]
		A=A.reset_index(drop=True)
		if B and isinstance(B,int)and B>0:A=A.tail(B).reset_index(drop=True)
		elif A.shape[0]>100000:A=A.tail(100000).reset_index(drop=True)
		if L is not None:A=A.round(L)
		A.source=C.data_source
		if to_df:return A
		else:return A.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([113,117,111,116,101]).decode(),bytes([102,120,115,98]).decode(),Quote)