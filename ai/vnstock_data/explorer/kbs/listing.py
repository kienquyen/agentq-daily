'Listing module for KB Securities (KBS) data source.'
import pandas as pd
from vnai import agg_execution
from vnstock.common import indices as market_indices
from vnstock.core.utils.logger import get_logger
from vnstock_data.core.utils.client import ProxyConfig,send_request
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.kbs.const import _GROUP_CODE,_IIS_BASE_URL,_SEARCH_URL,_SECTOR_ALL_URL
logger=get_logger(__name__)
class Listing:
	'\n    Lớp truy cập dữ liệu danh sách mã chứng khoán từ KB Securities (KBS).\n    '
	def __init__(A,random_agent=False,proxy_config=None,show_log=False,proxy_mode=None,proxy_list=None):
		'\n        Khởi tạo Listing client cho KBS.\n\n        Args:\n            random_agent: Sử dụng user agent ngẫu nhiên. Mặc định False.\n            proxy_config: Cấu hình proxy. Mặc định None (không sử dụng proxy).\n            show_log: Hiển thị log debug. Mặc định False.\n            proxy_mode: Chế độ proxy (try, rotate, random, single). Mặc định None.\n            proxy_list: Danh sách proxy URLs. Mặc định None.\n        ';E=proxy_mode;D=show_log;C=proxy_config;B=proxy_list;A.data_source=bytes([75,66,83]).decode();A.base_url=_IIS_BASE_URL;A.headers=get_headers(data_source=A.data_source,random_agent=random_agent);A.show_log=D
		if C is None:
			G=E if E else bytes([116,114,121]).decode();F=bytes([100,105,114,101,99,116]).decode()
			if B and len(B)>0:F=bytes([112,114,111,120,121]).decode()
			A.proxy_config=ProxyConfig(proxy_mode=G,proxy_list=B,request_mode=F)
		else:A.proxy_config=C
		if not D:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def all_symbols(self,show_log=False):
		"\n        Truy xuất danh sách toàn bộ mã chứng khoán trên thị trường Việt Nam từ KBS.\n\n        Trả về DataFrame đơn giản với mapping symbol → organ_name (tên công ty tiếng Việt).\n\n        Args:\n            show_log: Hiển thị log debug. Mặc định False.\n\n        Returns:\n            DataFrame với 2 cột: symbol, organ_name.\n            Metadata 'source' được lưu trong df.attrs['source'].\n\n        Examples:\n            >>> kbs = Listing()\n            >>> df = kbs.all_symbols()\n            >>> print(df.columns.tolist())\n            ['symbol', 'organ_name']\n            >>> print(df.attrs['source'])\n            'KBS'\n        ";B=show_log
		try:C=self._get_full_stock_data(show_log=B)
		except Exception as D:
			if B:logger.error(f"Lỗi khi lấy dữ liệu chứng khoán: {D!s}")
			return pd.DataFrame(columns=[bytes([115,121,109,98,111,108]).decode(),bytes([111,114,103,97,110,95,110,97,109,101]).decode()])
		if not C:return pd.DataFrame(columns=[bytes([115,121,109,98,111,108]).decode(),bytes([111,114,103,97,110,95,110,97,109,101]).decode()])
		A=pd.DataFrame(C).query(bytes([116,121,112,101,32,61,61,32,39,115,116,111,99,107,39]).decode())
		if bytes([110,97,109,101]).decode()in A.columns:A=A.rename(columns={bytes([110,97,109,101]).decode():bytes([111,114,103,97,110,95,110,97,109,101]).decode()})
		A=A[[bytes([115,121,109,98,111,108]).decode(),bytes([111,114,103,97,110,95,110,97,109,101]).decode()]];A.attrs[bytes([115,111,117,114,99,101]).decode()]=self.data_source
		if B:logger.info(f"Truy xuất thành công {len(A)} mã chứng khoán.")
		return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def symbols_by_exchange(self,get_all=False,show_log=False):
		"\n        Truy xuất danh sách mã chứng khoán theo sàn giao dịch.\n\n        Sử dụng endpoint /stock/search/data để lấy dữ liệu đầy đủ.\n\n        Args:\n            get_all: Lấy tất cả các cột mà API cung cấp thay vì chỉ các cột chuẩn hoá. Mặc định False.\n            show_log: Hiển thị log debug. Mặc định False.\n\n        Returns:\n            DataFrame chứa các cột từ API KBS: symbol, organ_name, en_organ_name,\n            exchange, type, id, re, ceiling, floor.\n            Metadata 'source' được lưu trong df.attrs['source'].\n            Các cột không có sẽ bỏ qua.\n        ";B=show_log
		try:C=self._get_full_stock_data(show_log=B)
		except Exception as E:
			if B:logger.error(f"Lỗi khi lấy dữ liệu chứng khoán: {E!s}")
			return pd.DataFrame(columns=[bytes([115,121,109,98,111,108]).decode(),bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([101,120,99,104,97,110,103,101]).decode(),bytes([115,111,117,114,99,101]).decode()])
		if not C:return pd.DataFrame(columns=[bytes([115,121,109,98,111,108]).decode(),bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([101,120,99,104,97,110,103,101]).decode(),bytes([115,111,117,114,99,101]).decode()])
		A=pd.DataFrame(C);F={bytes([110,97,109,101]).decode():bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([110,97,109,101,69,110]).decode():bytes([101,110,95,111,114,103,97,110,95,110,97,109,101]).decode(),bytes([105,110,100,101,120]).decode():bytes([105,100]).decode()};A=A.rename(columns=F)
		if get_all:G=[bytes([115,121,109,98,111,108]).decode(),bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([101,110,95,111,114,103,97,110,95,110,97,109,101]).decode(),bytes([101,120,99,104,97,110,103,101]).decode(),bytes([116,121,112,101]).decode(),bytes([105,100]).decode(),bytes([114,101]).decode(),bytes([99,101,105,108,105,110,103]).decode(),bytes([102,108,111,111,114]).decode()];D=[B for B in G if B in A.columns]
		else:D=[bytes([115,121,109,98,111,108]).decode(),bytes([111,114,103,97,110,95,110,97,109,101]).decode(),bytes([101,110,95,111,114,103,97,110,95,110,97,109,101]).decode(),bytes([101,120,99,104,97,110,103,101]).decode(),bytes([116,121,112,101]).decode(),bytes([105,100]).decode()]
		A=A[D];A.attrs[bytes([115,111,117,114,99,101]).decode()]=self.data_source
		if B:logger.info(f"Truy xuất thành công {len(A)} mã chứng khoán theo sàn.")
		return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def symbols_by_industries(self,lang=bytes([118,105]).decode(),show_log=False):
		"\n        Truy xuất danh sách mã chứng khoán theo nhóm ngành. Thông tin mã ngành là quy định riêng của KBS không theo chuẩn ICB thường gặp.\n\n        Args:\n            lang: Ngôn ngữ ('vi' hoặc 'en'). Mặc định 'vi'.\n            show_log: Hiển thị log debug. Mặc định False.\n\n        Returns:\n            DataFrame chứa thông tin mã chứng khoán theo ngành.\n\n        Raises:\n            ValueError: Nếu ngôn ngữ không hợp lệ.\n        ";C=show_log;B=self
		if lang not in[bytes([118,105]).decode(),bytes([101,110]).decode()]:raise ValueError(bytes([78,103,195,180,110,32,110,103,225,187,175,32,112,104,225,186,163,105,32,108,195,160,32,39,118,105,39,32,104,111,225,186,183,99,32,39,101,110,39,46]).decode())
		try:I=B._get_industries_internal(show_log=C)
		except Exception as D:
			if C:logger.error(f"Lỗi khi lấy danh sách ngành: {D!s}")
			A=pd.DataFrame(columns=[bytes([115,121,109,98,111,108]).decode(),bytes([105,110,100,117,115,116,114,121,95,99,111,100,101]).decode(),bytes([105,110,100,117,115,116,114,121,95,110,97,109,101]).decode()]);A.attrs[bytes([115,111,117,114,99,101]).decode()]=B.data_source;return A
		E=[]
		for G in I:
			F=G[bytes([99,111,100,101]).decode()];H=G[bytes([110,97,109,101]).decode()]
			try:
				J=B._get_symbols_by_industry_internal(industry_code=F,show_log=C)
				for K in J:E.append({bytes([115,121,109,98,111,108]).decode():K,bytes([105,110,100,117,115,116,114,121,95,99,111,100,101]).decode():F,bytes([105,110,100,117,115,116,114,121,95,110,97,109,101]).decode():H})
			except Exception as D:
				if C:logger.warning(f"Lỗi khi lấy mã từ ngành {H} ({F}): {D!s}")
		if E:A=pd.DataFrame(E);A.attrs[bytes([115,111,117,114,99,101]).decode()]=B.data_source;return A
		else:A=pd.DataFrame(columns=[bytes([115,121,109,98,111,108]).decode(),bytes([105,110,100,117,115,116,114,121,95,99,111,100,101]).decode(),bytes([105,110,100,117,115,116,114,121,95,110,97,109,101]).decode()]);A.attrs[bytes([115,111,117,114,99,101]).decode()]=B.data_source;return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def symbols_by_group(self,group=bytes([86,78,51,48]).decode(),show_log=False):
		"\n        Truy xuất danh sách mã chứng khoán theo nhóm chỉ số.\n\n        Hỗ trợ lọc theo các nhóm/sàn: chỉ số VN (VN30, VN100, VNMidCap, VNSmallCap, VNSI, VNX50, VNXALL),\n        sàn giao dịch (HOSE, HNX, UPCOM), chỉ số HNX30, ETF, chứng quyền (CW), trái phiếu (BOND),\n        và phái sinh (DER).\n\n        Để xem danh sách tất cả các nhóm được hỗ trợ, gọi `get_supported_groups()`.\n\n        Args:\n            group: Tên nhóm được hỗ trợ. Mặc định 'VN30'.\n                   Ví dụ: 'VN30', 'VN100', 'HOSE', 'HNX', 'UPCOM', 'ETF', 'BOND', 'CW', 'FU_INDEX'.\n            show_log: Hiển thị log debug. Mặc định False.\n\n        Returns:\n            Series chứa mã chứng khoán theo nhóm.\n\n        Raises:\n            ValueError: Nếu tên nhóm không hợp lệ.\n\n        Example:\n            >>> from vnstock_data.explorer.kbs import Listing\n            >>> kbs = Listing()\n            >>> # Lấy danh sách VN30\n            >>> vn30 = kbs.symbols_by_group('VN30')\n            >>> # Lấy tất cả ETF\n            >>> etf_symbols = kbs.symbols_by_group('ETF')\n            >>> # Xem tất cả nhóm được hỗ trợ\n            >>> groups = kbs.get_supported_groups()\n        ";A=group
		if A not in _GROUP_CODE:raise ValueError(bytes([78,104,195,179,109,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,83,225,187,173,32,100,225,187,165,110,103,32,103,101,116,95,115,117,112,112,111,114,116,101,100,95,103,114,111,117,112,115,40,41,32,196,145,225,187,131,32,120,101,109,32,100,97,110,104,32,115,195,161,99,104,32,110,104,195,179,109,32,196,145,198,176,225,187,163,99,32,104,225,187,151,32,116,114,225,187,163,46]).decode())
		C=self._get_symbols_by_group_internal(group=A,show_log=show_log);B=pd.Series(C,name=bytes([115,121,109,98,111,108]).decode());B.attrs[bytes([115,111,117,114,99,101]).decode()]=self.data_source;B.attrs[bytes([103,114,111,117,112]).decode()]=A;return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def industries_icb(self,show_log=False):'\n        Truy xuất thông tin danh sách các ngành công nghiệp.\n\n        Note: **KBS không cung cấp ICB classification.**\n        \n        Để lấy danh sách mã theo ngành, hãy sử dụng `symbols_by_industries()`.\n\n        Raises:\n            NotImplementedError: KBS không hỗ trợ ICB classification.\n        ';raise NotImplementedError(bytes([75,66,83,32,107,104,195,180,110,103,32,99,117,110,103,32,99,225,186,165,112,32,73,67,66,32,99,108,97,115,115,105,102,105,99,97,116,105,111,110,46,32,83,225,187,173,32,100,225,187,165,110,103,32,115,121,109,98,111,108,115,95,98,121,95,105,110,100,117,115,116,114,105,101,115,40,41,32,196,145,225,187,131,32,108,225,186,165,121,32,109,195,163,32,116,104,101,111,32,110,103,195,160,110,104,46]).decode())
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def get_supported_groups(self):"\n        Liệt kê tất cả các nhóm/sàn được hỗ trợ bởi phương thức symbols_by_group().\n\n        Các mô tả chỉ số tuân theo chuẩn của vnstock library.\n\n        Returns:\n            DataFrame với các cột:\n            - group_name: Tên nhóm có thể truyền vào symbols_by_group()\n            - group_code: Mã nội bộ của KBS\n            - category: Danh mục (Chỉ số VN, Sàn giao dịch, ETF/Quỹ, Chứng quyền, Trái phiếu, Phái sinh)\n            - description: Mô tả chi tiết theo chuẩn vnstock\n\n        Example:\n            >>> from vnstock_data.explorer.kbs import Listing\n            >>> kbs = Listing()\n            >>> groups = kbs.get_supported_groups()\n            >>> print(groups)\n            >>> # Lọc chỉ các chỉ số VN\n            >>> vn_indices = groups[groups['category'] == 'Chỉ số VN']\n        ";B={(bytes([86,78,51,48]).decode(),bytes([51,48]).decode(),bytes([67,104,225,187,137,32,115,225,187,145,32,86,78]).decode(),bytes([51,48,32,99,225,187,149,32,112,104,105,225,186,191,117,32,118,225,187,145,110,32,104,195,179,97,32,108,225,187,155,110,32,110,104,225,186,165,116,32,38,32,116,104,97,110,104,32,107,104,111,225,186,163,110,32,116,225,187,145,116,32,110,104,225,186,165,116,32,72,79,83,69]).decode()),(bytes([86,78,49,48,48]).decode(),bytes([49,48,48]).decode(),bytes([67,104,225,187,137,32,115,225,187,145,32,86,78]).decode(),bytes([49,48,48,32,99,225,187,149,32,112,104,105,225,186,191,117,32,99,195,179,32,118,225,187,145,110,32,104,111,195,161,32,108,225,187,155,110,32,110,104,225,186,165,116,32,72,79,83,69]).decode()),(bytes([86,78,77,105,100,67,97,112]).decode(),bytes([77,73,68]).decode(),bytes([67,104,225,187,137,32,115,225,187,145,32,86,78]).decode(),bytes([77,105,100,45,67,97,112,32,73,110,100,101,120,32,45,32,110,104,195,179,109,32,99,225,187,149,32,112,104,105,225,186,191,117,32,118,225,187,145,110,32,104,195,179,97,32,116,114,117,110,103,32,98,195,172,110,104]).decode()),(bytes([86,78,83,109,97,108,108,67,97,112]).decode(),bytes([83,77,76]).decode(),bytes([67,104,225,187,137,32,115,225,187,145,32,86,78]).decode(),bytes([83,109,97,108,108,45,67,97,112,32,73,110,100,101,120,32,45,32,110,104,195,179,109,32,99,225,187,149,32,112,104,105,225,186,191,117,32,118,225,187,145,110,32,104,195,179,97,32,110,104,225,187,143]).decode()),(bytes([86,78,83,73]).decode(),bytes([83,73]).decode(),bytes([67,104,225,187,137,32,115,225,187,145,32,86,78]).decode(),bytes([86,105,101,116,110,97,109,32,83,109,97,108,108,45,67,97,112,32,73,110,100,101,120]).decode()),(bytes([86,78,88,53,48]).decode(),bytes([88,53,48]).decode(),bytes([67,104,225,187,137,32,115,225,187,145,32,86,78]).decode(),bytes([53,48,32,99,225,187,149,32,112,104,105,225,186,191,117,32,118,225,187,145,110,32,104,195,179,97,32,108,225,187,155,110,32,110,104,225,186,165,116,32,116,114,195,170,110,32,116,111,195,160,110,32,98,225,187,153,32,116,104,225,187,139,32,116,114,198,176,225,187,157,110,103,32,72,79,83,69,32,118,195,160,32,72,78,88]).decode()),(bytes([86,78,88,65,76,76]).decode(),bytes([88,65,76,76]).decode(),bytes([67,104,225,187,137,32,115,225,187,145,32,86,78]).decode(),bytes([84,225,186,165,116,32,99,225,186,163,32,99,225,187,149,32,112,104,105,225,186,191,117,32,116,114,195,170,110,32,116,111,195,160,110,32,98,225,187,153,32,116,104,225,187,139,32,116,114,198,176,225,187,157,110,103,32,72,79,83,69,32,118,195,160,32,72,78,88]).decode()),(bytes([86,78,65,76,76]).decode(),bytes([65,76,76]).decode(),bytes([67,104,225,187,137,32,115,225,187,145,32,86,78]).decode(),bytes([84,225,186,165,116,32,99,225,186,163,32,99,225,187,149,32,112,104,105,225,186,191,117,32,116,114,195,170,110,32,72,79,83,69,32,118,195,160,32,72,78,88]).decode()),(bytes([72,78,88,51,48]).decode(),bytes([72,78,88,51,48]).decode(),bytes([67,104,225,187,137,32,115,225,187,145,32,86,78]).decode(),bytes([67,104,225,187,137,32,115,225,187,145,32,51,48,32,99,225,187,149,32,112,104,105,225,186,191,117,32,104,195,160,110,103,32,196,145,225,186,167,117,32,72,78,88]).decode()),(bytes([72,79,83,69]).decode(),bytes([72,79,83,69]).decode(),bytes([83,195,160,110,32,103,105,97,111,32,100,225,187,139,99,104]).decode(),bytes([83,225,187,159,32,103,105,97,111,32,100,225,187,139,99,104,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,32,84,80,46,32,72,225,187,147,32,67,104,195,173,32,77,105,110,104]).decode()),(bytes([72,78,88]).decode(),bytes([72,78,88]).decode(),bytes([83,195,160,110,32,103,105,97,111,32,100,225,187,139,99,104]).decode(),bytes([83,195,160,110,32,71,105,97,111,32,100,225,187,139,99,104,32,67,104,225,187,169,110,103,32,107,104,111,195,161,110,32,72,195,160,32,78,225,187,153,105]).decode()),(bytes([85,80,67,79,77]).decode(),bytes([85,80,67,79,77]).decode(),bytes([83,195,160,110,32,103,105,97,111,32,100,225,187,139,99,104]).decode(),bytes([83,195,160,110,32,71,105,97,111,32,100,225,187,139,99,104,32,79,84,67,32,40,85,80,67,111,77,32,45,32,85,110,108,105,115,116,101,100,32,80,117,98,108,105,99,32,67,111,109,112,97,110,121,32,77,97,114,107,101,116,41]).decode()),(bytes([69,84,70]).decode(),bytes([70,85,78,68]).decode(),bytes([69,84,70,47,81,117,225,187,185]).decode(),bytes([69,120,99,104,97,110,103,101,45,84,114,97,100,101,100,32,70,117,110,100,32,45,32,81,117,225,187,185,32,99,104,225,187,137,32,115,225,187,145,32,118,195,160,32,113,117,225,187,185,32,116,114,97,111,32,196,145,225,187,149,105]).decode()),(bytes([67,87]).decode(),bytes([67,87]).decode(),bytes([67,104,225,187,169,110,103,32,113,117,121,225,187,129,110]).decode(),bytes([67,111,118,101,114,101,100,32,87,97,114,114,97,110,116,32,45,32,67,104,225,187,169,110,103,32,113,117,121,225,187,129,110,32,112,104,195,161,116,32,104,195,160,110,104,32,98,225,187,159,105,32,99,195,161,99,32,116,225,187,149,32,99,104,225,187,169,99,32,116,195,160,105,32,99,104,195,173,110,104]).decode()),(bytes([66,79,78,68]).decode(),bytes([66,79,78,68]).decode(),bytes([84,114,195,161,105,32,112,104,105,225,186,191,117]).decode(),bytes([67,111,114,112,111,114,97,116,101,32,66,111,110,100,32,45,32,84,114,195,161,105,32,112,104,105,225,186,191,117,32,100,111,97,110,104,32,110,103,104,105,225,187,135,112,32,110,105,195,170,109,32,121,225,186,191,116]).decode()),(bytes([70,85,95,73,78,68,69,88]).decode(),bytes([68,69,82]).decode(),bytes([80,104,195,161,105,32,115,105,110,104]).decode(),bytes([70,117,116,117,114,101,115,32,45,32,72,225,187,163,112,32,196,145,225,187,147,110,103,32,116,198,176,198,161,110,103,32,108,97,105,32,99,104,225,187,137,32,115,225,187,145]).decode())};C=[{bytes([103,114,111,117,112,95,110,97,109,101]).decode():A,bytes([103,114,111,117,112,95,99,111,100,101]).decode():B,bytes([99,97,116,101,103,111,114,121]).decode():C,bytes([100,101,115,99,114,105,112,116,105,111,110]).decode():D}for(A,B,C,D)in sorted(B)];A=pd.DataFrame(C);A.attrs[bytes([115,111,117,114,99,101]).decode()]=self.data_source;return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def all_future_indices(self,show_log=False):'\n        Truy xuất danh sách mã phái sinh hợp đồng tương lai.\n\n        Args:\n            show_log: Hiển thị log debug. Mặc định False.\n\n        Returns:\n            Series chứa mã phái sinh.\n        ';return self.symbols_by_group(group=bytes([70,85,95,73,78,68,69,88]).decode(),show_log=show_log)
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def all_covered_warrant(self,show_log=False):'\n        Truy xuất danh sách mã chứng quyền.\n\n        Args:\n            show_log: Hiển thị log debug. Mặc định False.\n\n        Returns:\n            Series chứa mã chứng quyền.\n        ';return self.symbols_by_group(group=bytes([67,87]).decode(),show_log=show_log)
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def all_bonds(self,show_log=False):'\n        Truy xuất danh sách mã trái phiếu.\n\n        Args:\n            show_log: Hiển thị log debug. Mặc định False.\n\n        Returns:\n            Series chứa mã trái phiếu.\n        ';return self.symbols_by_group(group=bytes([66,79,78,68]).decode(),show_log=show_log)
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def all_etf(self,show_log=False):'\n        Truy xuất danh sách mã quỹ ETF.\n\n        Args:\n            show_log: Hiển thị log debug. Mặc định False.\n\n        Returns:\n            Series chứa mã ETF.\n        ';return self.symbols_by_group(group=bytes([69,84,70]).decode(),show_log=show_log)
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def all_government_bonds(self,show_log=False):'\n        Truy xuất danh sách mã trái phiếu chính phủ.\n\n        Note: **KBS không cung cấp dữ liệu trái phiếu chính phủ.**\n\n        Để lấy danh sách trái phiếu doanh nghiệp, hãy sử dụng `all_bonds()`.\n\n        Raises:\n            NotImplementedError: KBS không hỗ trợ trái phiếu chính phủ.\n        ';raise NotImplementedError(bytes([75,66,83,32,107,104,195,180,110,103,32,99,117,110,103,32,99,225,186,165,112,32,100,225,187,175,32,108,105,225,187,135,117,32,116,114,195,161,105,32,112,104,105,225,186,191,117,32,99,104,195,173,110,104,32,112,104,225,187,167,46,32,83,225,187,173,32,100,225,187,165,110,103,32,97,108,108,95,98,111,110,100,115,40,41,32,196,145,225,187,131,32,108,225,186,165,121,32,116,114,195,161,105,32,112,104,105,225,186,191,117,32,100,111,97,110,104,32,110,103,104,105,225,187,135,112,46]).decode())
	def _get_full_stock_data(B,show_log=False):
		'\n        Internal method để lấy dữ liệu đầy đủ về tất cả chứng khoán từ /stock/search/data endpoint.\n\n        Trả về danh sách chứng khoán với tất cả thông tin: symbol, name, nameEn, exchange, \n        type, index, re, ceiling, floor.\n\n        Args:\n            show_log: Hiển thị log debug. Mặc định False.\n\n        Returns:\n            List[Dict] chứa thông tin đầy đủ của tất cả chứng khoán, hoặc [] nếu lỗi.\n        ';D=show_log;E=_SEARCH_URL
		try:
			A=send_request(url=E,headers=B.headers,method=bytes([71,69,84]).decode(),payload=None,show_log=D,proxy_list=B.proxy_config.proxy_list,proxy_mode=B.proxy_config.proxy_mode,request_mode=B.proxy_config.request_mode)
			if not A:raise ValueError(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,100,225,187,175,32,108,105,225,187,135,117,32,99,104,225,187,169,110,103,32,107,104,111,195,161,110,46]).decode())
			if isinstance(A,list):C=A
			elif isinstance(A,dict)and bytes([100,97,116,97]).decode()in A:C=A[bytes([100,97,116,97]).decode()]
			else:C=[]
			if D:logger.info(f"Truy xuất thành công {len(C)} chứng khoán.")
			return C
		except Exception as F:
			if D:logger.error(f"Lỗi khi lấy dữ liệu chứng khoán: {F!s}")
			return[]
	def _get_symbols_by_group_internal(C,group,show_log=False):
		'\n        Internal method để lấy danh sách mã theo nhóm/sàn.\n\n        Args:\n            group: Tên nhóm hoặc sàn.\n            show_log: Hiển thị log debug.\n\n        Returns:\n            List[str] chứa danh sách mã.\n        ';E=show_log;B=group;F=_GROUP_CODE.get(B,B);G=f"{_IIS_BASE_URL}/index/{F}/stocks"
		try:
			A=send_request(url=G,headers=C.headers,method=bytes([71,69,84]).decode(),payload=None,show_log=E,proxy_list=C.proxy_config.proxy_list,proxy_mode=C.proxy_config.proxy_mode,request_mode=C.proxy_config.request_mode)
			if not A:raise ValueError(f"Không tìm thấy dữ liệu cho nhóm {B}.")
			if isinstance(A,dict)and bytes([100,97,116,97]).decode()in A:D=A[bytes([100,97,116,97]).decode()]
			elif isinstance(A,list):D=A
			else:D=[]
			if E:logger.info(f"Truy xuất thành công {len(D)} mã từ nhóm {B}.")
			return D
		except Exception as H:
			if E:logger.error(f"Lỗi khi lấy dữ liệu từ nhóm {B}: {H!s}")
			raise
	def _get_industries_internal(B,show_log=False):
		'\n        Internal method để lấy danh sách các ngành.\n\n        Args:\n            show_log: Hiển thị log debug.\n\n        Returns:\n            List[Dict] chứa thông tin ngành.\n        ';D=show_log;E=f"{_SECTOR_ALL_URL}"
		try:
			A=send_request(url=E,headers=B.headers,method=bytes([71,69,84]).decode(),payload=None,show_log=D,proxy_list=B.proxy_config.proxy_list,proxy_mode=B.proxy_config.proxy_mode,request_mode=B.proxy_config.request_mode)
			if not A:raise ValueError(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,100,225,187,175,32,108,105,225,187,135,117,32,110,103,195,160,110,104,46]).decode())
			if isinstance(A,list):C=A
			elif isinstance(A,dict)and bytes([100,97,116,97]).decode()in A:C=A[bytes([100,97,116,97]).decode()]
			else:C=[]
			if D:logger.info(f"Truy xuất thành công {len(C)} ngành.")
			return C
		except Exception as F:
			if D:logger.error(f"Lỗi khi lấy danh sách ngành: {F!s}")
			return[]
	def _get_symbols_by_industry_internal(B,industry_code,show_log=False):
		'\n        Internal method để lấy danh sách mã theo mã ngành.\n\n        Args:\n            industry_code: Mã ngành.\n            show_log: Hiển thị log debug.\n\n        Returns:\n            List[str] chứa danh sách mã.\n        ';E=show_log;D=industry_code;F=f"{_SECTOR_ALL_URL}?code={D}&l=1"
		try:
			A=send_request(url=F,headers=B.headers,method=bytes([71,69,84]).decode(),payload=None,show_log=E,proxy_list=B.proxy_config.proxy_list,proxy_mode=B.proxy_config.proxy_mode,request_mode=B.proxy_config.request_mode)
			if not A:return[]
			if isinstance(A,dict)and bytes([100,97,116,97]).decode()in A:C=A[bytes([100,97,116,97]).decode()]
			elif isinstance(A,list):C=A
			else:C=[]
			if E:logger.info(f"Truy xuất thành công {len(C)} mã từ ngành {D}.")
			return C
		except Exception as G:
			if E:logger.error(f"Lỗi khi lấy mã từ ngành {D}: {G!s}")
			return[]
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def all_indices(self,show_log=False):'\n        Lấy danh sách tất cả các chỉ số tiêu chuẩn hóa với thông tin\n        đầy đủ từ dữ liệu HOSE.\n\n        Returns:\n            DataFrame: Columns [symbol, name, description, full_name,\n                                group, index_id, sector_id (for sectors)]\n        ';return market_indices.get_all_indices()
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def indices_by_group(self,group,show_log=False):"\n        Lấy danh sách chỉ số theo nhóm tiêu chuẩn hóa từ dữ liệu HOSE.\n\n        Args:\n            group: Tên nhóm (VD: 'HOSE Indices', 'Sector Indices', etc.)\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame: Danh sách chỉ số trong nhóm hoặc None\n                       (Sector indices include sector_id mapping)\n        ";return market_indices.get_indices_by_group(group)
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([108,105,115,116,105,110,103]).decode(),bytes([107,98,115]).decode(),Listing)