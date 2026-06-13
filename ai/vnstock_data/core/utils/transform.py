from datetime import datetime
from typing import Any
import pandas as pd
from vnstock.core.types import TimeFrame
from vnstock.core.utils.interval import normalize_interval
from vnstock.core.utils.parser import localize_timestamp
from vnstock.core.utils.transform import get_trading_date
def generate_period(df):
	B=[bytes([121,101,97,114,82,101,112,111,114,116]).decode(),bytes([108,101,110,103,116,104,82,101,112,111,114,116]).decode(),bytes([114,101,112,111,114,116,95,112,101,114,105,111,100]).decode()]
	for A in B:
		if A not in df.columns:raise ValueError(f"Thiếu cột {A} trong df")
	df.loc[:,bytes([112,101,114,105,111,100]).decode()]=df.apply(lambda x:str(x[bytes([121,101,97,114,82,101,112,111,114,116]).decode()])if x[bytes([114,101,112,111,114,116,95,112,101,114,105,111,100]).decode()]==bytes([121,101,97,114]).decode()else str(x[bytes([121,101,97,114,82,101,112,111,114,116]).decode()])+bytes([45,81]).decode()+str(x[bytes([108,101,110,103,116,104,82,101,112,111,114,116]).decode()]),axis=1);return df
def remove_pattern_columns(df,patterns):"\n    Remove columns from a DataFrame that contains any of the given patterns in their names\n    \n    Parameters\n    ----------\n    df : pd.DataFrame\n        Input DataFrame\n    patterns : List[str]\n        List of patterns to remove\n    \n    Returns\n    -------\n    pd.DataFrame\n        DataFrame with columns that match the given patterns removed\n    \n    Examples\n    --------\n    >>> df = pd.DataFrame({'FooBar': [1, 2], 'BarFoo': [3, 4]})\n    >>> remove_pattern_columns(df, ['foo'])\n       BarFoo\n    0       3\n    1       4\n    ";A=[A for A in df.columns if any(B in A.lower()for B in patterns)];df.drop(columns=A,inplace=True);return df
def clean_numeric_string(s):
	"\n    Loại bỏ dấu phân nhóm (',' hoặc NBSP), chuẩn hoá dấu thập phân về '.'\n    "
	if not isinstance(s,str):return s
	s=s.replace(bytes([194,160]).decode(),'').replace(bytes([44]).decode(),'')
	if s.count(bytes([46]).decode())==0 and s.count(bytes([44]).decode())==1:s=s.replace(bytes([44]).decode(),bytes([46]).decode())
	return s.strip()
