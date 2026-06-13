import logging,re
from typing import Optional
import pandas as pd,requests
from bs4 import BeautifulSoup
from vnai import agg_execution
from vnstock.core.utils.parser import camel_to_snake
from vnstock_data.core.utils.parser import vn_to_snake_case
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.mbk.const import _BASE_URL,FINANCE_INFO,GET_DOCUMENT,REPORT_TERM,UNIT_TYPE,DOC_TYPE
logger=logging.getLogger(__name__)
class Finance:
	'\n    A class for fetching financial reports and document links from Maybank Kim Eng (MBK).\n    '
	def __init__(A,symbol,period=None,random_agent=False,proxy_config=None,show_log=False):
		C=show_log;B=period;A.symbol=symbol.upper()
		if B is not None and B not in[bytes([121,101,97,114]).decode(),bytes([113,117,97,114,116,101,114]).decode()]:raise ValueError(bytes([75,225,187,179,32,98,195,161,111,32,99,195,161,111,32,116,195,160,105,32,99,104,195,173,110,104,32,107,104,195,180,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,67,104,225,187,137,32,99,104,225,186,165,112,32,110,104,225,186,173,110,32,39,121,101,97,114,39,32,104,111,225,186,183,99,32,39,113,117,97,114,116,101,114,39,32,104,111,225,186,183,99,32,78,111,110,101,46]).decode())
		A.period=B;A.data_source=bytes([77,66,75]).decode();A.headers=get_headers(data_source=A.data_source,random_agent=random_agent);A.headers[bytes([99,111,110,116,101,110,116,45,116,121,112,101]).decode()]=bytes([97,112,112,108,105,99,97,116,105,111,110,47,120,45,119,119,119,45,102,111,114,109,45,117,114,108,101,110,99,111,100,101,100,59,32,99,104,97,114,115,101,116,61,85,84,70,45,56]).decode();A.headers[bytes([120,45,114,101,113,117,101,115,116,101,100,45,119,105,116,104]).decode()]=bytes([88,77,76,72,116,116,112,82,101,113,117,101,115,116]).decode();A.show_log=C;A.proxy_config=proxy_config;A._session=requests.Session();A._session.headers.update(A.headers);A._verification_token=None
		if C:logger.setLevel(bytes([73,78,70,79]).decode())
		else:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	def _get_verification_token(A):
		if A._verification_token:return A._verification_token
		E=f"{_BASE_URL}{A.symbol}/tai-chinh.htm";C=A._session.get(E,headers=A.headers);F=BeautifulSoup(C.text,bytes([104,116,109,108,46,112,97,114,115,101,114]).decode());B=F.find(bytes([105,110,112,117,116]).decode(),{bytes([110,97,109,101]).decode():bytes([95,95,82,101,113,117,101,115,116,86,101,114,105,102,105,99,97,116,105,111,110,84,111,107,101,110]).decode()})
		if B and B.get(bytes([118,97,108,117,101]).decode()):A._verification_token=B.get(bytes([118,97,108,117,101]).decode());return A._verification_token
		D=re.search(bytes([110,97,109,101,61,34,95,95,82,101,113,117,101,115,116,86,101,114,105,102,105,99,97,116,105,111,110,84,111,107,101,110,34,32,116,121,112,101,61,34,104,105,100,100,101,110,34,32,118,97,108,117,101,61,34,40,91,94,34,93,43,41,34]).decode(),C.text)
		if D:A._verification_token=D.group(1);return A._verification_token
		return''
	def _fetch_series_data(D,report_type,term,unit,limit=12):
		N=report_type;G=limit;g=f"{_BASE_URL}{FINANCE_INFO}";U=REPORT_TERM.get(term)
		if U is None:raise ValueError(f"Unsupported report term: {term}")
		V=UNIT_TYPE.get(str(unit))
		if V is None:raise ValueError(f"Unsupported unit: {unit}")
		W=D._get_verification_token();E=[];O=[];H=1
		while len(O)<G:
			X=f"Code={D.symbol}&ReportType={N}&ReportTermType={U}&Unit={V}&Page={H}&PageSize={max(G,4)}"
			if W:X+=f"&__RequestVerificationToken={W}"
			if D.show_log:logger.info(f"MBK Financial API Request: {D.symbol} - {N} - Page: {H}")
			Y=D._session.post(g,data=X);Y.raise_for_status()
			try:C=Y.json()
			except requests.exceptions.JSONDecodeError as h:logger.error(f"Failed to decode JSON from MBK API: {h}");break
			if not C:break
			if isinstance(C,list)and len(C)>=2 and isinstance(C[0],list):
				Z=C[0]
				if not Z:break
				a={};I=[]
				for(P,b)in enumerate(Z):c=b.get(bytes([84,101,114,109,67,111,100,101]).decode(),'');d=b.get(bytes([89,101,97,114,80,101,114,105,111,100]).decode(),'');J=f"{c}_{d}"if c else str(d);J=J.lower();a[f"Value{P+1}"]=J;I.append(J)
				Q=[]
				if isinstance(C[1],dict):
					for e in C[1].values():
						if isinstance(e,list):Q.extend(e)
				elif isinstance(C[1],list):Q=C[1]
				A=pd.DataFrame(Q);A.rename(columns=a,inplace=True)
				if bytes([78,97,109,101]).decode()in A.columns:A[bytes([105,116,101,109]).decode()]=A[bytes([78,97,109,101]).decode()]
				if bytes([78,97,109,101,69,110]).decode()in A.columns:A[bytes([105,116,101,109,95,101,110]).decode()]=A[bytes([78,97,109,101,69,110]).decode()]
				def i(row):
					A=row
					if pd.notna(A.get(bytes([105,116,101,109,95,101,110]).decode()))and str(A.get(bytes([105,116,101,109,95,101,110]).decode())).strip():return vn_to_snake_case(str(A[bytes([105,116,101,109,95,101,110]).decode()]))
					elif pd.notna(A.get(bytes([105,116,101,109]).decode()))and str(A.get(bytes([105,116,101,109]).decode())).strip():return vn_to_snake_case(str(A[bytes([105,116,101,109]).decode()]))
					return''
				if not A.empty:
					A[bytes([105,116,101,109,95,105,100]).decode()]=A.apply(i,axis=1);K={};L=[]
					for F in A[bytes([105,116,101,109,95,105,100]).decode()]:
						if not F:L.append('');continue
						if F in K:K[F]+=1;L.append(f"{F}_{K[F]}")
						else:K[F]=1;L.append(F)
					A[bytes([105,116,101,109,95,105,100]).decode()]=L
				else:A[bytes([105,116,101,109,95,105,100]).decode()]=pd.Series(dtype=bytes([115,116,114]).decode())
				if bytes([85,110,105,116]).decode()in A.columns:A[bytes([117,110,105,116]).decode()]=A[bytes([85,110,105,116]).decode()]
				if bytes([76,101,118,101,108,115]).decode()in A.columns:A[bytes([108,101,118,101,108,115]).decode()]=A[bytes([76,101,118,101,108,115]).decode()]
				if bytes([73,68]).decode()in A.columns:A[bytes([114,111,119,95,110,117,109,98,101,114]).decode()]=A[bytes([73,68]).decode()]
				j=[bytes([105,116,101,109]).decode(),bytes([105,116,101,109,95,101,110]).decode(),bytes([105,116,101,109,95,105,100]).decode(),bytes([117,110,105,116]).decode(),bytes([108,101,118,101,108,115]).decode(),bytes([114,111,119,95,110,117,109,98,101,114]).decode()]+I;k=[B for B in j if B in A.columns];A=A[k];A.attrs[bytes([112,101,114,105,111,100,115]).decode()]=[B for B in I if B in A.columns];E.append(A);f=[A for A in I if A not in O]
				if not f:break
				O.extend(f)
			else:A=pd.DataFrame(C);A.columns=[camel_to_snake(str(A))for A in A.columns];E.append(A);break
			H+=1
			if H>50:break
		if not E:return pd.DataFrame()
		B=E[0]
		if len(E)>1 and bytes([105,116,101,109,95,105,100]).decode()in B.columns:
			for P in range(1,len(E)):
				R=E[P];S=R.attrs.get(bytes([112,101,114,105,111,100,115]).decode(),[])
				if S:
					M=[bytes([105,116,101,109,95,105,100]).decode()]+[A for A in S if A not in B.columns];M=[A for A in M if A in R.columns]
					if len(M)>1:
						l=B.attrs;B=pd.merge(B,R[M],on=bytes([105,116,101,109,95,105,100]).decode(),how=bytes([111,117,116,101,114]).decode());B.attrs=l
						if bytes([112,101,114,105,111,100,115]).decode()in B.attrs:B.attrs[bytes([112,101,114,105,111,100,115]).decode()].extend([A for A in S if A not in B.attrs[bytes([112,101,114,105,111,100,115]).decode()]])
		if bytes([112,101,114,105,111,100,115]).decode()in B.attrs:
			T=B.attrs[bytes([112,101,114,105,111,100,115]).decode()]
			if len(T)>G:m=T[:G];n=T[G:];B=B.drop(columns=n,errors=bytes([105,103,110,111,114,101]).decode());B.attrs[bytes([112,101,114,105,111,100,115]).decode()]=m
		B.attrs[bytes([115,121,109,98,111,108]).decode()]=D.symbol;B.attrs[bytes([115,111,117,114,99,101]).decode()]=D.data_source;B.attrs[bytes([114,101,112,111,114,116,95,116,121,112,101]).decode()]=N;return B
	@agg_execution(bytes([77,66,75]).decode())
	def balance_sheet(self,period=None,limit=12,unit=bytes([49,48,48,48]).decode(),show_log=False):B=period;A=self;C=B if B else A.period if A.period else bytes([113,117,97,114,116,101,114]).decode();return A._fetch_series_data(bytes([67,68,75,84]).decode(),C,unit,limit)
	@agg_execution(bytes([77,66,75]).decode())
	def income_statement(self,period=None,limit=12,unit=bytes([49,48,48,48]).decode(),show_log=False):B=period;A=self;C=B if B else A.period if A.period else bytes([113,117,97,114,116,101,114]).decode();return A._fetch_series_data(bytes([75,81,75,68]).decode(),C,unit,limit)
	@agg_execution(bytes([77,66,75]).decode())
	def cash_flow(self,period=None,limit=12,unit=bytes([49,48,48,48]).decode(),show_log=False):B=period;A=self;C=B if B else A.period if A.period else bytes([113,117,97,114,116,101,114]).decode();return A._fetch_series_data(bytes([76,67]).decode(),C,unit,limit)
	@agg_execution(bytes([77,66,75]).decode())
	def ratio(self,period=None,limit=12,unit=bytes([49,48,48,48]).decode(),show_log=False):B=period;A=self;C=B if B else A.period if A.period else bytes([113,117,97,114,116,101,114]).decode();return A._fetch_series_data(bytes([67,83,84,67]).decode(),C,unit,limit)
	@agg_execution(bytes([77,66,75]).decode())
	def business_plan(self,period=None,limit=12,unit=bytes([49,48,48,48]).decode(),show_log=False):'Fetches business plans/targets (CTKH).';B=period;A=self;C=B if B else A.period if A.period else bytes([113,117,97,114,116,101,114]).decode();return A._fetch_series_data(bytes([67,84,75,72]).decode(),C,unit,limit)
	@agg_execution(bytes([77,66,75]).decode())
	def document(self,doc_type=None):
		"\n        Fetches a list of documents and their PDF links.\n        \n        Args:\n            doc_type (str, optional): Type of document to filter. Valid options:\n                - 'financial_report': Báo cáo tài chính\n                - 'annual_report': Báo cáo thường niên\n                - 'prospectus': Bản cáo bạch\n                - 'shareholder_resolution': Nghị quyết HĐCĐ\n                - 'shareholder_material': Tài liệu HĐCĐ\n                - 'business_explanation': Giải trình KQKD\n                - 'management_report': Báo cáo tình hình quản trị\n                - 'capital_adequacy': Báo cáo tỷ lệ an toàn vốn\n                - 'board_resolution': Nghị quyết HĐQT\n                - 'capital_safety': Tỷ lệ an toàn tài chính\n                - 'other': Khác\n            \n        Returns:\n            pd.DataFrame: Contains document names, details, and download URLs.\n        ";C=doc_type;B=self;I=f"{_BASE_URL}{GET_DOCUMENT}";F=B._get_verification_token();D=f"code={B.symbol}"
		if C:
			G=DOC_TYPE.get(C)
			if not G:raise ValueError(f"Unsupported doc_type: {C}. Valid options: {list(DOC_TYPE.keys())}")
			D+=f"&type={G}"
		if F:D+=f"&__RequestVerificationToken={F}"
		if B.show_log:logger.info(f"MBK Document API Request: {B.symbol}")
		E=B._session.post(I,data=D);E.raise_for_status()
		try:H=E.json()
		except requests.exceptions.JSONDecodeError as J:raise ValueError(f"Failed to decode JSON for documents from MBK API. Raw response excerpt: {E.text[:200]}")from J
		if not H:return pd.DataFrame()
		A=pd.DataFrame(H);A.columns=[camel_to_snake(str(A))for A in A.columns];K={bytes([117,114,108]).decode():bytes([100,111,99,95,117,114,108]).decode(),bytes([116,105,116,108,101]).decode():bytes([100,111,99,95,116,105,116,108,101]).decode(),bytes([102,117,108,108,95,110,97,109,101]).decode():bytes([100,111,99,95,110,97,109,101]).decode()};A=A.rename(columns=K);A.insert(0,bytes([116,105,99,107,101,114]).decode(),B.symbol)
		if bytes([112,97,116,104]).decode()in A.columns:L=_BASE_URL.rstrip(bytes([47]).decode());A[bytes([100,111,99,95,117,114,108]).decode()]=A[bytes([112,97,116,104]).decode()].apply(lambda x:f"{L}{x}"if isinstance(x,str)and x.startswith(bytes([47]).decode())else x);A=A.drop(columns=[bytes([112,97,116,104]).decode()])
		return A
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([102,105,110,97,110,99,105,97,108]).decode(),bytes([109,98,107]).decode(),Finance)