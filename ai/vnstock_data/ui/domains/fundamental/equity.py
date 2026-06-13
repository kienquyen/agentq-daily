'\nEquity Fundamental Domain (Layer 3).\nWraps the `kbs.financial.Finance` module.\n'
import pandas as pd
from vnstock_data.ui._base import BaseDetail
from vnstock_data.ui._registry import FUNDAMENTAL_SOURCES
from vnstock_data.ui.schemas.core import standardize_columns
class EquityFundamental(BaseDetail):
	'\n    Access point for fetching company financial statements and valuation ratios.\n    '
	def __init__(A,symbol):super().__init__(symbol=symbol,domain_name=bytes([101,113,117,105,116,121,46,102,117,110,100,97,109,101,110,116,97,108]).decode(),layer_sources=FUNDAMENTAL_SOURCES)
	def _resolve_scorecard(F,scorecard):
		'Resolves auto scorecard into exact sector keys based on literal text definitions';B=scorecard;D={bytes([98,97,110,107]).decode():bytes([98,97,110,107,105,110,103]).decode(),bytes([115,101,99]).decode():bytes([115,101,99,117,114,105,116,105,101,115]).decode(),bytes([105,110,115]).decode():bytes([105,110,115,117,114,97,110,99,101]).decode()}
		if B in D:B=D[B]
		if B==bytes([97,117,116,111]).decode():
			from vnstock_data.ui import Reference as G
			try:
				C=G().company(F.symbol).info()
				if not C.empty:
					E=bytes([105,110,100,117,115,116,114,121]).decode()if bytes([105,110,100,117,115,116,114,121]).decode()in C.columns else bytes([115,101,99,116,111,114]).decode()if bytes([115,101,99,116,111,114]).decode()in C.columns else None
					if E:
						A=str(C[E].iloc[0])
						if A.startswith(bytes([78,103,195,162,110,32,104,195,160,110,103]).decode())or bytes([98,97,110,107]).decode()in A.lower():return bytes([98,97,110,107,105,110,103]).decode()
						elif A.startswith(bytes([68,225,187,139,99,104,32,118,225,187,165,32,116,195,160,105,32,99,104,195,173,110,104]).decode())or bytes([99,104,225,187,169,110,103,32,107,104,111,195,161,110]).decode()in A.lower()or bytes([102,105,110,97,110,99,105,97,108,32,115,101,114,118,105,99,101,115]).decode()in A.lower():return bytes([115,101,99,117,114,105,116,105,101,115]).decode()
						elif bytes([66,225,186,163,111,32,104,105,225,187,131,109]).decode()in A or bytes([105,110,115,117,114,97,110,99,101]).decode()in A.lower():return bytes([105,110,115,117,114,97,110,99,101]).decode()
			except Exception:pass
			return bytes([103,101,110,101,114,105,99]).decode()
		return B
	def _dispatch_and_format(C,method_name,scorecard=None,filter_unmapped=None,**H):
		'\n        Dispatches method to KBS Finance and standardizes columns without strict trimming.\n        Financial statements vary widely depending on sector, so we use `strict=False`\n        to preserve all snake_cased accounting fields.\n        ';F=filter_unmapped;D=method_name;E=H.copy()
		if bytes([100,105,115,112,108,97,121,95,109,111,100,101]).decode()not in E:from vnstock_data.explorer.kbs.financial import FieldDisplayMode as M;E[bytes([100,105,115,112,108,97,121,95,109,111,100,101]).decode()]=M.STD
		E.pop(bytes([108,97,110,103]).decode(),None);A=C._dispatch(D,**E)
		if A.empty:return A
		from vnstock_data.ui.config import get_route as N;O,I,I,I=N(C._domain_name,D,C._sources_config);J=bytes([102,117,110,100,97,109,101,110,116,97,108,46,101,113,117,105,116,121]).decode();G=C._resolve_scorecard(scorecard)
		if F is None:F=G is not None
		A=standardize_columns(A,f"{J}.{D}",O,strict=False,filter_unmapped=F)
		if bytes([105,116,101,109,95,105,100]).decode()in A.columns:
			B=A.set_index(bytes([105,116,101,109,95,105,100]).decode());K=[A for A in B.columns if str(A).replace(bytes([45]).decode(),bytes([81]).decode()).replace(bytes([81]).decode(),bytes([49]).decode()).isdigit()]
			if K:B=B[K].transpose();B=B.reset_index();B=B.rename(columns={bytes([105,110,100,101,120]).decode():bytes([112,101,114,105,111,100]).decode()});B.insert(1,bytes([116,105,99,107,101,114]).decode(),C.symbol);A=B.sort_values(bytes([112,101,114,105,111,100]).decode()).reset_index(drop=True)
		A=A.loc[:,~A.columns.duplicated(keep=bytes([102,105,114,115,116]).decode())]
		if G:
			from vnstock_data.ui.schemas.scorecards import SCORECARDS as P;L=P.get(G,{}).get(f"{J}.{D}",[])
			if L:Q=[A for A in A.columns if A in L or A in[bytes([112,101,114,105,111,100]).decode(),bytes([116,105,99,107,101,114]).decode(),bytes([114,101,112,111,114,116,95,112,101,114,105,111,100]).decode()]];A=A[Q]
		if H.get(bytes([108,97,110,103]).decode())==bytes([118,105]).decode():from vnstock_data.ui.schemas.dictionary import FUNDAMENTAL_VI_LABELS as R;A=A.rename(columns=R)
		return A
	def ratio(A,scorecard=None,**B):'\n        Extracts key financial ratios (P/E, ROE, Debt/Equity, etc.).\n        \n        Returns:\n            pd.DataFrame: Ratios pivoted by period.\n        ';return A._dispatch_and_format(bytes([114,97,116,105,111]).decode(),scorecard=scorecard,**B)
	def income_statement(A,scorecard=None,**B):'\n        Extracts Income Statement.\n        ';return A._dispatch_and_format(bytes([105,110,99,111,109,101,95,115,116,97,116,101,109,101,110,116]).decode(),scorecard=scorecard,**B)
	def balance_sheet(A,scorecard=None,**B):'\n        Extracts Balance Sheet.\n        ';return A._dispatch_and_format(bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode(),scorecard=scorecard,**B)
	def cash_flow(A,scorecard=None,**B):'\n        Extracts Cash Flow statement.\n        ';return A._dispatch_and_format(bytes([99,97,115,104,95,102,108,111,119]).decode(),scorecard=scorecard,**B)
	def note(A,**C):
		"\n        Extracts Footnotes (Thuyết minh Báo cáo tài chính).\n        Note: This method doesn't accept display_mode parameter.\n        ";C.pop(bytes([100,105,115,112,108,97,121,95,109,111,100,101]).decode(),None);B=A._dispatch(bytes([110,111,116,101]).decode(),**C)
		if B.empty:return B
		from vnstock_data.ui.config import get_route as E;from vnstock_data.ui.schemas.core import standardize_columns as F;G,D,D,D=E(A._domain_name,bytes([110,111,116,101]).decode(),A._sources_config);return F(B,f"{A._domain_name}.note",G,strict=False,filter_unmapped=False)
	def filing(A,doc_type=None,**B):"\n        Extracts Corporate filing and Document URLs (inspired by Bloomberg CF).\n        \n        Args:\n            doc_type (str, optional): Filter by document type. Valid options:\n                - 'financial_report': Báo cáo tài chính\n                - 'annual_report': Báo cáo thường niên\n                - 'prospectus': Bản cáo bạch\n                - 'shareholder_resolution': Nghị quyết HĐCĐ\n                - 'shareholder_material': Tài liệu HĐCĐ\n                - 'business_explanation': Giải trình KQKD\n                - 'management_report': Báo cáo tình hình quản trị\n                - 'capital_adequacy': Báo cáo tỷ lệ an toàn vốn\n                - 'board_resolution': Nghị quyết HĐQT\n                - 'capital_safety': Tỷ lệ an toàn tài chính\n                - 'other': Khác\n            \n        Returns:\n            pd.DataFrame: A list of corporate documents and their PDF download links.\n        ";return A._dispatch(bytes([102,105,108,105,110,103]).decode(),doc_type=doc_type,**B)
	def financial_health(C,scorecard=bytes([97,117,116,111]).decode(),reports=None,**E):
		'\n        Aggregates Balance Sheet, Income Statement, Cash Flow, and Ratios into a single unified health matrix\n        with TCBS-style section headers and proper field ordering.\n        \n        Args:\n            scorecard: \'auto\' (detect via ICB), \'banking\', \'securities\', \'insurance\', \'generic\'.\n            reports: A list specifying which datasets to merge. Defaults to all 4 fundamental reports.\n                     Options: ["income_statement", "balance_sheet", "cash_flow", "ratio"]\n        ';I=scorecard;D=reports;print(bytes([27,91,57,51,109]).decode()+bytes([226,154,160,239,184,143,32,77,73,225,187,132,78,32,84,82,225,187,170,32,84,82,195,129,67,72,32,78,72,73,225,187,134,77,58,32,68,225,187,175,32,108,105,225,187,135,117,32,116,195,160,105,32,99,104,195,173,110,104,32,196,145,198,176,225,187,163,99,32,99,104,117,225,186,169,110,32,104,195,179,97,32,118,195,160,32,116,225,187,149,110,103,32,104,225,187,163,112,32,100,225,187,177,97,32,116,114,195,170,110,32,99,195,161,99,32,110,103,117,225,187,147,110,32,116,104,195,180,110,103,32,116,105,110,32,99,195,180,110,103,32,107,104,97,105,46,32,77,225,186,183,99,32,100,195,185,32,99,225,186,165,117,32,116,114,195,186,99,32,98,195,161,111,32,99,195,161,111,32,196,145,198,176,225,187,163,99,32,116,104,105,225,186,191,116,32,107,225,186,191,32,100,225,187,177,97,32,116,114,195,170,110,32,116,105,195,170,117,32,99,104,117,225,186,169,110,32,116,104,97,109,32,99,104,105,225,186,191,117,32,116,225,187,171,32,104,225,187,135,32,116,104,225,187,145,110,103,32,112,104,195,162,110,32,116,195,173,99,104,32,99,225,187,167,97,32,84,67,66,83,32,110,104,225,186,177,109,32,196,145,225,186,163,109,32,98,225,186,163,111,32,116,195,173,110,104,32,110,104,225,186,165,116,32,113,117,195,161,110,44,32,110,103,198,176,225,187,157,105,32,100,195,185,110,103,32,99,225,186,167,110,32,108,198,176,117,32,195,189,32,114,225,186,177,110,103,32,100,111,32,115,225,187,177,32,107,104,195,161,99,32,98,105,225,187,135,116,32,116,114,111,110,103,32,112,104,198,176,198,161,110,103,32,112,104,195,161,112,32,104,225,186,161,99,104,32,116,111,195,161,110,32,118,195,160,32,196,145,225,187,153,32,116,114,225,187,133,32,100,225,187,175,32,108,105,225,187,135,117,32,103,105,225,187,175,97,32,99,195,161,99,32,110,103,117,225,187,147,110,44,32,99,195,161,99,32,99,104,225,187,137,32,115,225,187,145,32,99,195,179,32,116,104,225,187,131,32,116,225,187,147,110,32,116,225,186,161,105,32,115,97,105,32,115,225,187,145,32,104,111,225,186,183,99,32,107,104,195,161,99,32,98,105,225,187,135,116,32,115,111,32,118,225,187,155,105,32,99,195,161,99,32,110,225,187,129,110,32,116,225,186,163,110,103,32,116,104,97,109,32,99,104,105,225,186,191,117,32,107,104,195,161,99,46,32,84,104,195,180,110,103,32,116,105,110,32,110,195,160,121,32,99,104,225,187,137,32,109,97,110,103,32,116,195,173,110,104,32,99,104,225,186,165,116,32,116,104,97,109,32,107,104,225,186,163,111,46,32,78,103,198,176,225,187,157,105,32,100,195,185,110,103,32,99,97,109,32,107,225,186,191,116,32,116,225,187,177,32,114,195,160,32,115,111,195,161,116,32,118,195,160,32,99,104,225,187,139,117,32,116,111,195,160,110,32,98,225,187,153,32,116,114,195,161,99,104,32,110,104,105,225,187,135,109,32,196,145,225,187,145,105,32,118,225,187,155,105,32,109,225,187,141,105,32,113,117,121,225,186,191,116,32,196,145,225,187,139,110,104,32,115,225,187,173,32,100,225,187,165,110,103,32,100,225,187,175,32,108,105,225,187,135,117,32,110,195,160,121,32,116,114,111,110,103,32,99,195,161,99,32,104,111,225,186,161,116,32,196,145,225,187,153,110,103,32,196,145,225,186,167,117,32,116,198,176,46]).decode()+bytes([27,91,48,109]).decode());F=[]
		if D is None:D=[bytes([105,110,99,111,109,101,95,115,116,97,116,101,109,101,110,116]).decode(),bytes([98,97,108,97,110,99,101,95,115,104,101,101,116]).decode(),bytes([99,97,115,104,95,102,108,111,119]).decode(),bytes([114,97,116,105,111]).decode()]
		for L in D:
			M=getattr(C,L);B=M(scorecard=I,**E)
			if not B.empty:
				if bytes([116,105,99,107,101,114]).decode()in B.columns:B=B.drop(columns=[bytes([116,105,99,107,101,114]).decode()])
				F.append(B.set_index(bytes([112,101,114,105,111,100]).decode()))
		if not F:return pd.DataFrame()
		G=pd.concat(F,axis=1,join=bytes([111,117,116,101,114]).decode());G=G.T.groupby(level=0).sum(min_count=1).T.reset_index();J=C._resolve_scorecard(I);A=C._apply_tcbs_ordering(G,J,**E)
		if J==bytes([98,97,110,107,105,110,103]).decode():
			N={bytes([110,101,116,95,105,110,116,101,114,101,115,116,95,105,110,99,111,109,101]).decode():bytes([84,104,117,32,110,104,225,186,173,112,32,108,195,163,105,32,116,104,117,225,186,167,110]).decode(),bytes([110,101,116,95,102,101,101,95,97,110,100,95,99,111,109,109,105,115,115,105,111,110,95,105,110,99,111,109,101]).decode():bytes([76,195,163,105,32,116,104,117,225,186,167,110,32,116,225,187,171,32,72,196,144,32,100,225,187,139,99,104,32,118,225,187,165]).decode(),bytes([110,101,116,95,103,97,105,110,95,108,111,115,115,95,102,114,111,109,95,105,110,118,101,115,116,109,101,110,116,95,97,99,116,105,118,105,116,105,101,115]).decode():bytes([76,195,163,105,32,116,104,117,225,186,167,110,32,116,225,187,171,32,72,196,144,32,196,145,225,186,167,117,32,116,198,176]).decode(),bytes([110,101,116,95,111,116,104,101,114,95,105,110,99,111,109,101]).decode():bytes([76,195,163,105,32,116,104,117,225,186,167,110,32,116,225,187,171,32,72,196,144,32,107,104,195,161,99]).decode()};K=[B for B in N.values()if B in A.columns]
			if len(K)>=2:A[bytes([84,225,187,149,110,103,32,116,104,117,32,110,104,225,186,173,112,32,72,196,144,32,40,84,79,73,41]).decode()]=A[K].sum(axis=1,min_count=1)
		H=E.get(bytes([108,105,109,105,116]).decode(),16)
		if H and H>0:A=A.sort_values(by=bytes([112,101,114,105,111,100]).decode(),ascending=False);A=A.head(H);A=A.sort_values(by=bytes([112,101,114,105,111,100]).decode(),ascending=True)
		else:A=A.sort_values(by=bytes([112,101,114,105,111,100]).decode(),ascending=True)
		A.insert(0,bytes([116,105,99,107,101,114]).decode(),C.symbol);return A
	def _apply_tcbs_ordering(T,df,scorecard_key,**M):
		'\n        Apply TCBS-style section headers and field ordering to the financial health data.\n        Creates a structured output with section headers as index values.\n        ';A=df;from vnstock_data.ui.schemas.dictionary import FUNDAMENTAL_VI_LABELS as N;from vnstock_data.ui.schemas.scorecards import get_financial_health_sections as O;P=O(scorecard_key);D=[]
		for H in P:
			Q=H[bytes([104,101,97,100,101,114]).decode()];R=H[bytes([102,105,101,108,100,115]).decode()];I=False;J=[]
			for E in R:
				B=None
				if E in A.columns:B=E
				elif M.get(bytes([108,97,110,103]).decode())==bytes([118,105]).decode():
					F=N.get(E)
					if F and F in A.columns:B=F
				if B:I=True;J.append(B)
			if I:D.append(Q);D.extend(J)
		G=[]
		for K in D:
			if K in A.columns:G.append(K)
		if G:
			C=[]
			if bytes([112,101,114,105,111,100]).decode()in A.columns:C.append(bytes([112,101,114,105,111,100]).decode())
			if bytes([116,105,99,107,101,114]).decode()in A.columns:C.append(bytes([116,105,99,107,101,114]).decode())
			S=C+[A for A in G if A not in C];L=A[S].copy()
		else:L=A.copy()
		return L