def process_match_types(df,asset_type,source):
	"\n    Process match_type labels with special handling for stock ATO/ATC transactions.\n    \n    For VCI:\n        - Replace 'b' with 'Buy' and 's' with 'Sell'.\n        - Missing values are represented by the string 'unknown'.\n    For MAS:\n        - Replace 'BUY' with 'Buy' and 'SELL' with 'Sell'.\n        - Fill in NaN values with 'unknown'.\n    For TCBS:\n        - Replace 'BU' with 'Buy' and 'SD' with 'Sell'.\n        - Missing values are assumed to be an empty string.\n    For KBS:\n        - Replace 'B' with 'Buy' and 'S' with 'Sell'.\n        - Missing values are assumed to be an empty string.\n    \n    Once basic replacements are done, if the asset type is 'stock' and missing\n    match_type values are present, the code will mark the ATO (at the earliest\n    morning transaction in the 9:13–9:17 window) and ATC (at the latest afternoon\n    transaction in the 14:43–14:47 window) within each trading day.\n    \n    Parameters:\n        df (DataFrame): The input DataFrame with a 'time' and 'match_type' column.\n        asset_type (str): The asset type (for example, 'stock').\n        source (str): The data source (e.g., 'VCI', 'MAS', 'TCBS', or 'KBS').\n        \n    Returns:\n        DataFrame: The modified DataFrame with updated match_type values.\n    ";B=source;A=df
	if B==bytes([86,67,73]).decode():A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()].replace({bytes([98]).decode():bytes([66,117,121]).decode(),bytes([115]).decode():bytes([83,101,108,108]).decode()})
	elif B==bytes([77,65,83]).decode():A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()].replace({bytes([66,85,89]).decode():bytes([66,117,121]).decode(),bytes([83,69,76,76]).decode():bytes([83,101,108,108]).decode()});A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()].fillna(bytes([117,110,107,110,111,119,110]).decode())
	elif B==bytes([84,67,66,83]).decode():A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()].replace({bytes([66,85]).decode():bytes([66,117,121]).decode(),bytes([83,68]).decode():bytes([83,101,108,108]).decode()})
	elif B==bytes([75,66,83]).decode():A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()].replace({bytes([66]).decode():bytes([66,117,121]).decode(),bytes([83]).decode():bytes([83,101,108,108]).decode()})
	C=bytes([117,110,107,110,111,119,110]).decode()if B in[bytes([86,67,73]).decode(),bytes([77,65,83]).decode()]else''
	if asset_type==bytes([115,116,111,99,107]).decode()and(A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()].eq(C).any()or A[bytes([109,97,116,99,104,95,116,121,112,101]).decode()].eq('').any()):
		A=A.sort_values(bytes([116,105,109,101]).decode());A[bytes([100,97,116,101]).decode()]=A[bytes([116,105,109,101]).decode()].dt.date
		def D(day_df):
			B=day_df;A=B[B[bytes([109,97,116,99,104,95,116,121,112,101]).decode()]==C]
			if A.empty:return B
			D=A[(A[bytes([116,105,109,101]).decode()].dt.hour==9)&A[bytes([116,105,109,101]).decode()].dt.minute.between(13,17)]
			if not D.empty:F=D[bytes([116,105,109,101]).decode()].idxmin();B.loc[F,bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=bytes([65,84,79]).decode()
			E=A[(A[bytes([116,105,109,101]).decode()].dt.hour==14)&A[bytes([116,105,109,101]).decode()].dt.minute.between(43,47)]
			if not E.empty:G=E[bytes([116,105,109,101]).decode()].idxmax();B.loc[G,bytes([109,97,116,99,104,95,116,121,112,101]).decode()]=bytes([65,84,67]).decode()
			return B
		try:A=A.groupby(bytes([100,97,116,101]).decode(),group_keys=False).apply(D,include_groups=False)
		except TypeError:A=A.groupby(bytes([100,97,116,101]).decode(),group_keys=False).apply(D)
		if bytes([100,97,116,101]).decode()in A.columns:A.drop(columns=[bytes([100,97,116,101]).decode()],inplace=True)
	return A
def ohlc_to_df(data,column_map,dtype_map,asset_type,symbol,source,interval=bytes([49,68]).decode(),floating=2,resample_map=None):
	'\n    Convert OHLC data from any source to standardized DataFrame format.\n    \n    Supports all 14 intervals: 1m, 5m, 15m, 30m, 1H, 4h, 1D, 1W, 1M\n    ';I=interval;H=asset_type;F=source;E=column_map;D=data;C=resample_map
	if not D:raise ValueError(bytes([73,110,112,117,116,32,100,97,116,97,32,105,115,32,101,109,112,116,121,32,111,114,32,110,111,116,32,112,114,111,118,105,100,101,100,46]).decode())
	try:G=normalize_interval(I)
	except ValueError as L:raise ValueError(f"Invalid interval '{I}': {L!s}")
	if F==bytes([84,67,66,83]).decode():A=pd.DataFrame(D);A.rename(columns=E,inplace=True)
	else:M={A:E[A]for A in E.keys()if A in D};A=pd.DataFrame(D)[M.keys()].rename(columns=E)
	N=[bytes([116,105,109,101]).decode(),bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode(),bytes([118,111,108,117,109,101]).decode()];J=[B for B in N if B not in A.columns]
	if J:O=A.columns.tolist();raise ValueError(f"Missing required columns: {J}. Available columns: {O}")
	A=A[[bytes([116,105,109,101]).decode(),bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode(),bytes([118,111,108,117,109,101]).decode()]]
	if bytes([116,105,109,101]).decode()in A.columns:
		if F==bytes([86,67,73]).decode():A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()].astype(int),unit=bytes([115]).decode()).dt.tz_localize(bytes([85,84,67]).decode());A[bytes([116,105,109,101]).decode()]=A[bytes([116,105,109,101]).decode()].dt.tz_convert(bytes([65,115,105,97,47,72,111,95,67,104,105,95,77,105,110,104]).decode())
		elif F==bytes([77,65,83]).decode():A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()].astype(float),unit=bytes([115]).decode()).dt.tz_localize(bytes([85,84,67]).decode()).dt.tz_convert(bytes([65,115,105,97,47,72,111,95,67,104,105,95,77,105,110,104]).decode())
		else:A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()],errors=bytes([99,111,101,114,99,101]).decode())
	if H not in[bytes([105,110,100,101,120]).decode(),bytes([100,101,114,105,118,97,116,105,118,101]).decode()]:A[[bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode()]]=A[[bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode()]].div(1000)
	A[[bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode()]]=A[[bytes([111,112,101,110]).decode(),bytes([104,105,103,104]).decode(),bytes([108,111,119]).decode(),bytes([99,108,111,115,101]).decode()]].round(floating)
	if C is None:C=_get_default_resample_map()
	P=[TimeFrame.MINUTE_1,TimeFrame.HOUR_1,TimeFrame.DAY_1]
	if G not in P and C:
		if G.value in C:A=A.set_index(bytes([116,105,109,101]).decode()).resample(C[G.value]).agg({bytes([111,112,101,110]).decode():bytes([102,105,114,115,116]).decode(),bytes([104,105,103,104]).decode():bytes([109,97,120]).decode(),bytes([108,111,119]).decode():bytes([109,105,110]).decode(),bytes([99,108,111,115,101]).decode():bytes([108,97,115,116]).decode(),bytes([118,111,108,117,109,101]).decode():bytes([115,117,109]).decode()}).dropna(subset=[bytes([111,112,101,110]).decode(),bytes([99,108,111,115,101]).decode()]).reset_index()
	for(B,K)in dtype_map.items():
		if B in A.columns:
			if K==bytes([100,97,116,101,116,105,109,101,54,52,91,110,115,93]).decode()and hasattr(A[B],bytes([100,116]).decode())and A[B].dt.tz is not None:
				A[B]=A[B].dt.tz_localize(None)
				if G in[TimeFrame.DAY_1,TimeFrame.DAILY]:A[B]=A[B].dt.date
			A[B]=A[B].astype(K)
	A.name=symbol;A.category=H;A.source=F;return A
