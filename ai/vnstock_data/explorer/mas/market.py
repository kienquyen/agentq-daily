'Market module for MAS.'
import pandas as pd
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake
from vnstock_data.core.utils.client import send_request
from vnstock_data.core.utils.user_agent import get_headers
logger=get_logger(__name__)
class Market:
	'\n    Truy xuất thông tin trạng thái thị trường chung từ MAS.\n    '
	def __init__(A,random_agent=False,show_log=True):
		A.data_source=bytes([77,65,83]).decode();A.base_url=bytes([104,116,116,112,115,58,47,47,109,97,115,98,111,97,114,100,46,109,97,115,118,110,46,99,111,109,47,97,112,105,47,118,49,47,109,97,114,107,101,116,47]).decode();A.headers=get_headers(data_source=A.data_source,random_agent=random_agent)
		if not show_log:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	@agg_execution(bytes([77,65,83,46,101,120,116]).decode())
	def status(self,to_df=True,show_log=False):
		'\n        Lấy trạng thái thực tế của thị trường (ví dụ: OPEN, CLOSED, ATO, ATC)\n        Đầu ra là danh sách trạng thái các sàn HOSE, HNX, UPCOM.\n        \n        Tham số:\n            - to_df (tùy chọn): Chuyển đổi dữ liệu trả về dưới dạng DataFrame. Mặc định là True.\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n        ';D=self.base_url+bytes([109,97,114,107,101,116,83,116,97,116,117,115]).decode();C=send_request(url=D,headers=self.headers,method=bytes([71,69,84]).decode(),payload=None,show_log=show_log)
		if not C:raise ValueError(bytes([75,104,195,180,110,103,32,116,104,225,187,131,32,108,225,186,165,121,32,100,225,187,175,32,108,105,225,187,135,117,32,116,114,225,186,161,110,103,32,116,104,195,161,105,32,116,104,225,187,139,32,116,114,198,176,225,187,157,110,103,46]).decode())
		A=pd.DataFrame(C)
		for B in[bytes([116,105,109,101]).decode(),bytes([108,97,115,116,84,114,97,100,105,110,103,68,97,116,101]).decode(),bytes([108,97,115,116,77,97,114,107,101,116,73,110,105,116]).decode()]:
			if B in A.columns:A[B]=pd.to_datetime(A[B],unit=bytes([109,115]).decode()).dt.tz_localize(bytes([85,84,67]).decode()).dt.tz_convert(bytes([65,115,105,97,47,72,111,95,67,104,105,95,77,105,110,104]).decode()).dt.tz_localize(None)
		A.columns=[camel_to_snake(A)for A in A.columns];E={bytes([109,97,114,107,101,116]).decode():bytes([101,120,99,104,97,110,103,101]).decode(),bytes([116,121,112,101]).decode():bytes([97,115,115,101,116,95,116,121,112,101]).decode(),bytes([116,105,109,101]).decode():bytes([116,105,109,101,115,116,97,109,112]).decode()};A=A.rename(columns=E);F=[bytes([101,120,99,104,97,110,103,101]).decode(),bytes([97,115,115,101,116,95,116,121,112,101]).decode(),bytes([115,116,97,116,117,115]).decode(),bytes([116,105,109,101,115,116,97,109,112]).decode(),bytes([108,97,115,116,95,116,114,97,100,105,110,103,95,100,97,116,101]).decode()];A=A[[B for B in F if B in A.columns]]
		if to_df:return A
		return A.to_json(orient=bytes([114,101,99,111,114,100,115]).decode())
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([109,97,114,107,101,116]).decode(),bytes([109,97,115]).decode(),Market)