'Financial module for KB Securities (KBS) data source.'
import logging
from enum import Enum
import pandas as pd
from vnai import agg_execution
from vnstock_data.core.utils.client import ProxyConfig,send_request
from vnstock_data.core.utils.parser import get_asset_type,vn_to_snake_case
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.kbs.const import _BALANCE_SHEET_MAP,_CASH_FLOW_MAP,_FINANCIAL_RATIOS_MAP,_INCOME_STATEMENT_MAP,_SAS_FINANCE_INFO_URL
logger=logging.getLogger(__name__)
class FieldDisplayMode(Enum):'Field display modes.';STD=bytes([115,116,100]).decode();ALL=bytes([97,108,108]).decode();AUTO=bytes([97,117,116,111]).decode()
class Finance:
	'\n    Lớp truy cập dữ liệu tài chính từ KB Securities (KBS).\n    '
	def __init__(A,symbol,period=None,random_agent=False,proxy_config=None,show_log=False,standardize_columns=True,proxy_mode=None,proxy_list=None):
		"\n        Khởi tạo Finance client cho KBS.\n\n        Args:\n            symbol: Mã chứng khoán (VD: 'ACB', 'VNM').\n            period: Kỳ báo cáo mặc định ('year', 'quarter' hoặc None).\n            random_agent: Sử dụng user agent ngẫu nhiên. Mặc định False.\n            proxy_config: Cấu hình proxy. Mặc định None.\n            show_log: Hiển thị log debug. Mặc định False.\n            standardize_columns: Chuẩn hoá tên cột theo schema. Mặc định True.\n            proxy_mode: Chế độ proxy (try, rotate, random, single). Mặc định None.\n            proxy_list: Danh sách proxy URLs. Mặc định None.\n\n        Raises:\n            ValueError: Nếu mã không phải là cổ phiếu.\n        ";F=proxy_mode;E=show_log;D=proxy_config;C=proxy_list;B=period;A.symbol=symbol.upper();A.asset_type=get_asset_type(A.symbol)
		if B is not None and B not in[bytes([121,101,97,114]).decode(),bytes([113,117,97,114,116,101,114]).decode()]:raise ValueError(bytes([75,225,187,179,32,98,195,161,111,32,99,195,161,111,32,116,195,160,105,32,99,104,195,173,110,104,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,104,225,186,165,112,32,110,104,225,186,173,110,32,39,121,101,97,114,39,32,104,111,225,186,183,99,32,39,113,117,97,114,116,101,114,39,32,104,111,225,186,183,99,32,78,111,110,101,46]).decode())
		A.period=B
		if A.asset_type not in[bytes([115,116,111,99,107]).decode()]:raise ValueError(bytes([77,195,163,32,67,75,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,32,104,111,225,186,183,99,32,107,104,195,180,110,103,32,112,104,225,186,163,105,32,99,225,187,149,32,112,104,105,225,186,191,117,46]).decode())
		A.data_source=bytes([75,66,83]).decode();A.headers=get_headers(data_source=A.data_source,random_agent=random_agent);A.show_log=E;A.standardize_columns=standardize_columns
		if D is None:
			H=F if F else bytes([116,114,121]).decode();G=bytes([100,105,114,101,99,116]).decode()
			if C and len(C)>0:G=bytes([112,114,111,120,121]).decode()
			A.proxy_config=ProxyConfig(proxy_mode=H,proxy_list=C,request_mode=G)
		else:A.proxy_config=D
		if E:logger.setLevel(bytes([73,78,70,79]).decode())
		else:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	def _get_column_mapping(B,report_type):'\n        Lấy column mapping cho loại báo cáo.\n        \n        Args:\n            report_type: Loại báo cáo (income_statement, balance_sheet, cash_flow, financial_ratios)\n            \n        Returns:\n            Dictionary chứa mapping từ cột gốc sang cột chuẩn hoá\n        ';A={bytes([105,110,99,111,109,101,95,115,116,97,116,101,109,101,110,116]).decode():_INCOME_STATEMENT_MAP,bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode():_BALANCE_SHEET_MAP,bytes([99,97,115,104,95,102,108,111,119]).decode():_CASH_FLOW_MAP,bytes([102,105,110,97,110,99,105,97,108,95,114,97,116,105,111,115]).decode():_FINANCIAL_RATIOS_MAP};return A.get(report_type,{})
	def _parse_financial_response(q,response,report_key,include_metadata=False):
		"\n        Parse KBS API response and extract financial data with proper structure.\n        \n        Args:\n            response: API response containing Audit, Unit, Head, Content\n            report_key: Key in Content (e.g., 'Kết quả kinh doanh')\n            include_metadata: Whether to include Audit and Unit info as rows in DataFrame\n            \n        Returns:\n            DataFrame with proper financial data structure\n        ";W=report_key;F=response;X=F.get(bytes([65,117,100,105,116]).decode(),[]);Y=F.get(bytes([85,110,105,116]).decode(),[]);Z=F.get(bytes([72,101,97,100]).decode(),[]);i=F.get(bytes([67,111,110,116,101,110,116]).decode(),{});a=i.get(W,[])
		if not a:return pd.DataFrame()
		G=[];N={};O={}
		if Z:
			j=sorted(Z,key=lambda x:x.get(bytes([73,68]).decode(),0))
			for E in j:
				if isinstance(E,dict):
					b=E.get(bytes([89,101,97,114,80,101,114,105,111,100]).decode(),'');P=E.get(bytes([84,101,114,109,78,97,109,101]).decode(),'')
					if P and bytes([81,117,195,189]).decode()in P:k=P.replace(bytes([81,117,195,189]).decode(),'').strip();C=f"{b}-Q{k}"
					else:C=str(b)
					G.append(C);N[C]=E.get(bytes([65,117,100,105,116,101,100,83,116,97,116,117,115]).decode(),'');O[C]=E.get(bytes([85,110,105,116,101,100]).decode(),'')
		Q={}
		if X:
			for R in X:
				if isinstance(R,dict):Q[R.get(bytes([65,117,100,105,116,101,100,83,116,97,116,117,115,67,111,100,101]).decode())]=R.get(bytes([68,101,115,99,114,105,112,116,105,111,110]).decode())
		S={}
		if Y:
			for T in Y:
				if isinstance(T,dict):S[T.get(bytes([85,110,105,116,101,100,67,111,100,101]).decode())]=T.get(bytes([85,110,105,116,101,100,78,97,109,101]).decode())
		H=[];I={}
		for D in a:
			J=D.get(bytes([78,97,109,101]).decode(),'');K=D.get(bytes([78,97,109,101,69,110]).decode(),'')
			if K and K.strip():A=vn_to_snake_case(K)
			elif J and J.strip():A=vn_to_snake_case(J)
			else:A=''
			if A and A in I:I[A]+=1;A=A+bytes([95]).decode()+str(I[A])
			elif A:I[A]=1
			c={bytes([105,116,101,109]).decode():J,bytes([105,116,101,109,95,101,110]).decode():K,bytes([105,116,101,109,95,105,100]).decode():A,bytes([117,110,105,116]).decode():D.get(bytes([85,110,105,116]).decode(),''),bytes([108,101,118,101,108,115]).decode():D.get(bytes([76,101,118,101,108,115]).decode(),0),bytes([114,111,119,95,110,117,109,98,101,114]).decode():D.get(bytes([73,68]).decode(),0)}
			for(l,C)in enumerate(G,1):
				m=f"Value{l}";L=D.get(m)
				if L is not None:
					try:L=float(L)
					except(ValueError,TypeError):pass
				c[C]=L
			H.append(c)
		if include_metadata:
			d={bytes([105,116,101,109]).decode():bytes([75,105,225,187,131,109,32,116,111,195,161,110]).decode(),bytes([105,116,101,109,95,101,110]).decode():bytes([65,117,100,105,116,32,83,116,97,116,117,115]).decode(),bytes([105,116,101,109,95,105,100]).decode():bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode(),bytes([117,110,105,116]).decode():'',bytes([108,101,118,101,108,115]).decode():0,bytes([114,111,119,95,110,117,109,98,101,114]).decode():-2};e={bytes([105,116,101,109]).decode():bytes([196,144,198,161,110,32,118,225,187,139]).decode(),bytes([105,116,101,109,95,101,110]).decode():bytes([85,110,105,116,32,84,121,112,101]).decode(),bytes([105,116,101,109,95,105,100]).decode():bytes([117,110,105,116,95,116,121,112,101]).decode(),bytes([117,110,105,116]).decode():'',bytes([108,101,118,101,108,115]).decode():0,bytes([114,111,119,95,110,117,109,98,101,114]).decode():-1}
			for M in G:f=N.get(M);d[M]=Q.get(f,f);g=O.get(M);e[M]=S.get(g,g)
			H.append(d);H.append(e)
		B=pd.DataFrame(H);n=[bytes([105,116,101,109]).decode(),bytes([105,116,101,109,95,101,110]).decode(),bytes([105,116,101,109,95,105,100]).decode(),bytes([117,110,105,116]).decode(),bytes([108,101,118,101,108,115]).decode(),bytes([114,111,119,95,110,117,109,98,101,114]).decode()];o=[A for A in n if A in B.columns];p=[A for A in G if A in B.columns];U=[]
		for h in p:
			if not B[h].isnull().all():U.append(h)
		B=B[o+U];V=U;B.attrs[bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()]={A:Q.get(B,B)for(A,B)in N.items()if A in V};B.attrs[bytes([117,110,105,116,95,116,121,112,101]).decode()]={A:S.get(B,B)for(A,B)in O.items()if A in V};B.attrs[bytes([112,101,114,105,111,100,115]).decode()]=V;B.attrs[bytes([114,101,112,111,114,116,95,107,101,121]).decode()]=W;return B
	def _apply_schema_standardization(B,df,report_type):
		'\n        Áp dụng chuẩn hoá schema cho DataFrame.\n        \n        Args:\n            df: DataFrame cần chuẩn hoá\n            report_type: Loại báo cáo\n            \n        Returns:\n            DataFrame với dữ liệu chuẩn hoá\n        ';A=df
		if not B.standardize_columns or A.empty:return A
		C=B._get_column_mapping(report_type)
		if bytes([105,116,101,109,95,105,100]).decode()in A.columns and C:
			E=A[bytes([105,116,101,109,95,105,100]).decode()].isin(C.keys());D=E.sum()
			if D>0:
				A[bytes([105,116,101,109,95,105,100]).decode()]=A[bytes([105,116,101,109,95,105,100]).decode()].replace(C)
				if B.show_log:logger.info(f"Applied schema standardization: {D} items standardized")
		return A
	def _filter_columns_by_lang(G,df,display_mode=FieldDisplayMode.STD):
		"\n        Filter DataFrame columns based on field display mode.\n        \n        Args:\n            df: DataFrame to filter\n            display_mode: Field display mode\n                - FieldDisplayMode.STD: Keep only 'item' and 'item_id' columns (standardized)\n                - FieldDisplayMode.ALL: Keep all item columns (item, item_en, item_id)\n                - FieldDisplayMode.AUTO: Auto-convert based on data type\n                - 'vi': Keep Vietnamese names only (backward compatibility)\n                - 'en': Keep English names only (backward compatibility)\n                - None: Keep all item columns (backward compatibility)\n            \n        Returns:\n            DataFrame with filtered columns\n        ";C=df;A=display_mode
		if C.empty:return C
		if isinstance(A,str):
			if A==bytes([118,105]).decode():A=FieldDisplayMode.STD
			elif A==bytes([101,110]).decode():A=FieldDisplayMode.STD
			else:A=FieldDisplayMode.ALL
		F=C.attrs.get(bytes([112,101,114,105,111,100,115]).decode(),[]);E=[A for A in C.columns if A not in F];D=C.copy()
		if A==FieldDisplayMode.ALL:B=E
		elif A==FieldDisplayMode.AUTO:B=E
		else:
			B=[A for A in E if A in[bytes([105,116,101,109]).decode(),bytes([105,116,101,109,95,105,100]).decode()]]
			if isinstance(A,str)and A==bytes([101,110]).decode()and bytes([105,116,101,109,95,101,110]).decode()in D.columns:D[bytes([105,116,101,109]).decode()]=D[bytes([105,116,101,109,95,101,110]).decode()];B=[bytes([105,116,101,109]).decode(),bytes([105,116,101,109,95,105,100]).decode()]
		B.extend(F);B=[A for A in B if A in D.columns];return D[B]
	def _fetch_financial_data(A,report_type=bytes([75,81,75,68]).decode(),period_type=1,page=1,page_size=4,show_log=False):
		'\n        Lấy dữ liệu tài chính từ API SAS với các tham số chính xác.\n\n        Args:\n            report_type: Loại báo cáo (CDKT, KQKD, LCTT, CSTC, CTKH, BCTT)\n            period_type: Loại kỳ báo cáo (1=năm, 2=quý)\n            page: Trang (mặc định 1)\n            page_size: Số bản ghi trên trang (mặc định 4)\n            show_log: Hiển thị log debug.\n\n        Returns:\n            Dictionary chứa dữ liệu tài chính đầy đủ.\n        ';F=period_type;E=report_type;B=show_log;G=f"{_SAS_FINANCE_INFO_URL}/{A.symbol}";C={bytes([112,97,103,101]).decode():page,bytes([112,97,103,101,83,105,122,101]).decode():page_size,bytes([116,121,112,101]).decode():E,bytes([117,110,105,116]).decode():1000,bytes([116,101,114,109,116,121,112,101]).decode():F}
		if E!=bytes([76,67,84,84]).decode():C[bytes([108,97,110,103,117,97,103,101,105,100]).decode()]=1
		else:C[bytes([99,111,100,101]).decode()]=A.symbol;C[bytes([116,101,114,109,84,121,112,101]).decode()]=F
		if B or A.show_log:logger.info(f"KBS Financial API Request: {A.symbol} - {E} - Period: {F}")
		try:
			D=send_request(url=G,headers=A.headers,method=bytes([71,69,84]).decode(),params=C,show_log=B or A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode)
			if B or A.show_log:
				if isinstance(D,dict)and bytes([100,97,116,97]).decode()in D:logger.info(bytes([65,80,73,32,82,101,115,112,111,110,115,101,32,114,101,99,101,105,118,101,100,58,32]).decode()+str(len(D.get(bytes([100,97,116,97]).decode(),[])))+bytes([32,114,101,99,111,114,100,115]).decode())
			return D
		except Exception as H:
			if B or A.show_log:logger.error(f"API Request Failed: {H!s}")
			raise
	def _fetch_series_data(H,report_type,period_type,report_key,limit=12,include_metadata=False,show_log=False):
		'\n        Helper to fetch data across multiple pages to satisfy the limit.\n        ';C=limit;D=[];I=[];E=1;L=max(C,4)
		while len(I)<C:
			M=H._fetch_financial_data(report_type=report_type,period_type=period_type,page=E,page_size=L,show_log=show_log);F=H._parse_financial_response(M,report_key,include_metadata=include_metadata)
			if F.empty:break
			J=F.attrs.get(bytes([112,101,114,105,111,100,115]).decode(),[])
			if not J:break
			D.append(F);I.extend(J);E+=1
			if E>50:break
		if not D:return pd.DataFrame()
		A=D[0];S=[bytes([105,116,101,109]).decode(),bytes([105,116,101,109,95,101,110]).decode(),bytes([105,116,101,109,95,105,100]).decode(),bytes([117,110,105,116]).decode(),bytes([108,101,118,101,108,115]).decode(),bytes([114,111,119,95,110,117,109,98,101,114]).decode()]
		for N in range(1,len(D)):
			B=D[N];K=B.attrs[bytes([112,101,114,105,111,100,115]).decode()];O=[bytes([105,116,101,109,95,105,100]).decode()]+K
			if bytes([105,116,101,109,95,105,100]).decode()in B.columns:
				P=A.attrs;A=pd.merge(A,B[O],on=bytes([105,116,101,109,95,105,100]).decode(),how=bytes([111,117,116,101,114]).decode());A.attrs=P
				if bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()in B.attrs:
					if bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()not in A.attrs:A.attrs[bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()]={}
					A.attrs[bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()].update(B.attrs[bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()])
				if bytes([117,110,105,116,95,116,121,112,101]).decode()in B.attrs:
					if bytes([117,110,105,116,95,116,121,112,101]).decode()not in A.attrs:A.attrs[bytes([117,110,105,116,95,116,121,112,101]).decode()]={}
					A.attrs[bytes([117,110,105,116,95,116,121,112,101]).decode()].update(B.attrs[bytes([117,110,105,116,95,116,121,112,101]).decode()])
				if bytes([112,101,114,105,111,100,115]).decode()in A.attrs:A.attrs[bytes([112,101,114,105,111,100,115]).decode()].extend(K)
		G=A.attrs[bytes([112,101,114,105,111,100,115]).decode()]
		if len(G)>C:Q=G[:C];R=G[C:];A=A.drop(columns=R,errors=bytes([105,103,110,111,114,101]).decode());A.attrs[bytes([112,101,114,105,111,100,115]).decode()]=Q
		return A
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def income_statement(self,period=None,limit=12,include_metadata=False,display_mode=FieldDisplayMode.STD,show_log=False):
		"\n        Truy xuất báo cáo kết quả kinh doanh (income statement).\n\n        Args:\n            period: Loại kỳ báo cáo ('year' hoặc 'quarter'). Mặc định 'year'.\n            limit: Số kỳ báo cáo tối đa cần lấy. Mặc định 4.\n            include_metadata: Bao gồm thông tin audit và unit trong rows. Mặc định False.\n            display_mode: Chế độ hiển thị trường dữ liệu. Mặc định FieldDisplayMode.STD.\n                - FieldDisplayMode.STD: Chỉ giữ cột 'item' và 'item_id' (đã chuẩn hóa)\n                - FieldDisplayMode.ALL: Giữ tất cả cột item (item, item_en, item_id)\n                - 'vi': Chỉ giữ tên tiếng Việt (tương thích ngược)\n                - 'en': Chỉ giữ tên tiếng Anh (tương thích ngược)\n                - None: Giữ tất cả cột (tương thích ngược)\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa báo cáo kết quả kinh doanh.\n\n        Examples:\n            >>> finance = Finance('ACB')\n            >>> df = finance.income_statement(period='year', display_mode=FieldDisplayMode.STD)\n            >>> # Returns DataFrame with columns: item, item_id, unit, periods...\n            >>> df_all = finance.income_statement(period='year', display_mode=FieldDisplayMode.ALL)\n            >>> # Returns DataFrame with all item columns\n            >>> # Backward compatibility:\n            >>> df_vi = finance.income_statement(period='year', display_mode='vi')\n            >>> df_en = finance.income_statement(period='year', display_mode='en')\n        ";E=show_log;D=period;A=self;C=D if D else A.period if A.period else bytes([121,101,97,114]).decode();G=str(C).lower()
		if G in[bytes([121,101,97,114]).decode(),bytes([121]).decode(),bytes([97,110,110,117,97,108]).decode()]:C=bytes([121,101,97,114]).decode();F=1
		else:C=bytes([113,117,97,114,116,101,114]).decode();F=2
		B=A._fetch_series_data(report_type=bytes([75,81,75,68]).decode(),period_type=F,report_key=bytes([75,225,186,191,116,32,113,117,225,186,163,32,107,105,110,104,32,100,111,97,110,104]).decode(),limit=limit,include_metadata=include_metadata,show_log=E)
		if B.empty:logger.warning(f"Không tìm thấy báo cáo kết quả kinh doanh cho {A.symbol}.");return pd.DataFrame()
		if A.standardize_columns:B=A._apply_schema_standardization(B,bytes([105,110,99,111,109,101,95,115,116,97,116,101,109,101,110,116]).decode())
		B=A._filter_columns_by_lang(B,display_mode);B.attrs[bytes([115,121,109,98,111,108]).decode()]=A.symbol;B.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source;B.attrs[bytes([114,101,112,111,114,116,95,116,121,112,101]).decode()]=bytes([105,110,99,111,109,101,95,115,116,97,116,101,109,101,110,116]).decode();B.attrs[bytes([112,101,114,105,111,100]).decode()]=C
		if E or A.show_log:logger.info(f"Truy xuất thành công báo cáo kết quả kinh doanh cho {A.symbol}.")
		return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def balance_sheet(self,period=None,limit=12,include_metadata=False,display_mode=FieldDisplayMode.STD,show_log=False):
		"\n        Truy xuất bảng cân đối kế toán (balance sheet).\n\n        Args:\n            period: Loại kỳ báo cáo ('year' hoặc 'quarter'). Mặc định 'year'.\n            limit: Số kỳ báo cáo tối đa cần lấy. Mặc định 4.\n            include_metadata: Bao gồm thông tin audit và unit trong rows. Mặc định False.\n            display_mode: Chế độ hiển thị trường dữ liệu. Mặc định FieldDisplayMode.STD.\n                - FieldDisplayMode.STD: Chỉ giữ cột 'item' và 'item_id' (đã chuẩn hóa)\n                - FieldDisplayMode.ALL: Giữ tất cả cột item (item, item_en, item_id)\n                - 'vi': Chỉ giữ tên tiếng Việt (tương thích ngược)\n                - 'en': Chỉ giữ tên tiếng Anh (tương thích ngược)\n                - None: Giữ tất cả cột (tương thích ngược)\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa bảng cân đối kế toán.\n\n        Examples:\n            >>> finance = Finance('ACB')\n            >>> df = finance.balance_sheet(period='year', display_mode=FieldDisplayMode.STD)\n            >>> df_all = finance.balance_sheet(period='year', display_mode=FieldDisplayMode.ALL)\n            >>> # Backward compatibility:\n            >>> df_vi = finance.balance_sheet(period='year', display_mode='vi')\n            >>> df_en = finance.balance_sheet(period='year', display_mode='en')\n        ";E=show_log;D=period;A=self;C=D if D else A.period if A.period else bytes([121,101,97,114]).decode();G=str(C).lower()
		if G in[bytes([121,101,97,114]).decode(),bytes([121]).decode(),bytes([97,110,110,117,97,108]).decode()]:C=bytes([121,101,97,114]).decode();F=1
		else:C=bytes([113,117,97,114,116,101,114]).decode();F=2
		B=A._fetch_series_data(report_type=bytes([67,68,75,84]).decode(),period_type=F,report_key=bytes([67,195,162,110,32,196,145,225,187,145,105,32,107,225,186,191,32,116,111,195,161,110]).decode(),limit=limit,include_metadata=include_metadata,show_log=E)
		if B.empty:logger.warning(f"Không tìm thấy bảng cân đối kế toán cho {A.symbol}.");return pd.DataFrame()
		if A.standardize_columns:B=A._apply_schema_standardization(B,bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode())
		B=A._filter_columns_by_lang(B,display_mode);B.attrs[bytes([115,121,109,98,111,108]).decode()]=A.symbol;B.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source;B.attrs[bytes([114,101,112,111,114,116,95,116,121,112,101]).decode()]=bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode();B.attrs[bytes([112,101,114,105,111,100]).decode()]=C
		if E or A.show_log:logger.info(f"Truy xuất thành công bảng cân đối kế toán cho {A.symbol}.")
		return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def cash_flow(self,period=None,limit=12,include_metadata=False,display_mode=FieldDisplayMode.STD,show_log=False):
		"\n        Truy xuất báo cáo lưu chuyển tiền tệ (cash flow statement).\n\n        Args:\n            period: Loại kỳ báo cáo ('year' hoặc 'quarter'). Mặc định 'year'.\n            limit: Số kỳ báo cáo tối đa cần lấy. Mặc định 4.\n            include_metadata: Bao gồm thông tin audit và unit trong rows. Mặc định False.\n            display_mode: Chế độ hiển thị trường dữ liệu. Mặc định FieldDisplayMode.STD.\n                - FieldDisplayMode.STD: Chỉ giữ cột 'item' và 'item_id' (đã chuẩn hóa)\n                - FieldDisplayMode.ALL: Giữ tất cả cột item (item, item_en, item_id)\n                - 'vi': Chỉ giữ tên tiếng Việt (tương thích ngược)\n                - 'en': Chỉ giữ tên tiếng Anh (tương thích ngược)\n                - None: Giữ tất cả cột (tương thích ngược)\n            show_log: Hiển thị log debug.\n\n        Returns:\n            DataFrame chứa báo cáo lưu chuyển tiền tệ.\n\n        Examples:\n            >>> finance = Finance('ACB')\n            >>> df = finance.cash_flow(period='year', display_mode=FieldDisplayMode.STD)\n            >>> df_all = finance.cash_flow(period='year', display_mode=FieldDisplayMode.ALL)\n            >>> # Backward compatibility:\n            >>> df_vi = finance.cash_flow(period='year', display_mode='vi')\n            >>> df_en = finance.cash_flow(period='year', display_mode='en')\n        ";G=show_log;F=period;A=self;C=F if F else A.period if A.period else bytes([121,101,97,114]).decode();J=str(C).lower()
		if J in[bytes([121,101,97,114]).decode(),bytes([121]).decode(),bytes([97,110,110,117,97,108]).decode()]:C=bytes([121,101,97,114]).decode();E=1
		else:C=bytes([113,117,97,114,116,101,114]).decode();E=2
		H=A._fetch_financial_data(report_type=bytes([76,67,84,84]).decode(),period_type=E,page_size=1,show_log=False)
		if not H:raise ValueError(f"Không tìm thấy dữ liệu tài chính cho mã {A.symbol}.")
		I=H.get(bytes([67,111,110,116,101,110,116]).decode(),{});D=None
		if bytes([76,198,176,117,32,99,104,117,121,225,187,131,110,32,116,105,225,187,129,110,32,116,225,187,135,32,103,105,195,161,110,32,116,105,225,186,191,112]).decode()in I:D=bytes([76,198,176,117,32,99,104,117,121,225,187,131,110,32,116,105,225,187,129,110,32,116,225,187,135,32,103,105,195,161,110,32,116,105,225,186,191,112]).decode()
		elif bytes([76,198,176,117,32,99,104,117,121,225,187,131,110,32,116,105,225,187,129,110,32,116,225,187,135,32,116,114,225,187,177,99,32,116,105,225,186,191,112]).decode()in I:D=bytes([76,198,176,117,32,99,104,117,121,225,187,131,110,32,116,105,225,187,129,110,32,116,225,187,135,32,116,114,225,187,177,99,32,116,105,225,186,191,112]).decode()
		if not D:logger.warning(f"Không tìm thấy báo cáo lưu chuyển tiền tệ cho {A.symbol}.");return pd.DataFrame()
		B=A._fetch_series_data(report_type=bytes([76,67,84,84]).decode(),period_type=E,report_key=D,limit=limit,include_metadata=include_metadata,show_log=G)
		if B.empty:logger.warning(f"Không tìm thấy báo cáo lưu chuyển tiền tệ cho {A.symbol}.");return pd.DataFrame()
		if A.standardize_columns:B=A._apply_schema_standardization(B,bytes([99,97,115,104,95,102,108,111,119]).decode())
		B=A._filter_columns_by_lang(B,display_mode);B.attrs[bytes([115,121,109,98,111,108]).decode()]=A.symbol;B.attrs[bytes([115,111,117,114,99,101]).decode()]=A.data_source;B.attrs[bytes([114,101,112,111,114,116,95,116,121,112,101]).decode()]=bytes([99,97,115,104,95,102,108,111,119]).decode();B.attrs[bytes([112,101,114,105,111,100]).decode()]=C
		if G or A.show_log:logger.info(f"Truy xuất thành công báo cáo lưu chuyển tiền tệ cho {A.symbol}.")
		return B
	@agg_execution(bytes([75,66,83,46,101,120,116]).decode())
	def ratio(self,period=None,limit=12,include_metadata=False,display_mode=FieldDisplayMode.STD,show_log=False):
		"\n        Truy xuất các chỉ số tài chính (financial ratios).\n\n        Args:\n            period: Loại kỳ báo cáo ('year' hoặc 'quarter'). Mặc định 'year'.\n            limit: Số kỳ báo cáo tối đa cần lấy. Mặc định 4.\n            include_metadata: Bao gồm thông tin audit và unit trong rows. Mặc định False.\n            display_mode: Chế độ hiển thị trường dữ liệu. Mặc định FieldDisplayMode.STD.\n                - FieldDisplayMode.STD: Chỉ giữ cột 'item' và 'item_id' (đã chuẩn hóa)\n                - FieldDisplayMode.ALL: Giữ tất cả cột item (item, item_en, item_id)\n                - 'vi': Chỉ giữ tên tiếng Việt (tương thích ngược)\n                - 'en': Chỉ giữ tên tiếng Anh (tương thích ngược)\n                - None: Giữ tất cả cột (tương thích ngược)\n# Register provider\nfrom vnstock_data.core.registry import ProviderRegistry\nProviderRegistry.register('financial', 'kbs', Finance)\n\n\n        Returns:\n            DataFrame chứa các chỉ số tài chính.\n\n        Examples:\n            >>> finance = Finance('ACB')\n            >>> df = finance.ratio(period='year', display_mode=FieldDisplayMode.STD)\n            >>> df_all = finance.ratio(period='year', display_mode=FieldDisplayMode.ALL)\n            >>> # Backward compatibility:\n            >>> df_vi = finance.ratio(period='year', display_mode='vi')\n            >>> df_en = finance.ratio(period='year', display_mode='en')\n        ";M=show_log;L=period;D=limit;B=self;F=L if L else B.period if B.period else bytes([121,101,97,114]).decode();S=str(F).lower()
		if S in[bytes([121,101,97,114]).decode(),bytes([121]).decode(),bytes([97,110,110,117,97,108]).decode()]:F=bytes([121,101,97,114]).decode();N=1
		else:F=bytes([113,117,97,114,116,101,114]).decode();N=2
		E=[];O=[];H=1;T=max(D,4)
		while len(O)<D:
			G=B._fetch_financial_data(report_type=bytes([67,83,84,67]).decode(),period_type=N,page=H,page_size=T,show_log=M)
			if not G:break
			U=G.get(bytes([67,111,110,116,101,110,116]).decode(),{});V=[bytes([78,104,195,179,109,32,99,104,225,187,137,32,115,225,187,145,32,196,144,225,187,139,110,104,32,103,105,195,161]).decode(),bytes([78,104,195,179,109,32,99,104,225,187,137,32,115,225,187,145,32,83,105,110,104,32,108,225,187,163,105]).decode(),bytes([78,104,195,179,109,32,99,104,225,187,137,32,115,225,187,145,32,84,196,131,110,103,32,116,114,198,176,225,187,159,110,103]).decode(),bytes([78,104,195,179,109,32,99,104,225,187,137,32,115,225,187,145,32,84,104,97,110,104,32,107,104,111,225,186,163,110]).decode(),bytes([78,104,195,179,109,32,99,104,225,187,137,32,115,225,187,145,32,67,104,225,186,165,116,32,108,198,176,225,187,163,110,103,32,116,195,160,105,32,115,225,186,163,110]).decode()];I=[]
			for W in V:
				P=U.get(W,[])
				if P:I.extend(P)
			if not I:break
			G[bytes([67,111,110,116,101,110,116]).decode()][bytes([70,105,110,97,110,99,105,97,108,32,82,97,116,105,111,115,32,67,111,109,98,105,110,101,100]).decode()]=I;J=B._parse_financial_response(G,bytes([70,105,110,97,110,99,105,97,108,32,82,97,116,105,111,115,32,67,111,109,98,105,110,101,100]).decode(),include_metadata=include_metadata)
			if J.empty:break
			Q=J.attrs.get(bytes([112,101,114,105,111,100,115]).decode(),[])
			if not Q:break
			E.append(J);O.extend(Q);H+=1
			if H>50:break
		if not E:logger.warning(f"Không tìm thấy chỉ số tài chính cho {B.symbol}.");return pd.DataFrame()
		A=E[0]
		for X in range(1,len(E)):
			C=E[X];R=C.attrs[bytes([112,101,114,105,111,100,115]).decode()];Y=[bytes([105,116,101,109,95,105,100]).decode()]+R
			if bytes([105,116,101,109,95,105,100]).decode()in C.columns:
				Z=A.attrs;A=pd.merge(A,C[Y],on=bytes([105,116,101,109,95,105,100]).decode(),how=bytes([111,117,116,101,114]).decode());A.attrs=Z
				if bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()in C.attrs:
					if bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()not in A.attrs:A.attrs[bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()]={}
					A.attrs[bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()].update(C.attrs[bytes([97,117,100,105,116,95,115,116,97,116,117,115]).decode()])
				if bytes([117,110,105,116,95,116,121,112,101]).decode()in C.attrs:
					if bytes([117,110,105,116,95,116,121,112,101]).decode()not in A.attrs:A.attrs[bytes([117,110,105,116,95,116,121,112,101]).decode()]={}
					A.attrs[bytes([117,110,105,116,95,116,121,112,101]).decode()].update(C.attrs[bytes([117,110,105,116,95,116,121,112,101]).decode()])
				if bytes([112,101,114,105,111,100,115]).decode()in A.attrs:A.attrs[bytes([112,101,114,105,111,100,115]).decode()].extend(R)
		K=A.attrs[bytes([112,101,114,105,111,100,115]).decode()]
		if len(K)>D:a=K[:D];b=K[D:];A=A.drop(columns=b,errors=bytes([105,103,110,111,114,101]).decode());A.attrs[bytes([112,101,114,105,111,100,115]).decode()]=a
		if B.standardize_columns:A=B._apply_schema_standardization(A,bytes([102,105,110,97,110,99,105,97,108,95,114,97,116,105,111,115]).decode())
		A=B._filter_columns_by_lang(A,display_mode);A.attrs[bytes([115,121,109,98,111,108]).decode()]=B.symbol;A.attrs[bytes([115,111,117,114,99,101]).decode()]=B.data_source;A.attrs[bytes([114,101,112,111,114,116,95,116,121,112,101]).decode()]=bytes([102,105,110,97,110,99,105,97,108,95,114,97,116,105,111,115]).decode();A.attrs[bytes([112,101,114,105,111,100]).decode()]=F
		if M or B.show_log:logger.info(f"Truy xuất thành công chỉ số tài chính cho {B.symbol}.")
		return A
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([102,105,110,97,110,99,105,97,108]).decode(),bytes([107,98,115]).decode(),Finance)