def _get_default_resample_map():'\n    Get default resample frequency mapping for all 14 intervals.\n    \n    Returns:\n        dict: Mapping of TimeFrame value to pandas resample frequency\n    ';return{bytes([49,109]).decode():bytes([49,109,105,110]).decode(),bytes([53,109]).decode():bytes([53,109,105,110]).decode(),bytes([49,53,109]).decode():bytes([49,53,109,105,110]).decode(),bytes([51,48,109]).decode():bytes([51,48,109,105,110]).decode(),bytes([49,72]).decode():bytes([49,72]).decode(),bytes([52,104]).decode():bytes([52,72]).decode(),bytes([49,68]).decode():bytes([49,68]).decode(),bytes([49,87]).decode():bytes([49,87]).decode(),bytes([49,77]).decode():bytes([49,77,83]).decode()}
def intraday_to_df(data,column_map,dtype_map,symbol,asset_type,source):
	'\n    Convert intraday trading data to standardized DataFrame format,\n    với:\n      - Tiền xử lý chuỗi số cho price/volume\n      - Map scale dựa trên source (không hardcode /1000)\n      - Kiểm soát NaN, rounding volume an toàn\n      - Xử lý time, match_type như trước\n    ';I=symbol;F=asset_type;D=column_map;C=source
	if not data:E=pd.DataFrame(columns=list(D.values()));E.attrs[bytes([115,121,109,98,111,108]).decode()]=I;E.category=F;E.source=C;return E
	A=pd.DataFrame(data);G=[B for B in D if B in A.columns]
	if not G:O=list(D);P=A.columns.tolist();raise ValueError(f"Expected columns {O} not found, got {P}")
	A=A[G].rename(columns={A:D[A]for A in G})
	for B in(bytes([112,114,105,99,101]).decode(),bytes([118,111,108,117,109,101]).decode()):
		if B in A.columns:
			A[B]=A[B].map(clean_numeric_string);A[B]=pd.to_numeric(A[B],errors=bytes([99,111,101,114,99,101]).decode());J=A[B].isna().sum()
			if J:H=bytes([91,87,97,114,110,105,110,103,93,32]).decode()+str(J)+bytes([32,103,105,195,161,32,116,114,225,187,139,32,225,187,159,32,39]).decode()+B+bytes([39,32,107,104,195,180,110,103,32,112,97,114,115,101,32,196,145,198,176,225,187,163,99,44,32,99,104,117,121,225,187,131,110,32,116,104,195,160,110,104,32,78,97,78]).decode();print(H)
	Q={bytes([86,67,73]).decode():1000,bytes([77,65,83]).decode():1000};R=Q.get(C,1)
	if bytes([112,114,105,99,101]).decode()in A.columns:A[bytes([112,114,105,99,101]).decode()]=A[bytes([112,114,105,99,101]).decode()]/R
	if bytes([118,111,108,117,109,101]).decode()in A.columns:
		K=A[bytes([118,111,108,117,109,101]).decode()].fillna(0);L=K%1!=0
		if L.any():S=int(L.sum());H=f"[Info] {S} giá trị volume có decimal, sẽ làm tròn";print(H)
		A[bytes([118,111,108,117,109,101]).decode()]=K.round().astype(int)
	if bytes([116,105,109,101]).decode()in A.columns:
		T=get_trading_date()
		if C==bytes([86,67,73]).decode():A[bytes([116,105,109,101]).decode()]=localize_timestamp(A[bytes([116,105,109,101]).decode()].astype(int),unit=bytes([115]).decode())
		elif C==bytes([77,65,83]).decode():A[bytes([116,105,109,101]).decode()]=localize_timestamp(A[bytes([116,105,109,101]).decode()].astype(int),unit=bytes([109,115]).decode());A[bytes([116,105,109,101]).decode()]=A[bytes([116,105,109,101]).decode()].dt.floor(bytes([115]).decode())
		else:
			M=str(A[bytes([116,105,109,101]).decode()].iloc[0])if not A.empty else''
			if bytes([58]).decode()in M and len(M)<=8:A[bytes([116,105,109,101]).decode()]=A[bytes([116,105,109,101]).decode()].apply(lambda x:datetime.combine(T,datetime.strptime(x,bytes([37,72,58,37,77,58,37,83]).decode()).time())if isinstance(x,str)and bytes([58]).decode()in x else pd.NaT);A[bytes([116,105,109,101]).decode()]=localize_timestamp(A[bytes([116,105,109,101]).decode()],return_string=False)
			else:
				A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()],format=bytes([37,89,45,37,109,45,37,100,32,37,72,58,37,77,58,37,83]).decode(),errors=bytes([99,111,101,114,99,101]).decode())
				if A[bytes([116,105,109,101]).decode()].dt.tz is None:A[bytes([116,105,109,101]).decode()]=localize_timestamp(A[bytes([116,105,109,101]).decode()],return_string=False)
	if bytes([109,97,116,99,104,95,116,121,112,101]).decode()in A.columns:A=process_match_types(A,F,C)
	if bytes([116,105,109,101]).decode()in A.columns:A=A.sort_values(bytes([116,105,109,101]).decode())
	A=A.reset_index(drop=True);N={B:C for(B,C)in dtype_map.items()if B in A.columns and B!=bytes([116,105,109,101]).decode()}
	if N:A=A.astype(N)
	A.attrs[bytes([115,121,109,98,111,108]).decode()]=I;A.category=F;A.source=C;return A