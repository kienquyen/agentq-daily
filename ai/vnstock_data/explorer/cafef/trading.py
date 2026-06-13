import pandas as pd,requests
from vnstock.core.utils.logger import get_logger
from vnstock_data.core.utils.parser import days_between
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.cafef.const import _BASE_URL,_CAFEF_INDEX_BASE_URL,_CAFEF_INDEX_MAPPING,_FOREIGN_TRADE_MAP,_INDEX_FOREIGN_TRADE_MAP,_INDEX_ORDER_STATS_MAP,_INDEX_PRICE_HISTORY_MAP,_INSIDER_DEAL_MAP,_ORDER_STATS_MAP,_PRICE_HISTORY_MAP,_PROP_TRADE_MAP
logger=get_logger(__name__)
class Trading:
	def __init__(A,symbol,random_agent=False,asset_type=bytes([101,113,117,105,116,121]).decode(),**B):
		A.asset_type=asset_type;A.raw_symbol=symbol.upper()
		if A.asset_type==bytes([105,110,100,101,120]).decode():
			if A.raw_symbol not in _CAFEF_INDEX_MAPPING:raise ValueError(f"Mã chỉ số '{A.raw_symbol}' không được hỗ trợ bởi nguồn CafeF. Các mã hợp lệ: VNINDEX (HOSE), UPCOMINDEX (UPCOM), HNXINDEX (HNX), VN30.")
			A.symbol=_CAFEF_INDEX_MAPPING[A.raw_symbol]
		else:A.symbol=A.raw_symbol
		A.base_url=_BASE_URL;A.headers=get_headers(data_source=bytes([67,65,70,69,70]).decode(),random_agent=random_agent)
	def _df_standardized(E,history_data,mapping_dict):
		'\n        Định dạng lại dữ liệu lịch sử giá của mã chứng khoán\n        ';B=mapping_dict;A=history_data;A=A.rename(columns=B);C=B.values()
		if A.empty:logger.info(bytes([78,111,32,100,97,116,97,32,102,111,117,110,100]).decode());return
		else:
			try:A=A[C]
			except Exception:logger.debug(f"Failed to sort column names. Actual columns and predefine mapping dict mismatched. Actual columns: {A.columns}. Expected columns: {C}");pass
			if bytes([116,105,109,101]).decode()in A.columns:
				if A[bytes([116,105,109,101]).decode()].astype(str).str.contains(bytes([47,68,97,116,101,92,40]).decode(),regex=True).any():D=A[bytes([116,105,109,101]).decode()].astype(str).str.replace(bytes([92,68]).decode(),'',regex=True);A[bytes([116,105,109,101]).decode()]=pd.to_datetime(pd.to_numeric(D),unit=bytes([109,115]).decode())
				else:A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()],format=bytes([37,100,47,37,109,47,37,89]).decode())
				A.set_index(bytes([116,105,109,101]).decode(),inplace=True)
			return A
	def price_history(B,start,end,page=1,limit=None):
		"\n        Truy xuất dữ liệu lịch sử giá của mã chứng khoán/chỉ số bất kỳ từ nguồn dữ liệu CafeF\n\n        Tham số:\n            - start (bắt buộc): Ngày bắt đầu lấy dữ liệu, định dạng YYYY-mm-dd. Ví dụ '2024-06-01'.\n            - end (bắt buộc): Ngày kết thúc lấy dữ liệu, định dạng YYYY-mm-dd. Ví dụ '2024-07-31'.\n            - page (tùy chọn): Trang hiện tại. Mặc định là 1.\n            - limit (tùy chọn): Số lượng dữ liệu trả về trong một lần request. Mặc định là None.\n        Return:\n            - DataFrame: Dữ liệu lịch sử giá của mã chứng khoán/chỉ số.\n        ";G=limit;F=end;E=start
		if G is None:G=days_between(start=E,end=F,format=bytes([37,89,45,37,109,45,37,100]).decode())
		if B.asset_type==bytes([105,110,100,101,120]).decode():
			H=pd.to_datetime(E).strftime(bytes([37,100,47,37,109,47,37,89]).decode());I=pd.to_datetime(F).strftime(bytes([37,100,47,37,109,47,37,89]).decode());J=f"{_CAFEF_INDEX_BASE_URL}/LichSuGia.ashx?TradeCenter={B.symbol}&StartDate={H}&EndDate={I}";D=requests.request(bytes([71,69,84]).decode(),J,headers=B.headers)
			if D.status_code!=200:raise ConnectionError(f"Tải dữ liệu không thành công: {D.status_code} - {D.text}")
			C=D.json()
			if bytes([68,97,116,97]).decode()not in C or bytes([76,105,115,116,68,97,116,97,76,83,71]).decode()not in C[bytes([68,97,116,97]).decode()]or C[bytes([68,97,116,97]).decode()][bytes([76,105,115,116,68,97,116,97,76,83,71]).decode()]is None:logger.error(f"Dữ liệu không hợp lệ từ CafeF: {C}");return
			K=len(C[bytes([68,97,116,97]).decode()][bytes([76,105,115,116,68,97,116,97,76,83,71]).decode()]);logger.info(f"Lịch sử giá chỉ số:\nMã CK (Index): {B.symbol}. Số bản ghi hợp lệ: {K}");A=pd.DataFrame(C[bytes([68,97,116,97]).decode()][bytes([76,105,115,116,68,97,116,97,76,83,71]).decode()])
			try:A=B._df_standardized(A,_INDEX_PRICE_HISTORY_MAP)
			except Exception as L:logger.error(f"Failed to standardize data: {L}")
		else:
			H=pd.to_datetime(E).strftime(bytes([37,109,47,37,100,47,37,89]).decode());I=pd.to_datetime(F).strftime(bytes([37,109,47,37,100,47,37,89]).decode());J=f"{B.base_url}/PriceHistory.ashx?Symbol={B.symbol}&StartDate={H}&EndDate={I}&PageIndex={page}&PageSize={G}";D=requests.request(bytes([71,69,84]).decode(),J,headers=B.headers)
			if D.status_code!=200:raise ConnectionError(f"Tải dữ liệu không thành công: {D.status_code} - {D.text}")
			C=D.json().get(bytes([68,97,116,97]).decode())
			if C is None or not isinstance(C,dict)or C.get(bytes([68,97,116,97]).decode())is None:logger.error(f"Dữ liệu không hợp lệ từ CafeF cho mã {B.symbol}");return pd.DataFrame()
			K=C[bytes([84,111,116,97,108,67,111,117,110,116]).decode()];logger.info(f"Lịch sử giá:\nMã CK: {B.symbol}. Số bản ghi hợp lệ: {K}");A=pd.DataFrame(C[bytes([68,97,116,97]).decode()])
			try:
				if bytes([84,104,97,121,68,111,105]).decode()in A.columns:A[bytes([99,104,97,110,103,101,95,112,99,116]).decode()]=pd.to_numeric(A[bytes([84,104,97,121,68,111,105]).decode()].str.split(bytes([40]).decode(),expand=True)[1].str.replace(bytes([32,37,41]).decode(),'',regex=False).str.replace(bytes([41]).decode(),'',regex=False).str.strip(),errors=bytes([99,111,101,114,99,101]).decode())/100
			except:logger.debug(bytes([70,97,105,108,101,100,32,116,111,32,101,120,116,114,97,99,116,32,99,104,97,110,103,101,95,112,99,116,32,102,114,111,109,32,84,104,97,121,68,111,105,32,99,111,108,117,109,110]).decode());pass
			try:A=B._df_standardized(A,_PRICE_HISTORY_MAP)
			except Exception as L:logger.error(f"Failed to standardize data: {L}")
		try:A.drop(columns=[bytes([99,104,97,110,103,101]).decode()],inplace=True)
		except:logger.debug(bytes([70,97,105,108,101,100,32,116,111,32,100,114,111,112,32,99,104,97,110,103,101,32,99,111,108,117,109,110]).decode());pass
		A.name=B.symbol;A.category=bytes([104,105,115,116,111,114,121,95,112,114,105,99,101]).decode();A.source=bytes([67,97,102,101,70]).decode();return A
	def foreign_trade(A,start,end,page=1,limit=None):
		'\n        Truy xuất dữ liệu lịch sử giao dịch nhà đầu tư nước ngoài của mã chứng khoán/chỉ số bất kỳ từ nguồn dữ liệu CafeF\n        ';G=limit;F=end;E=start
		if G is None:G=days_between(start=E,end=F,format=bytes([37,89,45,37,109,45,37,100]).decode())
		if A.asset_type==bytes([105,110,100,101,120]).decode():
			H=pd.to_datetime(E).strftime(bytes([37,100,47,37,109,47,37,89]).decode());I=pd.to_datetime(F).strftime(bytes([37,100,47,37,109,47,37,89]).decode());J=f"{_CAFEF_INDEX_BASE_URL}/GDNuocNgoai.ashx?TradeCenter={A.symbol}&StartDate={H}&EndDate={I}";D=requests.request(bytes([71,69,84]).decode(),J,headers=A.headers)
			if D.status_code!=200:raise ConnectionError(f"Tải dữ liệu không thành công: {D.status_code} - {D.text}")
			B=D.json()
			if bytes([68,97,116,97]).decode()not in B or bytes([76,105,115,116,68,97,116,97,78,78]).decode()not in B[bytes([68,97,116,97]).decode()]or B[bytes([68,97,116,97]).decode()][bytes([76,105,115,116,68,97,116,97,78,78]).decode()]is None:return
			K=len(B[bytes([68,97,116,97]).decode()][bytes([76,105,115,116,68,97,116,97,78,78]).decode()]);logger.info(f"Lịch sử GD Nước ngoài chỉ số:\nMã CK (Index): {A.symbol}. Số bản ghi hợp lệ: {K}");C=pd.DataFrame(B[bytes([68,97,116,97]).decode()][bytes([76,105,115,116,68,97,116,97,78,78]).decode()]);C=A._df_standardized(C,_INDEX_FOREIGN_TRADE_MAP)
		else:
			H=pd.to_datetime(E).strftime(bytes([37,109,47,37,100,47,37,89]).decode());I=pd.to_datetime(F).strftime(bytes([37,109,47,37,100,47,37,89]).decode());J=f"{A.base_url}/GDKhoiNgoai.ashx?Symbol={A.symbol}&StartDate={H}&EndDate={I}&PageIndex={page}&PageSize={G}";D=requests.request(bytes([71,69,84]).decode(),J,headers=A.headers)
			if D.status_code!=200:raise ConnectionError(f"Tải dữ liệu không thành công: {D.status_code} - {D.text}")
			B=D.json().get(bytes([68,97,116,97]).decode())
			if B is None or not isinstance(B,dict)or B.get(bytes([68,97,116,97]).decode())is None:return pd.DataFrame()
			K=B[bytes([84,111,116,97,108,67,111,117,110,116]).decode()];logger.info(f"Lịch sử GD Nước ngoài:\nMã CK: {A.symbol}. Số bản ghi hợp lệ: {K}");C=pd.DataFrame(B[bytes([68,97,116,97]).decode()]);C=A._df_standardized(C,_FOREIGN_TRADE_MAP)
		try:C.drop(columns=[bytes([99,104,97,110,103,101]).decode()],inplace=True)
		except:logger.debug(bytes([70,97,105,108,101,100,32,116,111,32,100,114,111,112,32,99,104,97,110,103,101,32,99,111,108,117,109,110]).decode());pass
		C.name=A.symbol;C.category=bytes([102,111,114,101,105,103,110,95,116,114,97,100,101]).decode();C.source=bytes([67,97,102,101,70]).decode();return C
	def prop_trade(A,start,end,page=1,limit=None):
		'\n        Truy xuất dữ liệu lịch sử giao dịch tự doanh (chỉ hỗ trợ cổ phiếu) từ nguồn dữ liệu CafeF\n        ';F=start;E=limit
		if A.asset_type==bytes([105,110,100,101,120]).decode():raise ValueError(bytes([65,80,73,32,67,97,102,101,70,32,107,104,195,180,110,103,32,104,225,187,151,32,116,114,225,187,163,32,100,225,187,175,32,108,105,225,187,135,117,32,103,105,97,111,32,100,225,187,139,99,104,32,116,225,187,177,32,100,111,97,110,104,32,99,104,111,32,196,145,225,187,145,105,32,116,198,176,225,187,163,110,103,32,99,104,225,187,137,32,115,225,187,145,46]).decode())
		if E is None:E=days_between(start=F,end=end,format=bytes([37,89,45,37,109,45,37,100]).decode())
		G=pd.to_datetime(F).strftime(bytes([37,109,47,37,100,47,37,89]).decode());H=pd.to_datetime(end).strftime(bytes([37,109,47,37,100,47,37,89]).decode());I=f"{A.base_url}/GDTuDoanh.ashx?Symbol={A.symbol}&StartDate={G}&EndDate={H}&PageIndex={page}&PageSize={E}";D=requests.request(bytes([71,69,84]).decode(),I,headers=A.headers)
		if D.status_code!=200:raise ConnectionError(f"Tải dữ liệu không thành công: {D.status_code} - {D.text}")
		C=D.json().get(bytes([68,97,116,97]).decode())
		if C is None or not isinstance(C,dict)or C.get(bytes([76,105,115,116,68,97,116,97,84,117,100,111,97,110,104]).decode())is None:return pd.DataFrame()
		J=C[bytes([84,111,116,97,108,67,111,117,110,116]).decode()];logger.info(f"Lịch sử GD Tự Doanh:\nMã CK: {A.symbol}. Số bản ghi hợp lệ: {J}");B=pd.DataFrame(C[bytes([76,105,115,116,68,97,116,97,84,117,100,111,97,110,104]).decode()]);B=A._df_standardized(B,_PROP_TRADE_MAP)
		try:B.drop(columns=bytes([115,121,109,98,111,108]).decode(),inplace=True)
		except:logger.debug(bytes([70,97,105,108,101,100,32,116,111,32,100,114,111,112,32,115,121,109,98,111,108,32,99,111,108,117,109,110]).decode());pass
		B.name=A.symbol;B.category=bytes([112,114,111,112,95,116,114,97,100,101]).decode();B.source=bytes([67,97,102,101,70]).decode();return B
	def order_stats(A,start,end,page=1,limit=None):
		'\n        Truy xuất dữ liệu lịch sử thống kê đặt lệnh của mã chứng khoán/chỉ số bất kỳ từ nguồn dữ liệu CafeF\n        ';G=limit;F=end;E=start
		if G is None:G=days_between(start=E,end=F,format=bytes([37,89,45,37,109,45,37,100]).decode())
		if A.asset_type==bytes([105,110,100,101,120]).decode():
			H=pd.to_datetime(E).strftime(bytes([37,100,47,37,109,47,37,89]).decode());I=pd.to_datetime(F).strftime(bytes([37,100,47,37,109,47,37,89]).decode());J=f"{_CAFEF_INDEX_BASE_URL}/ThongKeDL.ashx?TradeCenter={A.symbol}&StartDate={H}&EndDate={I}";D=requests.request(bytes([71,69,84]).decode(),J,headers=A.headers)
			if D.status_code!=200:raise ConnectionError(f"Tải dữ liệu không thành công: {D.status_code} - {D.text}")
			B=D.json()
			if bytes([68,97,116,97]).decode()not in B or bytes([76,105,115,116,68,97,116,97,84,75,68,76]).decode()not in B[bytes([68,97,116,97]).decode()]or B[bytes([68,97,116,97]).decode()][bytes([76,105,115,116,68,97,116,97,84,75,68,76]).decode()]is None:return
			K=len(B[bytes([68,97,116,97]).decode()][bytes([76,105,115,116,68,97,116,97,84,75,68,76]).decode()]);logger.info(f"Thống kê đặt lệnh chỉ số:\nMã CK (Index): {A.symbol}. Số bản ghi hợp lệ: {K}");C=pd.DataFrame(B[bytes([68,97,116,97]).decode()][bytes([76,105,115,116,68,97,116,97,84,75,68,76]).decode()]);C=A._df_standardized(C,_INDEX_ORDER_STATS_MAP)
		else:
			H=pd.to_datetime(E).strftime(bytes([37,109,47,37,100,47,37,89]).decode());I=pd.to_datetime(F).strftime(bytes([37,109,47,37,100,47,37,89]).decode());J=f"{A.base_url}/ThongKeDL.ashx?Symbol={A.symbol}&StartDate={H}&EndDate={I}&PageIndex={page}&PageSize={G}";D=requests.request(bytes([71,69,84]).decode(),J,headers=A.headers)
			if D.status_code!=200:raise ConnectionError(f"Tải dữ liệu không thành công: {D.status_code} - {D.text}")
			B=D.json()[bytes([68,97,116,97]).decode()]
			if B is None or bytes([68,97,116,97]).decode()not in B or B[bytes([68,97,116,97]).decode()]is None:return pd.DataFrame()
			K=B[bytes([84,111,116,97,108,67,111,117,110,116]).decode()];logger.info(f"Thống kê đặt lệnh:\nMã CK: {A.symbol}. Số bản ghi hợp lệ: {K}");C=pd.DataFrame(B[bytes([68,97,116,97]).decode()]);C=A._df_standardized(C,_ORDER_STATS_MAP)
		try:C.drop(columns=[bytes([99,104,97,110,103,101]).decode()],inplace=True)
		except:logger.debug(bytes([70,97,105,108,101,100,32,116,111,32,100,114,111,112,32,99,104,97,110,103,101,32,99,111,108,117,109,110]).decode());pass
		C.name=A.symbol;C.category=bytes([111,114,100,101,114,95,115,116,97,116,115]).decode();C.source=bytes([67,97,102,101,70]).decode();return C
	def insider_deal(B,start,end,page=1,limit=None):
		'\n        Truy xuất dữ liệu lịch sử thống kê giao dịch của cổ đông & nội bộ (chỉ hỗ trợ cổ phiếu) từ nguồn dữ liệu CafeF\n        ';G=start;F=limit
		if B.asset_type==bytes([105,110,100,101,120]).decode():raise ValueError(bytes([65,80,73,32,67,97,102,101,70,32,107,104,195,180,110,103,32,104,225,187,151,32,116,114,225,187,163,32,116,104,225,187,145,110,103,32,107,195,170,32,100,225,187,175,32,108,105,225,187,135,117,32,99,225,187,149,32,196,145,195,180,110,103,32,110,225,187,153,105,32,98,225,187,153,32,99,104,111,32,196,145,225,187,145,105,32,116,198,176,225,187,163,110,103,32,99,104,225,187,137,32,115,225,187,145,46]).decode())
		if F is None:F=days_between(start=G,end=end,format=bytes([37,89,45,37,109,45,37,100]).decode())
		H=pd.to_datetime(G).strftime(bytes([37,109,47,37,100,47,37,89]).decode());I=pd.to_datetime(end).strftime(bytes([37,109,47,37,100,47,37,89]).decode());J=f"{B.base_url}/GDCoDong.ashx?Symbol={B.symbol}&StartDate={H}&EndDate={I}&PageIndex={page}&PageSize={F}";D=requests.request(bytes([71,69,84]).decode(),J,headers=B.headers)
		if D.status_code!=200:raise ConnectionError(f"Tải dữ liệu không thành công: {D.status_code} - {D.text}")
		C=D.json()[bytes([68,97,116,97]).decode()]
		if C is None or bytes([68,97,116,97]).decode()not in C or C[bytes([68,97,116,97]).decode()]is None:return pd.DataFrame()
		K=C[bytes([84,111,116,97,108,67,111,117,110,116]).decode()];logger.info(f"Thống kê giao dịch Cổ Đông & Nội bộ:\nMã CK: {B.symbol}. Số bản ghi hợp lệ: {K}");A=pd.DataFrame(C[bytes([68,97,116,97]).decode()]);A=B._df_standardized(A,_INSIDER_DEAL_MAP)
		for E in[bytes([112,108,97,110,95,98,101,103,105,110,95,100,97,116,101]).decode(),bytes([112,108,97,110,95,101,110,100,95,100,97,116,101]).decode(),bytes([114,101,97,108,95,101,110,100,95,100,97,116,101]).decode(),bytes([112,117,98,108,105,115,104,101,100,95,100,97,116,101]).decode(),bytes([111,114,100,101,114,95,100,97,116,101]).decode()]:A[E]=A[E].str.replace(bytes([92,68]).decode(),'',regex=True);A[E]=pd.to_datetime(pd.to_numeric(A[E]),unit=bytes([109,115]).decode())
		A.name=B.symbol;A.category=bytes([105,110,115,105,100,101,114,95,100,101,97,108,115]).decode();A.source=bytes([67,97,102,101,70]).decode();return A
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([116,114,97,100,105,110,103]).decode(),bytes([99,97,102,101,102]).decode(),Trading)