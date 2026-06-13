'Listing module for ForexSB.'
import gzip,json,pandas as pd
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
logger=get_logger(__name__)
from vnstock_data.core.utils.user_agent import get_headers
class Listing:
	'\n    Cấu hình truy cập danh sách symbol từ ForexSB.\n    '
	def __init__(A,random_agent=False,show_log=False):
		B=show_log;A.data_source=bytes([70,88,83,66]).decode();A.base_url=bytes([104,116,116,112,115,58,47,47,100,97,116,97,46,102,111,114,101,120,115,98,46,99,111,109,47,100,97,116,97,102,101,101,100,47,105,110,102,111,47,112,114,101,109,105,117,109,46,106,115,111,110,46,103,122]).decode();A.show_log=B
		if not B:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	@agg_execution(bytes([70,88,83,66,46,101,120,116]).decode())
	def all_symbols(self,show_log=False,to_df=True):
		'\n        Truy xuất danh sách các mã hỗ trợ (Forex, Crypto, v.v) từ ForexSB.\n        ';import requests as E;A=E.get(self.base_url,headers=get_headers(bytes([70,88,83,66]).decode(),random_agent=False,browser=bytes([99,104,114,111,109,101]).decode(),platform=bytes([109,97,99,111,115]).decode()))
		if A.status_code!=200:raise ValueError(f"Không thể truy cập dữ liệu symbol từ ForexSB. Status: {A.status_code}")
		try:
			if A.content[:2]==b'\x1f\x8b':C=gzip.decompress(A.content)
			else:C=A.content
			F=json.loads(C)
		except Exception as G:raise ValueError(f"Lỗi khi giải nén hoặc parse dữ liệu: {G}")
		B=F
		if show_log:logger.info(f"Tìm thấy {len(B)} biểu tượng.")
		if to_df:H=list(B.values());D=pd.DataFrame(H);D.source=self.data_source;return D
		else:return B
	@agg_execution(bytes([70,88,83,66,46,101,120,116]).decode())
	def search_symbol(self,query,show_log=False,to_df=True):
		'\n        Tìm kiếm các mã hỗ trợ trên ForexSB dựa vào từ khóa (tìm theo symbol hoặc description).\n        \n        Tham số:\n            - query (str): Từ khóa tìm kiếm.\n            - show_log (bool): Hiển thị log dữ liệu.\n            - to_df (bool): Trả về DataFrame hay JSON string.\n        ';D=to_df;C=query;A=self.all_symbols(show_log=False,to_df=True)
		if A.empty:
			if not D:return bytes([91,93]).decode()
			return A
		E=C.lower();F=A[bytes([115,121,109,98,111,108]).decode()].str.lower().str.contains(E,na=False)|A[bytes([100,101,115,99,114,105,112,116,105,111,110]).decode()].str.lower().str.contains(E,na=False);B=A[F].reset_index(drop=True)
		if show_log:logger.info(f"Tìm thấy {len(B)} kết quả khớp với từ khóa '{C}'")
		if D:return B
		else:return B.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([108,105,115,116,105,110,103]).decode(),bytes([102,120,115,98]).decode(),Listing)