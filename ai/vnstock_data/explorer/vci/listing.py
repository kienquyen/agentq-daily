'Listing module.'
import pandas as pd
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake
from vnstock.core.utils.transform import drop_cols_by_pattern,reorder_cols
from.const import _GROUP_CODE_MAPPING,_VCI_INDEX_MAPPING,_TRADING_URL
from vnstock_data.core.utils.client import send_request
from vnstock_data.core.utils.user_agent import get_headers
logger=get_logger(__name__)
class Listing:
	'\n    Cấu hình truy cập dữ liệu lịch sử giá chứng khoán từ VCI.\n    '
	def __init__(A,random_agent=False,show_log=False):
		B=show_log;A.data_source=bytes([86,67,73]).decode();A.base_url=_TRADING_URL;A.headers=get_headers(data_source=A.data_source,random_agent=random_agent);A.show_log=B
		if not B:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def all_symbols(self,show_log=False,to_df=True):
		'\n        Truy xuất danh sách toàn. bộ mã và tên các cổ phiếu trên thị trường Việt Nam.\n\n        Tham số:\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n            - to_df (tùy chọn): Chuyển đổi dữ liệu danh sách mã cổ phiếu trả về dưới dạng DataFrame. Mặc định là True. Đặt là False để trả về dữ liệu dạng JSON.\n        ';A=self.symbols_by_exchange(show_log=show_log,to_df=True);A=A.query(bytes([116,121,112,101,32,61,61,32,34,83,84,79,67,75,34]).decode()).reset_index(drop=True);A=A[[bytes([115,121,109,98,111,108]).decode(),bytes([111,114,103,97,110,95,110,97,109,101]).decode()]]
		if to_df:return A
		else:B=A.to_json(orient=bytes([114,101,99,111,114,100,115]).decode());return B
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def symbols_by_industries(self,lang=bytes([118,105]).decode(),show_log=False,to_df=True):
		'\n        Truy xuất thông tin phân ngành icb của các mã cổ phiếu trên thị trường Việt Nam.\n\n        Tham số:\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n            - to_df (tùy chọn): Chuyển đổi dữ liệu danh sách mã cổ phiếu trả về dưới dạng DataFrame. Mặc định là True. Đặt là False để trả về dữ liệu dạng JSON.\n        ';E=show_log
		if lang not in[bytes([118,105]).decode(),bytes([101,110]).decode()]:raise ValueError(bytes([84,104,97,109,32,115,225,187,145,32,108,97,110,103,32,112,104,225,186,163,105,32,108,195,160,32,39,118,105,39,32,104,111,225,186,183,99,32,39,101,110,39,46]).decode())
		H=bytes([49]).decode()if lang==bytes([118,105]).decode()else bytes([50]).decode();I=f"https://iq.vietcap.com.vn/api/iq-insight-service/v2/company/search-bar?language={H}";C=send_request(url=I,headers=self.headers,method=bytes([71,69,84]).decode(),show_log=E)
		if not C or bytes([100,97,116,97]).decode()not in C:raise ValueError(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,100,225,187,175,32,108,105,225,187,135,117,46,32,86,117,105,32,108,195,178,110,103,32,107,105,225,187,131,109,32,116,114,97,32,108,225,186,161,105,46]).decode())
		if E:logger.info(bytes([84,114,117,121,32,120,117,225,186,165,116,32,116,104,195,160,110,104,32,99,195,180,110,103,32,100,225,187,175,32,108,105,225,187,135,117,32,100,97,110,104,32,115,195,161,99,104,32,112,104,195,162,110,32,110,103,195,160,110,104,32,105,99,98,46]).decode())
		F=[]
		for B in C[bytes([100,97,116,97]).decode()]:
			J=B.get(bytes([99,111,100,101]).decode());K=B.get(bytes([110,97,109,101]).decode());L=B.get(bytes([99,111,109,84,121,112,101,67,111,100,101]).decode())
			for G in range(1,5):
				D=f"icbLv{G}"
				if D in B and B[D]is not None:F.append({bytes([115,121,109,98,111,108]).decode():J,bytes([111,114,103,97,110,95,110,97,109,101]).decode():K,bytes([99,111,109,95,116,121,112,101,95,99,111,100,101]).decode():L,bytes([105,99,98,95,108,101,118,101,108]).decode():G,bytes([105,99,98,95,99,111,100,101]).decode():B[D].get(bytes([99,111,100,101]).decode()),bytes([105,99,98,95,110,97,109,101]).decode():B[D].get(bytes([110,97,109,101]).decode())})
		A=pd.DataFrame(F)
		if not A.empty:A=A[A[bytes([105,99,98,95,99,111,100,101]).decode()].notna()&(A[bytes([105,99,98,95,99,111,100,101]).decode()]!='')];A=A.sort_values(by=[bytes([115,121,109,98,111,108]).decode(),bytes([105,99,98,95,108,101,118,101,108]).decode()]).reset_index(drop=True);A=A[[bytes([115,121,109,98,111,108]).decode(),bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([99,111,109,95,116,121,112,101,95,99,111,100,101]).decode(),bytes([105,99,98,95,108,101,118,101,108]).decode(),bytes([105,99,98,95,99,111,100,101]).decode(),bytes([105,99,98,95,110,97,109,101]).decode()]]
		A.source=bytes([86,67,73]).decode()
		if to_df:return A
		else:C=A.to_json(orient=bytes([114,101,99,111,114,100,115]).decode());return C
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def symbols_by_exchange(self,lang=bytes([118,105]).decode(),show_log=False,to_df=True):
		'\n        Truy xuất thông tin niêm yết theo sàn của các mã cổ phiếu trên thị trường Việt Nam.\n\n        Tham số:\n                - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n                - to_df (tùy chọn): Chuyển đổi dữ liệu danh sách mã cổ phiếu trả về dưới dạng DataFrame. Mặc định là True. Đặt là False để trả về dữ liệu dạng JSON.\n        ';C=show_log
		if lang not in[bytes([118,105]).decode(),bytes([101,110]).decode()]:raise ValueError(bytes([84,104,97,109,32,115,225,187,145,32,108,97,110,103,32,112,104,225,186,163,105,32,108,195,160,32,39,118,105,39,32,104,111,225,186,183,99,32,39,101,110,39,46]).decode())
		D=self.base_url.rstrip(bytes([47]).decode())+bytes([47,112,114,105,99,101,47,115,121,109,98,111,108,115,47,103,101,116,65,108,108]).decode();B=send_request(url=D,headers=self.headers,method=bytes([71,69,84]).decode(),payload=None,show_log=C)
		if not B:raise ValueError(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,100,225,187,175,32,108,105,225,187,135,117,46,32,86,117,105,32,108,195,178,110,103,32,107,105,225,187,131,109,32,116,114,97,32,108,225,186,161,105,46]).decode())
		if C:logger.info(f"Truy xuất dữ liệu thành công cho {len(B)} mã.")
		A=pd.DataFrame(B);A.columns=[camel_to_snake(A)for A in A.columns];A=A.rename(columns={bytes([98,111,97,114,100]).decode():bytes([101,120,99,104,97,110,103,101]).decode()});A=reorder_cols(A,[bytes([115,121,109,98,111,108]).decode(),bytes([101,120,99,104,97,110,103,101]).decode(),bytes([116,121,112,101]).decode()],position=bytes([102,105,114,115,116]).decode());A=A.drop(columns=[bytes([105,100]).decode()])
		if lang==bytes([118,105]).decode():A=drop_cols_by_pattern(A,[bytes([101,110,95]).decode()])
		else:A=A.drop(columns=[bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([111,114,103,97,110,95,115,104,111,114,116,95,110,97,109,101]).decode()]);A.columns=[A.replace(bytes([101,110,95]).decode(),'')for A in A.columns]
		if to_df:A.source=bytes([86,67,73]).decode();return A
		else:B=A.to_json(orient=bytes([114,101,99,111,114,100,115]).decode());return B
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def industries_icb(self,show_log=False,to_df=True):
		'\n        Truy xuất thông tin phân ngành icb của các mã cổ phiếu trên thị trường Việt Nam.\n\n        Tham số:\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n            - to_df (tùy chọn): Chuyển đổi dữ liệu danh sách mã cổ phiếu trả về dưới dạng DataFrame. Mặc định là True. Đặt là False để trả về dữ liệu dạng JSON.\n        ';C=show_log;D=bytes([104,116,116,112,115,58,47,47,105,113,46,118,105,101,116,99,97,112,46,99,111,109,46,118,110,47,97,112,105,47,105,113,45,105,110,115,105,103,104,116,45,115,101,114,118,105,99,101,47,118,49,47,115,101,99,116,111,114,115,47,105,99,98,45,99,111,100,101,115]).decode();B=send_request(url=D,headers=self.headers,method=bytes([71,69,84]).decode(),show_log=C)
		if not B:raise ValueError(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,100,225,187,175,32,108,105,225,187,135,117,46,32,86,117,105,32,108,195,178,110,103,32,107,105,225,187,131,109,32,116,114,97,32,108,225,186,161,105,46]).decode())
		if C:logger.info(bytes([84,114,117,121,32,120,117,225,186,165,116,32,116,104,195,160,110,104,32,99,195,180,110,103,32,100,225,187,175,32,108,105,225,187,135,117,32,100,97,110,104,32,115,195,161,99,104,32,112,104,195,162,110,32,110,103,195,160,110,104,32,105,99,98,46]).decode())
		A=pd.DataFrame(B[bytes([100,97,116,97]).decode()]);A=A.rename(columns={bytes([110,97,109,101]).decode():bytes([105,99,98,95,99,111,100,101]).decode(),bytes([118,105,83,101,99,116,111,114]).decode():bytes([105,99,98,95,110,97,109,101]).decode(),bytes([101,110,83,101,99,116,111,114]).decode():bytes([101,110,95,105,99,98,95,110,97,109,101]).decode(),bytes([105,99,98,76,101,118,101,108]).decode():bytes([108,101,118,101,108]).decode()})
		if not A.empty:A=A[[bytes([105,99,98,95,110,97,109,101]).decode(),bytes([101,110,95,105,99,98,95,110,97,109,101]).decode(),bytes([105,99,98,95,99,111,100,101]).decode(),bytes([108,101,118,101,108]).decode()]];A=A.sort_values(by=[bytes([105,99,98,95,99,111,100,101]).decode()]).reset_index(drop=True)
		A.source=bytes([86,67,73]).decode()
		if to_df:return A
		else:B=A.to_json(orient=bytes([114,101,99,111,114,100,115]).decode());return B
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def symbols_by_group(self,group=bytes([86,78,51,48]).decode(),show_log=False,to_df=True):
		"\n        Truy xuất danh sách các mã cổ phiếu theo tên nhóm trên thị trường Việt Nam.\n\n        Tham số:\n            - group (tùy chọn): Tên nhóm cổ phiếu. Mặc định là 'VN30'. Các mã được hỗ trợ bao gồm các sàn (HOSE, HNX, UPCOM), các chỉ số (VN30, VNMID, VNSML, VN100, VNALL, HNX30, HNXCON, HNXFIN, HNXLCAP, HNXMSCAP, HNXMAN), và các loại công cụ (ETF, FUTURE, WARRANT, BOND, FUND_BOND).\n            - show_log (tùy chọn): Hiển thị thông tin log giúp debug dễ dàng. Mặc định là False.\n            - to_df (tùy chọn): Chuyển đổi dữ liệu danh sách mã cổ phiếu trả về dưới dạng DataFrame. Mặc định là True. Đặt là False để trả về dữ liệu dạng JSON.\n        ";E=show_log;D=group;A=D.upper()
		if A in _VCI_INDEX_MAPPING:F=_VCI_INDEX_MAPPING[A]
		elif A in _GROUP_CODE_MAPPING:F=_GROUP_CODE_MAPPING[A]
		else:G=list(_GROUP_CODE_MAPPING.keys())+list(_VCI_INDEX_MAPPING.keys());raise ValueError(f"Invalid group '{D}'. Group must be one of {G}")
		H=self.base_url.rstrip(bytes([47]).decode())+f"/price/symbols/getByGroup?group={F}";B=send_request(url=H,headers=self.headers,method=bytes([71,69,84]).decode(),payload=None,show_log=E)
		if E:logger.info(bytes([84,114,117,121,32,120,117,225,186,165,116,32,116,104,195,160,110,104,32,99,195,180,110,103,32,100,225,187,175,32,108,105,225,187,135,117,32,100,97,110,104,32,115,195,161,99,104,32,109,195,163,32,67,80,32,116,104,101,111,32,110,104,195,179,109,46]).decode())
		C=pd.DataFrame(B)
		if to_df:
			if not B:raise ValueError(bytes([74,83,79,78,32,100,97,116,97,32,105,115,32,101,109,112,116,121,32,111,114,32,110,111,116,32,112,114,111,118,105,100,101,100,46]).decode())
			C.source=bytes([86,67,73]).decode();return C[bytes([115,121,109,98,111,108]).decode()]
		else:B=C.to_json(orient=bytes([114,101,99,111,114,100,115]).decode());return B
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def all_future_indices(self,show_log=False,to_df=True):return self.symbols_by_group(group=bytes([70,85,84,85,82,69]).decode(),show_log=show_log,to_df=to_df)
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def all_government_bonds(self,show_log=False,to_df=True):return self.symbols_by_group(group=bytes([70,85,95,66,79,78,68]).decode(),show_log=show_log,to_df=to_df)
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def all_covered_warrant(self,show_log=False,to_df=True):return self.symbols_by_group(group=bytes([67,87]).decode(),show_log=show_log,to_df=to_df)
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def all_bonds(self,show_log=False,to_df=True):return self.symbols_by_group(group=bytes([66,79,78,68]).decode(),show_log=show_log,to_df=to_df)
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def all_etf(self,show_log=False,to_df=True):'\n        Truy xuất danh sách mã quỹ ETF.\n        ';return self.symbols_by_group(group=bytes([69,84,70]).decode(),show_log=show_log,to_df=to_df)
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([108,105,115,116,105,110,103]).decode(),bytes([118,99,105]).decode(),Listing)