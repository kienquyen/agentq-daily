from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo
import pandas as pd
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.lookback import get_start_date_from_lookback
from.spl_fetcher import SPLFetcher
logger=get_logger(__name__)
class CommodityPrice:
	'\n    Lớp cung cấp các phương thức để lấy dữ liệu giá hàng hóa từ nguồn SPL.\n    '
	def __init__(A,start=None,end=None,length=None,show_log=False):
		"\n        Khởi tạo đối tượng CommodityPrice với tùy chọn ngày bắt đầu và kết thúc mặc định.\n\n        Các tham số:\n            start (str, optional): Ngày bắt đầu mặc định (định dạng 'YYYY-MM-DD'). Mặc định là None.\n            end (str, optional): Ngày kết thúc mặc định (định dạng 'YYYY-MM-DD'). Mặc định là None.\n            length (str, int, optional): Khoảng thời gian mặc định cần lấy dữ liệu. Mặc định là '1Y'.\n        ";B=length;A.fetcher=SPLFetcher();A.default_start=start;A.default_end=end;A.default_length=B if B is not None else bytes([49,89]).decode()
		if not show_log:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	def _fetch_commodity(B,ticker,start=None,end=None,interval=bytes([49,100]).decode(),columns=None,length=None):
		"\n        Lấy dữ liệu giá hàng hóa từ API SPL.\n\n        Các tham số:\n            ticker (str): Mã hàng hóa cần lấy dữ liệu.\n            start (str, optional): Ngày bắt đầu (định dạng 'YYYY-MM-DD').\n                Ưu tiên tham số nếu có, mặc định là giá trị khởi tạo.\n            end (str, optional): Ngày kết thúc (định dạng 'YYYY-MM-DD').\n                Ưu tiên tham số nếu có, mặc định là giá trị khởi tạo.\n            interval (str, optional): Khoảng thời gian (mặc định '1d').\n            columns (List, optional): Danh sách cột cần lấy.\n                Mặc định là None (lấy tất cả).\n        \n        Giá trị trả về:\n            pd.DataFrame: Dữ liệu giá hàng hóa với time làm index.\n        ";N=columns;G=end;F=start;C=length;D=G or B.default_end
		if D is None:D=datetime.now().strftime(bytes([37,89,45,37,109,45,37,100]).decode())
		E=F
		if E is None:
			K=C if C is not None else B.default_length
			if K is not None:
				if str(K).isdigit():E=get_start_date_from_lookback(lookback_length=bytes([50,48,89]).decode(),end_date=D)
				else:
					H=str(K).upper()
					if H.endswith(bytes([66]).decode()):H=H[:-1]+bytes([68]).decode()
					E=get_start_date_from_lookback(lookback_length=H,end_date=D)
			else:E=B.default_start
		I={bytes([116,105,99,107,101,114]).decode():ticker,bytes([105,110,116,101,114,118,97,108]).decode():interval,bytes([116,121,112,101]).decode():bytes([99,111,109,109,111,100,105,116,121]).decode()};J=ZoneInfo(bytes([65,115,105,97,47,72,111,95,67,104,105,95,77,105,110,104]).decode());F=E;G=D
		if F:L=datetime.strptime(F,bytes([37,89,45,37,109,45,37,100]).decode());L=L.replace(hour=0,minute=0,second=0,microsecond=0,tzinfo=J);I[bytes([102,114,111,109]).decode()]=int(L.timestamp())
		if G:M=datetime.strptime(G,bytes([37,89,45,37,109,45,37,100]).decode());M=M.replace(hour=23,minute=59,second=59,microsecond=999999,tzinfo=J);I[bytes([116,111]).decode()]=int(M.timestamp())
		B.fetcher.validate(I);O=B.fetcher.fetch(endpoint=bytes([47,104,105,115,116,111,114,105,99,97,108,47,112,114,105,99,101,115,47,111,104,108,99,118]).decode(),params=I);A=B.fetcher.to_dataframe(O[bytes([100,97,116,97]).decode()]);A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()])
		if A[bytes([116,105,109,101]).decode()].dt.tz is None:A[bytes([116,105,109,101]).decode()]=A[bytes([116,105,109,101]).decode()].dt.tz_localize(J)
		else:A[bytes([116,105,109,101]).decode()]=A[bytes([116,105,109,101]).decode()].dt.tz_convert(J)
		A[bytes([116,105,109,101]).decode()]=A[bytes([116,105,109,101]).decode()].dt.tz_localize(None).dt.normalize();A.set_index(bytes([116,105,109,101]).decode(),inplace=True)
		if N is not None:A=A[N]
		if C is not None and str(C).isdigit():A=A.tail(int(C)).copy()
		return A
	def _gold_vn_buy(A,start=None,end=None,length=None):'Lấy giá vàng Việt Nam (mua vào).';return A._fetch_commodity(bytes([71,79,76,68,58,86,78,58,66,85,89]).decode(),start,end,columns=[bytes([99,108,111,115,101]).decode()],length=length)
	def _gold_vn_sell(A,start=None,end=None,length=None):'Lấy giá vàng Việt Nam (bán ra).';return A._fetch_commodity(bytes([71,79,76,68,58,86,78,58,83,69,76,76]).decode(),start,end,columns=[bytes([99,108,111,115,101]).decode()],length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def gold_vn(self,start=None,end=None,length=None):'Lấy giá vàng Việt Nam.';C=length;B=start;D=self._gold_vn_buy(B,end,length=C);E=self._gold_vn_sell(B,end,length=C);A=pd.concat([D,E],axis=1);A.columns=[bytes([98,117,121]).decode(),bytes([115,101,108,108]).decode()];A=A.ffill();return A
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def gold_global(self,start=None,end=None,length=None):'Lấy giá vàng thế giới.';return self._fetch_commodity(bytes([71,67,61,70]).decode(),start,end,length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def _gas_ron92(self,start=None,end=None,length=None):'Lấy giá xăng RON92 tại Việt Nam.';return self._fetch_commodity(bytes([71,65,83,58,82,79,78,57,50,58,86,78]).decode(),start,end,columns=[bytes([99,108,111,115,101]).decode()],length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def _gas_ron95(self,start=None,end=None,length=None):'Lấy giá xăng RON95 tại Việt Nam.';return self._fetch_commodity(bytes([71,65,83,58,82,79,78,57,53,58,86,78]).decode(),start,end,columns=[bytes([99,108,111,115,101]).decode()],length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def _oil_do(self,start=None,end=None,length=None):'Lấy giá dầu DO tại Việt Nam.';return self._fetch_commodity(bytes([71,65,83,58,68,79,58,86,78]).decode(),start,end,columns=[bytes([99,108,111,115,101]).decode()],length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def gas_vn(self,start=None,end=None,length=None):'Lấy giá xăng và dầu DO tại Việt Nam.';E=length;D=end;C=start;B=self;F=B._gas_ron92(C,D,length=E);G=B._gas_ron95(C,D,length=E);H=B._oil_do(C,D,length=E);A=pd.concat([G,F,H],axis=1);A.columns=[bytes([114,111,110,57,53]).decode(),bytes([114,111,110,57,50]).decode(),bytes([111,105,108,95,100,111]).decode()];A=A.ffill();return A
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def oil_crude(self,start=None,end=None,length=None):'Lấy giá dầu thô.';return self._fetch_commodity(bytes([67,76,61,70]).decode(),start,end,length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def gas_natural(self,start=None,end=None,length=None):'Lấy giá khí thiên nhiên.';return self._fetch_commodity(bytes([78,71,61,70]).decode(),start,end,length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def coke(self,start=None,end=None,length=None):'Lấy giá than cốc.';return self._fetch_commodity(bytes([73,67,69,69,85,82,58,78,67,70,49,33]).decode(),start,end,length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def steel_d10(self,start=None,end=None,length=None):'Lấy giá thép D10 tại Việt Nam.';return self._fetch_commodity(bytes([83,84,69,69,76,58,68,49,48,58,86,78]).decode(),start,end,columns=[bytes([99,108,111,115,101]).decode()],length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def iron_ore(self,start=None,end=None,length=None):'Lấy giá quặng sắt.';return self._fetch_commodity(bytes([67,79,77,69,88,58,84,73,79,49,33]).decode(),start,end,length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def steel_hrc(self,start=None,end=None,length=None):'Lấy giá thép HRC.';return self._fetch_commodity(bytes([67,79,77,69,88,58,72,82,67,49,33]).decode(),start,end,length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def fertilizer_ure(self,start=None,end=None,length=None):'Lấy giá phân ure.';return self._fetch_commodity(bytes([67,66,79,84,58,85,77,69,49,33]).decode(),start,end,length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def soybean(self,start=None,end=None,length=None):'Lấy giá đậu tương.';return self._fetch_commodity(bytes([90,77,61,70]).decode(),start,end,length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def corn(self,start=None,end=None,length=None):'Lấy giá ngô (bắp).';return self._fetch_commodity(bytes([90,67,61,70]).decode(),start,end,length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def sugar(self,start=None,end=None,length=None):'Lấy giá đường.';return self._fetch_commodity(bytes([83,66,61,70]).decode(),start,end,length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def pork_north_vn(self,start=None,end=None,length=None):'Lấy giá heo hơi miền Bắc Việt Nam.';return self._fetch_commodity(bytes([80,73,71,58,78,79,82,84,72,58,86,78]).decode(),start,end,columns=[bytes([99,108,111,115,101]).decode()],length=length)
	@agg_execution(bytes([83,80,76,46,101,120,116]).decode())
	def pork_china(self,start=None,end=None,length=None):'Lấy giá heo hơi Trung Quốc.';return self._fetch_commodity(bytes([80,73,71,58,67,72,73,78,65]).decode(),start,end,columns=[bytes([99,108,111,115,101]).decode()],length=length)
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([99,111,109,109,111,100,105,116,121]).decode(),bytes([115,112,108]).decode(),CommodityPrice)