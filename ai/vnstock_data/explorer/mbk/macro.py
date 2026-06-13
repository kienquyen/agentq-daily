from datetime import date,datetime
import pandas as pd
from vnai import agg_execution
from vnstock.core.utils.lookback import get_start_date_from_lookback
from vnstock.core.utils.parser import camel_to_snake
from vnstock.core.utils.transform import reorder_cols
from vnstock_data.core.utils.client import send_request
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.mbk.const import _BASE_URL,MACRO_DATA,REPORT_PERIOD,TYPE_ID
def process_report_dates(df,last_updated_col,keep_label=True):
	"\n    Processes input series index to clean up and convert it to YYYY-mm-dd format.\n\n    Parameters:\n    df (pd.DataFrame): DataFrame whose index contains date information.\n    last_updated_col (str): Column name in df with the last updated dates (format 'YYYY-mm-dd' or datetime.date).\n    keep_label (bool): Whether to keep the original index as a column named 'original_index'.\n\n    Returns:\n    pd.DataFrame: DataFrame with two additional columns:\n        - report_time (converted to 'YYYY-mm-dd')\n        - report_type (extracted from original index)\n    ";B=df;I=[];J=[]
	for(F,G)in zip(B.index,B[last_updated_col],strict=False):
		if isinstance(G,date):K=G
		else:K=datetime.strptime(str(G),bytes([37,89,45,37,109,45,37,100]).decode()).date()
		if bytes([47]).decode()in str(F):A,C=str(F).split(bytes([47]).decode());C=int(C)
		else:
			A=str(F)
			try:C=int(A);A=bytes([78,196,131,109]).decode()
			except ValueError:raise ValueError(f"Unrecognized report type: {A}")
		if bytes([81,117,195,189]).decode()in A:
			H=int(A.split(bytes([32]).decode())[1]);L=H*3;D=date(C,L,1)
			if H==4 and K.year>C:D=date(C,12,31)
			E=f"Quý {H}"
		elif bytes([54,32,116,104,195,161,110,103]).decode()in A:D=date(C,6,30);E=bytes([54,32,116,104,195,161,110,103]).decode()
		elif bytes([57,32,116,104,195,161,110,103]).decode()in A:D=date(C,9,30);E=bytes([57,32,116,104,195,161,110,103]).decode()
		elif bytes([78,196,131,109]).decode()in A or A.isdigit():D=date(C,12,31);E=bytes([78,196,131,109]).decode()
		else:raise ValueError(f"Unrecognized report type: {A}")
		I.append(D.strftime(bytes([37,89,45,37,109,45,37,100]).decode()));J.append(E)
	B=B.copy()
	if keep_label:B[bytes([108,97,98,101,108]).decode()]=B.index
	B.index=I;B[bytes([114,101,112,111,114,116,95,116,121,112,101]).decode()]=J;return B
