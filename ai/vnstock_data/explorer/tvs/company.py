'\nModule quản lý thông tin công ty từ nguồn dữ liệu VCI.\n'
import pandas as pd
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake,get_asset_type
from vnstock_data.core.utils.client import send_request
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.tvs.const import _BASE_URL
logger=get_logger(__name__)
class Company:
	'\n    Class (lớp) quản lý các thông tin liên quan đến công ty từ nguồn dữ liệu VCI.\n\n    Tham số:\n        - symbol (str): Mã chứng khoán của công ty cần truy xuất thông tin.\n        - random_agent (bool): Sử dụng user-agent ngẫu nhiên hoặc không. Mặc định là False.\n        - to_df (bool): Chuyển đổi dữ liệu thành DataFrame hoặc không. Mặc định là True.\n        - show_log (bool): Hiển thị thông tin log hoặc không. Mặc định là False.\n    '
	def __init__(A,symbol,random_agent=False,to_df=True,show_log=False):
		'\n        Khởi tạo đối tượng Company với các tham số cho việc truy xuất dữ liệu.\n        ';B=show_log;A.symbol=symbol.upper();A.asset_type=get_asset_type(A.symbol)
		if A.asset_type not in[bytes([115,116,111,99,107]).decode()]:raise ValueError(bytes([77,195,163,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,225,187,149,32,112,104,105,225,186,191,117,32,109,225,187,155,105,32,99,195,179,32,116,104,195,180,110,103,32,116,105,110,46]).decode())
		A.headers=get_headers(data_source=bytes([84,86,83]).decode(),random_agent=random_agent);A.show_log=B;A.to_df=to_df
		if not B:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	def _fetch_data(A,url):
		'\n        Phương thức riêng để lấy dữ liệu công ty từ nguồn VCI.\n        \n        Returns:\n            Dict: Dữ liệu thô về công ty từ API.\n        '
		if A.show_log:logger.debug(f"Requesting data for {A.symbol} from {url}. payload: {payload}")
		B=send_request(url=url,headers=A.headers,method=bytes([80,79,83,84]).decode(),payload=payload,show_log=A.show_log);return B
	@agg_execution(bytes([84,86,83,46,101,120,116]).decode())
	def overview(self):
		'\n        Lấy thông tin tổng quan về công ty từ nguồn dữ liệu VCI.\n        \n        Returns:\n            Union[Dict, pd.DataFrame]: Thông tin tổng quan về công ty dưới dạng từ điển hoặc DataFrame.\n        ';B=self;D=f"{_BASE_URL}Dashboard/GetComanyInfo?ticker={B.symbol}";C=B._fetch_data(D)
		if not C:logger.warning(f"No data available for {B.symbol}");return
		A=pd.DataFrame(C,index=[0]);A.columns=[camel_to_snake(A)for A in A.columns];A=A.rename(columns={bytes([116,105,99,107,101,114]).decode():bytes([115,121,109,98,111,108]).decode()})
		if B.to_df:return A
		else:return C.to_dict(orient=bytes([114,101,99,111,114,100,115]).decode())[0]if not C.empty else{}