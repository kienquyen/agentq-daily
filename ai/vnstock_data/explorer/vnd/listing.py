import pandas as pd,requests
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake
from vnstock_data.core.utils.user_agent import get_headers
logger=get_logger(__name__)
class Listing:
	'\n    Cấu hình truy cập dữ liệu lịch sử giá chứng khoán từ VCI.\n    '
	def __init__(A,random_agent=False,show_log=False):
		A.data_source=bytes([86,78,68]).decode();A.headers=get_headers(data_source=A.data_source,random_agent=random_agent)
		if not show_log:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	@agg_execution(bytes([86,78,68,46,101,120,116]).decode())
	def all_symbols(self,exchange=[bytes([72,79,83,69]).decode(),bytes([72,78,88]).decode(),bytes([85,80,67,79,77]).decode()],show_log=False,to_df=True):
		'\n        Truy xuất toàn bộ danh sách cổ phiếu và trạng thái giao dịch.\n\n        Tham số:\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n            - to_df (tùy chọn): Chuyển đổi dữ liệu danh sách mã cổ phiếu trả về dưới dạng DataFrame. Mặc định là True. Đặt là False để trả về dữ liệu dạng JSON.\n        ';B=exchange
		if len(B)>1:B=bytes([44]).decode().join(B)
		else:B=B[0]
		E=f"https://api-finfo.vndirect.com.vn/v4/stocks?q=type:stock,ifc~floor:{B}&size=9999"
		if show_log:logger.info(f"Requested URL: {E}")
		C=requests.request(bytes([71,69,84]).decode(),E,headers=self.headers)
		if C.status_code!=200:raise ConnectionError(f"Failed to fetch data: {C.status_code} - {C.reason}")
		D=C.json();A=pd.DataFrame(D[bytes([100,97,116,97]).decode()])
		if bytes([102,108,111,111,114]).decode()in A.columns:A=A.rename(columns={bytes([102,108,111,111,114]).decode():bytes([101,120,99,104,97,110,103,101]).decode()})
		if bytes([99,111,100,101]).decode()in A.columns:A=A.rename(columns={bytes([99,111,100,101]).decode():bytes([115,121,109,98,111,108]).decode()})
		if to_df:
			if not D:raise ValueError(bytes([74,83,79,78,32,100,97,116,97,32,105,115,32,101,109,112,116,121,32,111,114,32,110,111,116,32,112,114,111,118,105,100,101,100,46]).decode())
			A.columns=[camel_to_snake(A)for A in A.columns];A.source=bytes([86,78,68]).decode();return A
		else:D=A.to_json(orient=bytes([114,101,99,111,114,100,115]).decode());return D
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([108,105,115,116,105,110,103]).decode(),bytes([118,110,100]).decode(),Listing)