class Macro:
	"\n    A dedicated class for fetching macroeconomic data from MaybankTrade's API.\n\n    This class abstracts the common logic for retrieving macroeconomic data\n    (GDP, CPI, etc.) via a generalized data fetching method.\n\n    Attributes:\n        start (str): The default start period in the format 'YYYY-MM'.\n        end (str): The default end period in the format 'YYYY-MM'.\n        headers (dict): HTTP headers including a User-Agent for making requests.\n        show_log (bool): Flag to enable or disable logging for debugging.\n        data_source (str): Constant data source identifier ('MBK').\n\n    Methods:\n        _fetch_macro_data(indicator: str, start: str, end: str, period: str) -> pd.DataFrame:\n            Internal method to fetch and standardize data for a given indicator.\n        gdp(start: str, end: str, period: str) -> pd.DataFrame:\n            Fetches and returns standardized GDP data.\n        cpi(start: str, end: str, period: str) -> pd.DataFrame:\n            Fetches and returns standardized CPI data.\n    "
	def __init__(A,random_agent=False,show_log=False):'\n        Initializes the Macro class with a date range and API configuration.\n\n        Args:\n            random_agent (bool, optional): Use a random user agent if True. Defaults to False.\n            show_log (bool, optional): Toggle logging output. Defaults to False.\n        ';A.data_source=bytes([77,66,75]).decode();A.headers=get_headers(data_source=A.data_source,random_agent=random_agent);A.headers[bytes([99,111,110,116,101,110,116,45,116,121,112,101]).decode()]=bytes([97,112,112,108,105,99,97,116,105,111,110,47,120,45,119,119,119,45,102,111,114,109,45,117,114,108,101,110,99,111,100,101,100,59,32,99,104,97,114,115,101,116,61,85,84,70,45,56]).decode();A.show_log=show_log
	def _fetch_macro_data(L,indicator,start=None,end=None,period=bytes([113,117,97,114,116,101,114]).decode(),length=None):
		"\n        Internal method to fetch and process macroeconomic data for a given indicator.\n\n        This method validates the date inputs based on the indicator type,\n        constructs a raw-text payload, sends an API request, and processes the returned data.\n\n        Args:\n            indicator (str): The economic indicator key as defined in TYPE_ID (e.g., 'gdp', 'cpi', 'exchange_rate').\n            start (str): Start date. For 'exchange_rate', the format must be 'YYYY-mm-dd';\n                        for other indicators, the format must be 'YYYY-mm'.\n            end (str): End date. For 'exchange_rate', the format must be 'YYYY-mm-dd';\n                    for other indicators, the format must be 'YYYY-mm'.\n            period (str, optional): Report period type. Commonly 'quarter' or 'day'. Defaults to 'quarter'.\n\n        Raises:\n            ValueError: If the report period is unsupported, if date formats are invalid,\n                        or if the indicator code is not found in the TYPE_ID mapping.\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized macroeconomic data with 'report_time' as the index.\n        ";M=start;K=indicator;H=length;D=period;T=f"{_BASE_URL}{MACRO_DATA}";N=REPORT_PERIOD.get(D)
		if N is None:raise ValueError(f"Unsupported report period type: {D}")
		if end is None:B=datetime.now().strftime(bytes([37,89,45,37,109,45,37,100]).decode())
		else:
			F=str(end)
			if len(F)==4 and F.isdigit():B=f"{F}-12-31"
			elif len(F)==7 and bytes([45]).decode()in F:U,V=map(int,F.split(bytes([45]).decode()));B=pd.Period(f"{U}-{V}",freq=bytes([77]).decode()).end_time.strftime(bytes([37,89,45,37,109,45,37,100]).decode())
			else:B=F
		if M is None:
			if H is not None:
				E=str(H).upper()
				if E.endswith(bytes([66]).decode()):E=E[:-1]+bytes([68]).decode();C=get_start_date_from_lookback(lookback_length=E,end_date=B)
				elif E.isdigit():
					if D==bytes([100,97,121]).decode():E+=bytes([68]).decode();C=get_start_date_from_lookback(lookback_length=E,end_date=B)
					else:C=get_start_date_from_lookback(lookback_length=bytes([50,48,89]).decode(),end_date=B)
				else:C=get_start_date_from_lookback(lookback_length=E,end_date=B)
			else:W=bytes([49,89]).decode()if D==bytes([100,97,121]).decode()else bytes([49,48,89]).decode();C=get_start_date_from_lookback(lookback_length=W,end_date=B)
		else:
			G=str(M)
			if len(G)==4 and G.isdigit():C=f"{G}-01-01"
			elif len(G)==7 and bytes([45]).decode()in G:C=f"{G}-01"
			else:C=G
		O=C.split(bytes([45]).decode());P=B.split(bytes([45]).decode());X=O[0];Y=P[0]
		if K in[bytes([101,120,99,104,97,110,103,101,95,114,97,116,101]).decode(),bytes([105,110,116,101,114,101,115,116,95,114,97,116,101]).decode()]and D==bytes([100,97,121]).decode():I=C;J=B
		elif D==bytes([121,101,97,114]).decode():I=bytes([48]).decode();J=bytes([48]).decode()
		else:
			Q=O[1];R=P[1]
			if D==bytes([113,117,97,114,116,101,114]).decode():Z=(int(Q)-1)//3;a=(int(R)-1)//3;I=str(Z);J=str(a)
			elif D==bytes([109,111,110,116,104]).decode():I=str(int(Q));J=str(int(R))
			else:I=bytes([48]).decode();J=bytes([48]).decode()
		S=TYPE_ID.get(K)
		if S is None:raise ValueError(f"{K} report type code is not defined in TYPE_ID mapping")
		b=f"type={N}&fromYear={X}&toYear={Y}&from={I}&to={J}&normTypeID={S}";c=send_request(url=T,headers=L.headers,method=bytes([80,79,83,84]).decode(),payload=b,show_log=L.show_log);A=pd.DataFrame(c);A.columns=[camel_to_snake(A)for A in A.columns];A.columns=A.columns.str.replace(bytes([116,101,114,110,95]).decode(),'',regex=False).str.replace(bytes([110,111,114,109,95]).decode(),'',regex=False).str.replace(bytes([116,101,114,109,95]).decode(),'',regex=False).str.replace(bytes([102,114,111,109,95]).decode(),'',regex=False).str.replace(bytes([95,99,111,100,101]).decode(),'',regex=False)
		if bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()in A.columns:A=A[A[bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()]!=bytes([48]).decode()].copy()
		d=pd.to_numeric(A[bytes([100,97,121]).decode()].str.replace(bytes([47,68,97,116,101,40]).decode(),'',regex=False).str.replace(bytes([41,47]).decode(),'',regex=False));A[bytes([100,97,121]).decode()]=pd.to_datetime(d,unit=bytes([109,115]).decode()).dt.date;e=[bytes([114,101,112,111,114,116,95,100,97,116,97,95,105,100]).decode(),bytes([105,100]).decode(),bytes([121,101,97,114]).decode(),bytes([103,114,111,117,112,95,105,100]).decode(),bytes([99,115,115,95,115,116,121,108,101]).decode(),bytes([116,121,112,101,95,105,100]).decode()];A=A.drop(columns=e,errors=bytes([105,103,110,111,114,101]).decode());A=reorder_cols(A,cols=[bytes([117,110,105,116]).decode(),bytes([115,111,117,114,99,101]).decode()],position=bytes([108,97,115,116]).decode());A=reorder_cols(A,cols=[bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()],position=bytes([102,105,114,115,116]).decode())
		if A[bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()].str.contains(bytes([84,104,195,161,110,103,32]).decode()).any():A[bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()]=A[bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()].str.replace(bytes([84,104,195,161,110,103,32]).decode(),'',regex=False);A[bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()]=A[bytes([114,101,112,111,114,116,95,116,105,109,101]).decode()].apply(lambda x:pd.Period(x,freq=bytes([77]).decode()).end_time.date()if isinstance(x,str)else x)
		A.set_index(bytes([114,101,112,111,114,116,95,116,105,109,101]).decode(),inplace=True);A=A.sort_index(ascending=True);A.rename(columns={bytes([100,97,121]).decode():bytes([108,97,115,116,95,117,112,100,97,116,101,100]).decode()},inplace=True)
		if H is not None and str(H).isdigit():A=A.tail(int(H)).copy()
		return A
	@agg_execution(bytes([77,66,75]).decode())
	def gdp(self,start=None,end=None,period=bytes([113,117,97,114,116,101,114]).decode(),keep_label=False,length=None):
		"\n        Fetches GDP data for the specified period.\n\n        Args:\n            start (str, optional): Start date in the format 'YYYY-MM'. Defaults to '2015-01'.\n            end (str, optional): End date in the format 'YYYY-MM'. Defaults to '2025-04'.\n            period (str, optional): Report period type. Defaults to 'quarter'.\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized GDP data.\n        ";B=period
		if B not in[bytes([113,117,97,114,116,101,114]).decode(),bytes([121,101,97,114]).decode()]:raise ValueError(f"Unsupported report period type: {B}")
		A=self._fetch_macro_data(bytes([103,100,112]).decode(),start,end,B,length=length);A=process_report_dates(A,last_updated_col=bytes([108,97,115,116,95,117,112,100,97,116,101,100]).decode(),keep_label=keep_label);A.index.name=bytes([114,101,112,111,114,116,95,116,105,109,101]).decode();A=A.sort_values([bytes([108,97,115,116,95,117,112,100,97,116,101,100]).decode(),bytes([103,114,111,117,112,95,110,97,109,101]).decode(),bytes([110,97,109,101]).decode()]);return A
	@agg_execution(bytes([77,66,75]).decode())
	def cpi(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):
		"\n        Fetches CPI data for the specified period.\n\n        Args:\n            start (str, optional): Start date in the format 'YYYY-MM'. Defaults to '2015-01'.\n            end (str, optional): End date in the format 'YYYY-MM'. Defaults to '2025-04'.\n            period (str, optional): Report period type. Defaults to 'quarter'.\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized CPI data.\n        ";B=period
		if B not in[bytes([109,111,110,116,104]).decode(),bytes([121,101,97,114]).decode()]:raise ValueError(f"Unsupported report period type: {B}")
		A=self._fetch_macro_data(bytes([99,112,105]).decode(),start,end,B,length=length)
		if bytes([103,114,111,117,112,95,110,97,109,101]).decode()in A.columns:A=A.drop(columns=[bytes([103,114,111,117,112,95,110,97,109,101]).decode()])
		return A
	@agg_execution(bytes([77,66,75]).decode())
	def industry_prod(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):
		"\n        Fetches Industrial Production data for the specified period.\n\n        Args:\n            start (str, optional): Start date in the format 'YYYY-MM'. Defaults to '2015-01'.\n            end (str, optional): End date in the format 'YYYY-MM'. Defaults to '2025-04'.\n            period (str, optional): Report period type. Defaults to 'quarter'.\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized Industrial Production data.\n        ";A=period
		if A not in[bytes([109,111,110,116,104]).decode(),bytes([121,101,97,114]).decode()]:raise ValueError(f"Unsupported report period type: {A}")
		return self._fetch_macro_data(bytes([105,110,100,117,115,116,114,105,97,108,95,112,114,111,100,117,99,116,105,111,110]).decode(),start,end,A,length=length)
	@agg_execution(bytes([77,66,75]).decode())
	def import_export(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):
		"\n        Fetches Import-Export data for the specified period.\n\n        Args:\n            start (str, optional): Start date in the format 'YYYY-MM'. Defaults to '2015-01'.\n            end (str, optional): End date in the format 'YYYY-MM'. Defaults to '2025-04'.\n            period (str, optional): Report period type. Defaults to 'quarter'.\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized Import-Export data.\n        ";B=period
		if B not in[bytes([109,111,110,116,104]).decode(),bytes([121,101,97,114]).decode()]:raise ValueError(f"Unsupported report period type: {B}")
		A=self._fetch_macro_data(bytes([101,120,112,111,114,116,95,105,109,112,111,114,116]).decode(),start,end,B,length=length)
		if bytes([103,114,111,117,112,95,110,97,109,101]).decode()in A.columns:A=A.drop(columns=[bytes([103,114,111,117,112,95,110,97,109,101]).decode()])
		return A
	@agg_execution(bytes([77,66,75]).decode())
	def retail(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):
		"\n        Fetches Retail data for the specified period.\n\n        Args:\n            start (str, optional): Start date in the format 'YYYY-MM'. Defaults to '2015-01'.\n            end (str, optional): End date in the format 'YYYY-MM'. Defaults to '2025-04'.\n            period (str, optional): Report period type. Defaults to 'quarter'.\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized Retail data.\n        ";B=period
		if B not in[bytes([109,111,110,116,104]).decode(),bytes([121,101,97,114]).decode()]:raise ValueError(f"Unsupported report period type: {B}")
		A=self._fetch_macro_data(bytes([114,101,116,97,105,108]).decode(),start,end,B,length=length)
		if bytes([103,114,111,117,112,95,110,97,109,101]).decode()in A.columns:A=A.drop(columns=[bytes([103,114,111,117,112,95,110,97,109,101]).decode()])
		return A
	@agg_execution(bytes([77,66,75]).decode())
	def fdi(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):
		"\n        Fetches Foreign Direct Investment data for the specified period.\n\n        Args:\n            start (str, optional): Start date in the format 'YYYY-MM'. Defaults to '2015-01'.\n            end (str, optional): End date in the format 'YYYY-MM'. Defaults to '2025-04'.\n            period (str, optional): Report period type. Defaults to 'quarter'.\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized Foreign Direct Investment data.\n        ";A=period
		if A not in[bytes([109,111,110,116,104]).decode(),bytes([121,101,97,114]).decode()]:raise ValueError(f"Unsupported report period type: {A}")
		return self._fetch_macro_data(bytes([102,100,105]).decode(),start,end,A,length=length)
	@agg_execution(bytes([77,66,75]).decode())
	def money_supply(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):
		"\n        Fetches money supply data for the specified period.\n\n        Args:\n            start (str, optional): Start date in the format 'YYYY-MM'. Defaults to '2015-01'.\n            end (str, optional): End date in the format 'YYYY-MM'. Defaults to '2025-04'.\n            period (str, optional): Report period type. Defaults to 'quarter'.\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized Foreign Direct Investment data.\n        ";B=period
		if B not in[bytes([109,111,110,116,104]).decode(),bytes([121,101,97,114]).decode()]:raise ValueError(f"Unsupported report period type: {B}")
		A=self._fetch_macro_data(bytes([109,111,110,101,121,95,115,117,112,112,108,121]).decode(),start,end,B,length=length)
		if bytes([103,114,111,117,112,95,110,97,109,101]).decode()in A.columns:A=A.drop(columns=[bytes([103,114,111,117,112,95,110,97,109,101]).decode()])
		return A
	@agg_execution(bytes([77,66,75]).decode())
	def interest_rate(self,start=None,end=None,period=bytes([100,97,121]).decode(),format=bytes([112,105,118,111,116]).decode(),length=None):
		"\n        Fetches Interest Rate data for the specified period.\n\n        Args:\n            start (str, optional): Start date in the format 'YYYY-MM-DD'. Defaults to '2025-01-02'.\n            end (str, optional): End date in the format 'YYYY-MM-DD'. Defaults to '2025-04-10'.\n            period (str, optional): Report period type. Defaults to 'day'.\n            format (str, optional): Format of the returned DataFrame. Options: 'pivot' (default wide table) or 'long' (raw flat table).\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized Interest Rate data.\n        ";B=period
		if B not in[bytes([100,97,121]).decode(),bytes([121,101,97,114]).decode()]:raise ValueError(f"Unsupported report period type: {B}")
		if format not in[bytes([112,105,118,111,116]).decode(),bytes([108,111,110,103]).decode()]:raise ValueError(f"Unsupported format type: {format}. Use 'pivot' or 'long'.")
		A=self._fetch_macro_data(bytes([105,110,116,101,114,101,115,116,95,114,97,116,101]).decode(),start,end,B,length=length);A.index=pd.to_datetime(A.index,dayfirst=True)
		if format==bytes([112,105,118,111,116]).decode():A=A.pivot_table(index=bytes([114,101,112,111,114,116,95,116,105,109,101]).decode(),columns=[bytes([103,114,111,117,112,95,110,97,109,101]).decode(),bytes([110,97,109,101]).decode()],values=bytes([118,97,108,117,101]).decode());A=A.sort_index(axis=1,level=[0,1]);A=A.ffill()
		return A
	@agg_execution(bytes([77,66,75]).decode())
	def exchange_rate(self,start=None,end=None,period=bytes([100,97,121]).decode(),length=None):
		"\n        Fetches Real Interest exchange_rate data for the specified period.\n\n        Args:\n            start (str, optional): Start date in the format 'YYYY-MM'. Defaults to '2015-01'.\n            end (str, optional): End date in the format 'YYYY-MM'. Defaults to '2025-04'.\n            period (str, optional): Report period type. Defaults to 'quarter'.\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized Real Interest exchange_rate data.\n        ";B=period
		if B not in[bytes([100,97,121]).decode(),bytes([121,101,97,114]).decode()]:raise ValueError(f"Unsupported report period type: {B}")
		A=self._fetch_macro_data(bytes([101,120,99,104,97,110,103,101,95,114,97,116,101]).decode(),start,end,B,length=length)
		if bytes([103,114,111,117,112,95,110,97,109,101]).decode()in A.columns:A=A.drop(columns=[bytes([103,114,111,117,112,95,110,97,109,101]).decode()])
		A.index=pd.to_datetime(A.index,dayfirst=True);return A
	@agg_execution(bytes([77,66,75]).decode())
	def population_labor(self,start=None,end=None,period=bytes([121,101,97,114]).decode(),length=None):
		"\n        Fetches Population and Labor data for the specified period.\n\n        Args:\n            start (str, optional): Start date in the format 'YYYY-MM'. Defaults to '2015-01'.\n            end (str, optional): End date in the format 'YYYY-MM'. Defaults to '2025-04'.\n            period (str, optional): Report period type. Defaults to 'quarter'.\n\n        Returns:\n            pd.DataFrame: A DataFrame containing the standardized Population and Labor data.\n        ";B=period
		if B not in[bytes([109,111,110,116,104]).decode(),bytes([121,101,97,114]).decode()]:raise ValueError(f"Unsupported report period type: {B}")
		A=self._fetch_macro_data(bytes([112,111,112,117,108,97,116,105,111,110,95,108,97,98,111,114]).decode(),start,end,B,length=length)
		if bytes([103,114,111,117,112,95,110,97,109,101]).decode()in A.columns:A=A.drop(columns=[bytes([103,114,111,117,112,95,110,97,109,101]).decode()])
		return A
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([109,97,99,114,111]).decode(),bytes([109,98,107]).decode(),Macro)