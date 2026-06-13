import json,time
from typing import Any
import pandas as pd
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake,flatten_data,get_asset_type
from vnstock.core.utils.transform import flatten_hierarchical_index
from vnstock.explorer.vci.const import _TRADING_URL
from vnstock_data.core.utils.client import ProxyConfig,send_request
from vnstock_data.core.utils.parser import filter_columns_by_language
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.core.utils.validation import validate_date
from vnstock_data.explorer.vci.const import _ODD_LOT_STANDARD_COLUMNS,_ODD_LOT_URL,_PRICE_BOARD_STANDARD_COLUMNS,_PUT_THROUGH_STANDARD_COLUMNS,_PUT_THROUGH_URL,_REPORT_RESOLUTION,_STOCK_BOARD_STANDARD_COLUMNS,_VCI_COMPANY_URL,_VCI_INDEX_MAPPING,_VCI_MARKET_INDICES_URL,_VCIQ_URL
logger=get_logger(__name__)
class Trading:
	'\n    Truy xuất dữ liệu giao dịch của mã chứng khoán từ nguồn dữ liệu VCI.\n    '
	def __init__(A,symbol=None,random_agent=False,proxy_config=None,show_log=False):
		D=show_log;C=proxy_config;B=symbol
		if isinstance(B,list):A.symbol=[A.upper()for A in B];A.asset_type=None
		else:
			A.symbol=B.upper()if B else'';A.asset_type=get_asset_type(A.symbol)if A.symbol else None
			if A.asset_type==bytes([105,110,100,101,120]).decode()and A.symbol in _VCI_INDEX_MAPPING:A.symbol=_VCI_INDEX_MAPPING[A.symbol]
		A.base_url=_VCIQ_URL;A.headers=get_headers(data_source=bytes([86,67,73]).decode(),random_agent=random_agent);A.proxy_config=C if C is not None else ProxyConfig()
		if not D:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
		A.show_log=D
	def _process_dates(C,start,end):
		'\n        Validate and process start/end dates for API requests.\n        \n        Args:\n            start (str, optional): Start date in YYYY-mm-dd format\n            end (str, optional): End date in YYYY-mm-dd format\n            \n        Returns:\n            tuple: Processed dates in YYYYMMDD format or (None, None) if invalid\n        ';B=end;A=start
		if A and B:
			if not validate_date(A)or not validate_date(B):logger.error(bytes([73,110,118,97,108,105,100,32,100,97,116,101,32,102,111,114,109,97,116,46,32,80,108,101,97,115,101,32,117,115,101,32,116,104,101,32,102,111,114,109,97,116,32,89,89,89,89,45,109,109,45,100,100,46]).decode());return None,None
			else:return A.replace(bytes([45]).decode(),''),B.replace(bytes([45]).decode(),'')
		return None,None
	def _fetch_data(A,endpoint,params):
		"\n        Core function to fetch data from VCI API endpoints.\n        \n        Args:\n            endpoint (str): API endpoint path (e.g., 'price-history-summary')\n            params (dict): Query parameters for the API request\n            \n        Returns:\n            dict: Raw JSON response from VCI API\n            \n        Raises:\n            requests.exceptions.RequestException: For HTTP-related errors\n            ValueError: For JSON parsing errors\n        ";C=params;B=endpoint
		if A.asset_type==bytes([105,110,100,101,120]).decode():
			if B in[bytes([112,114,105,99,101,45,104,105,115,116,111,114,121]).decode(),bytes([112,114,105,99,101,45,104,105,115,116,111,114,121,45,115,117,109,109,97,114,121]).decode()]:D=f"{_VCI_MARKET_INDICES_URL}/history";C[bytes([105,110,100,101,120]).decode()]=A.symbol
			else:D=f"{_VCI_MARKET_INDICES_URL}/{B}";C[bytes([105,110,100,101,120]).decode()]=A.symbol
		else:D=f"{_VCI_COMPANY_URL}/{A.symbol}/{B}"
		try:
			E=send_request(D,headers=A.headers,method=bytes([71,69,84]).decode(),params=C,show_log=A.show_log,proxy_list=A.proxy_config.proxy_list,proxy_mode=A.proxy_config.proxy_mode,request_mode=A.proxy_config.request_mode)
			if A.show_log:logger.info(f"Successfully fetched data from {B} for {A.symbol}")
			return E
		except Exception as F:logger.error(f"Error fetching data from {B} for {A.symbol}: {F}");raise
	def _to_dataframe(D,data,data_path=None):
		"\n        Convert API response data to pandas DataFrame with flexible data path extraction.\n        \n        Args:\n            data (dict): Raw JSON response from API\n            data_path (list, optional): Path to extract data from nested structure \n                                       (e.g., ['data'] or ['data', 'content'])\n                                       If None, defaults to ['data']\n            \n        Returns:\n            pd.DataFrame: Processed DataFrame with snake_case columns\n        ";B=data_path
		try:
			if B is None:B=[bytes([100,97,116,97]).decode()]
			A=data
			for E in B:
				if isinstance(A,dict)and E in A:A=A[E]
				else:logger.warning(f"Data path {B} not found in response for {D.symbol}");return pd.DataFrame()
			if not A:logger.warning(f"No data found at path {B} for {D.symbol}");return pd.DataFrame()
			if isinstance(A,list):C=pd.DataFrame(A)
			elif isinstance(A,dict):C=pd.DataFrame([A])
			else:logger.error(f"Unexpected data type at path {B}: {type(A)}");return pd.DataFrame()
			if not C.empty:C.columns=[camel_to_snake(A)for A in C.columns]
			return C
		except(KeyError,TypeError,Exception)as F:logger.error(f"Unexpected error processing data for {D.symbol}: {F}");raise
	def _process_bid_ask_data(F,item,row):
		'\n        Extract and process bid/ask prices and volumes from item data.\n        \n        Args:\n            item (dict): Raw item data from API response\n            row (dict): Row dictionary to populate with bid/ask data\n        ';B=row
		try:
			C=item.get(bytes([98,105,100,65,115,107]).decode(),{});G=C.get(bytes([98,105,100,80,114,105,99,101,115]).decode(),[])
			for(A,D)in enumerate(G,start=1):B[f"bidAsk_bid_{A}_price"]=D.get(bytes([112,114,105,99,101]).decode());B[f"bidAsk_bid_{A}_volume"]=D.get(bytes([118,111,108,117,109,101]).decode())
			H=C.get(bytes([97,115,107,80,114,105,99,101,115]).decode(),[])
			for(A,E)in enumerate(H,start=1):B[f"bidAsk_ask_{A}_price"]=E.get(bytes([112,114,105,99,101]).decode());B[f"bidAsk_ask_{A}_volume"]=E.get(bytes([118,111,108,117,109,101]).decode())
		except(KeyError,TypeError,AttributeError)as I:logger.debug(f"Error processing bid/ask data for {F.symbol}: {I}")
	def _normalize_exchange_code(B,df,column_name):
		'\n        Normalize exchange codes (HSX → HOSE) for consistency.\n        \n        Args:\n            df (pd.DataFrame): DataFrame to normalize\n            column_name (str): Column name to normalize\n        ';A=column_name
		if A in df.columns:df[A]=df[A].map(lambda x:bytes([72,79,83,69]).decode()if x==bytes([72,83,88]).decode()else x)
	def _flatten_price_board_columns(B,df,separator=bytes([95]).decode(),drop_levels=None):'\n        Flatten hierarchical columns in price board DataFrame.\n        \n        Args:\n            df (pd.DataFrame): DataFrame with MultiIndex columns\n            separator (str): Separator for flattened column names\n            drop_levels (int or list): Levels to drop during flattening\n            \n        Returns:\n            pd.DataFrame: DataFrame with flattened columns\n        ';A=flatten_hierarchical_index(df,separator=separator,drop_levels=drop_levels,handle_duplicates=True);B._normalize_exchange_code(A,bytes([108,105,115,116,105,110,103,95,101,120,99,104,97,110,103,101]).decode());return A
	def _fetch_stock_board(B,symbols_list,show_log=False,flatten_columns=True,separator=bytes([95]).decode(),drop_levels=None):
		"\n        Internal method to fetch stock board (lô chẵn) data.\n        \n        Args:\n            symbols_list (List[str]): List of stock symbols to fetch\n            show_log (bool): Show logging information (default: False)\n            flatten_columns (bool): Flatten hierarchical columns (default: True)\n            separator (str): Separator for flattened column names (default: '_')\n            drop_levels (int or list): Levels to drop during flattening (default: None)\n            \n        Returns:\n            pd.DataFrame: Stock board data with normalized columns\n        ";G=show_log;F=symbols_list;H=f"{_TRADING_URL}price/symbols/getList";I=json.dumps({bytes([115,121,109,98,111,108,115]).decode():F})
		if G:logger.info(f"Requested URL: {H} with query payload: {I}")
		try:J=send_request(H,headers=B.headers,method=bytes([80,79,83,84]).decode(),payload=json.loads(I),show_log=G,proxy_list=B.proxy_config.proxy_list,proxy_mode=B.proxy_config.proxy_mode,request_mode=B.proxy_config.request_mode)
		except Exception as D:logger.error(f"Failed to fetch price board data: {D}");raise
		if not J:raise ConnectionError(bytes([84,225,186,163,105,32,100,225,187,175,32,108,105,225,187,135,117,32,107,104,195,180,110,103,32,116,104,195,160,110,104,32,99,195,180,110,103,32,104,111,225,186,183,99,32,107,104,195,180,110,103,32,99,195,179,32,100,225,187,175,32,108,105,225,187,135,117,32,116,114,225,186,163,32,118,225,187,129,46]).decode())
		E=[]
		for C in J:
			try:L={bytes([108,105,115,116,105,110,103]).decode():C.get(bytes([108,105,115,116,105,110,103,73,110,102,111]).decode(),{}),bytes([98,105,100,65,115,107]).decode():C.get(bytes([98,105,100,65,115,107]).decode(),{}),bytes([109,97,116,99,104]).decode():C.get(bytes([109,97,116,99,104,80,114,105,99,101]).decode(),{})};K=flatten_data(L);B._process_bid_ask_data(C,K);E.append(K)
			except Exception as D:logger.warning(f"Error processing item in price_board: {D}");continue
		if not E:logger.warning(f"No valid data rows found for symbols: {F}");return pd.DataFrame()
		A=pd.DataFrame(E);A.columns=pd.MultiIndex.from_tuples([tuple(camel_to_snake(A)for A in A.split(bytes([95]).decode(),1))for A in A.columns]);M=[(bytes([98,105,100,95,97,115,107]).decode(),bytes([99,111,100,101]).decode()),(bytes([98,105,100,95,97,115,107]).decode(),bytes([115,121,109,98,111,108]).decode()),(bytes([98,105,100,95,97,115,107]).decode(),bytes([115,101,115,115,105,111,110]).decode()),(bytes([98,105,100,95,97,115,107]).decode(),bytes([114,101,99,101,105,118,101,100,95,116,105,109,101]).decode()),(bytes([98,105,100,95,97,115,107]).decode(),bytes([109,101,115,115,97,103,101,95,116,121,112,101]).decode()),(bytes([98,105,100,95,97,115,107]).decode(),bytes([116,105,109,101]).decode()),(bytes([98,105,100,95,97,115,107]).decode(),bytes([98,105,100,95,112,114,105,99,101,115]).decode()),(bytes([98,105,100,95,97,115,107]).decode(),bytes([97,115,107,95,112,114,105,99,101,115]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([99,111,100,101]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([101,120,101,114,99,105,115,101,95,112,114,105,99,101]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([101,120,101,114,99,105,115,101,95,114,97,116,105,111]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([109,97,116,117,114,105,116,121,95,100,97,116,101]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([117,110,100,101,114,108,121,105,110,103,95,115,121,109,98,111,108]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([105,115,115,117,101,114,95,110,97,109,101]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([114,101,99,101,105,118,101,100,95,116,105,109,101]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([109,101,115,115,97,103,101,95,116,121,112,101]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([101,110,95,111,114,103,97,110,95,110,97,109,101]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([101,110,95,111,114,103,97,110,95,115,104,111,114,116,95,110,97,109,101]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([111,114,103,97,110,95,115,104,111,114,116,95,110,97,109,101]).decode()),(bytes([108,105,115,116,105,110,103]).decode(),bytes([116,105,99,107,101,114]).decode()),(bytes([109,97,116,99,104]).decode(),bytes([99,111,100,101]).decode()),(bytes([109,97,116,99,104]).decode(),bytes([115,121,109,98,111,108]).decode()),(bytes([109,97,116,99,104]).decode(),bytes([114,101,99,101,105,118,101,100,95,116,105,109,101]).decode()),(bytes([109,97,116,99,104]).decode(),bytes([109,101,115,115,97,103,101,95,116,121,112,101]).decode()),(bytes([109,97,116,99,104]).decode(),bytes([116,105,109,101]).decode()),(bytes([109,97,116,99,104]).decode(),bytes([115,101,115,115,105,111,110]).decode())];A=A.drop(columns=[B for B in M if B in A.columns]);A=A.rename(columns={bytes([98,111,97,114,100]).decode():bytes([101,120,99,104,97,110,103,101]).decode()},level=1);B._normalize_exchange_code(A,(bytes([108,105,115,116,105,110,103]).decode(),bytes([101,120,99,104,97,110,103,101]).decode()))
		if flatten_columns:A=B._flatten_price_board_columns(A,separator=separator,drop_levels=drop_levels)
		A.attrs[bytes([115,111,117,114,99,101]).decode()]=bytes([86,67,73]).decode();return A
	def _normalize_unified_data(G,df):
		'\n        Normalize VCI unified format data - standardize data types and units.\n        \n        Data Type Standards (semantic correctness):\n        - All prices (open, high, low, close, ceiling, floor, reference, average, bid/ask): float64\n          (Rationale: API provides with decimal precision, maintaining accuracy)\n        - All volumes (bid_vol, ask_vol, total_trades, foreign_volumes): int64\n          (Rationale: Share counts are integers)\n        - total_value: float64, scaled to VND from millions\n          (VCI provides in triệu đ, scale ×1,000,000 to match KBS in VND)\n        - Percentages (percent_change): float64\n        - Identifiers (symbol, exchange): str\n        - Timestamp (time): int64\n        \n        Unit Conversion:\n        - total_value: 771888.25 (triệu đ) → 771888.25 × 1,000,000 = 771,888,250,000 (VND)\n        \n        Args:\n            df (pd.DataFrame): VCI unified format DataFrame (after column renaming to flat structure)\n            \n        Returns:\n            pd.DataFrame: Normalized DataFrame with consistent data types\n        ';A=df
		if A is None or A.empty:return A
		A=A.copy()
		if isinstance(A.columns,pd.MultiIndex):A.columns=A.columns.map(lambda x:bytes([95]).decode().join(str(A)for A in x)if isinstance(x,tuple)else x)
		if bytes([116,111,116,97,108,95,118,97,108,117,101]).decode()in A.columns:
			try:A[bytes([116,111,116,97,108,95,118,97,108,117,101]).decode()]=(A[bytes([116,111,116,97,108,95,118,97,108,117,101]).decode()]*1000000).astype(bytes([102,108,111,97,116,54,52]).decode())
			except Exception as B:logger.warning(f"Could not scale total_value: {B}")
		try:
			D=[A for A in A.columns if isinstance(A,str)and bytes([112,114,105,99,101]).decode()in A.lower()]
			for C in D:
				if C in A.columns:A[C]=A[C].astype(bytes([102,108,111,97,116,54,52]).decode())
		except Exception as B:logger.warning(f"Could not normalize price columns: {B}")
		try:
			E=[A for A in A.columns if isinstance(A,str)and(bytes([118,111,108]).decode()in A.lower()or bytes([118,111,108,117,109,101]).decode()in A.lower()or bytes([116,114,97,100,101,115]).decode()in A.lower())]
			for C in E:
				if C in A.columns and A[C].dtype!=bytes([111,98,106,101,99,116]).decode():A[C]=A[C].astype(bytes([105,110,116,54,52]).decode())
		except Exception as B:logger.warning(f"Could not normalize volume columns: {B}")
		if bytes([114,101,102,101,114,101,110,99,101,95,112,114,105,99,101]).decode()in A.columns and bytes([99,108,111,115,101,95,112,114,105,99,101]).decode()in A.columns:
			try:A[bytes([112,114,105,99,101,95,99,104,97,110,103,101]).decode()]=(A[bytes([99,108,111,115,101,95,112,114,105,99,101]).decode()]-A[bytes([114,101,102,101,114,101,110,99,101,95,112,114,105,99,101]).decode()]).astype(bytes([102,108,111,97,116,54,52]).decode());A[bytes([112,101,114,99,101,110,116,95,99,104,97,110,103,101]).decode()]=(A[bytes([112,114,105,99,101,95,99,104,97,110,103,101]).decode()]/A[bytes([114,101,102,101,114,101,110,99,101,95,112,114,105,99,101]).decode()]*100).round(2)
			except Exception as B:logger.warning(f"Could not calculate price_change/percent_change: {B}")
		try:F=int(time.time()*1000);A[bytes([116,105,109,101]).decode()]=F
		except Exception as B:logger.warning(f"Could not add time column: {B}")
		return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def price_board(self,symbols_list,board=bytes([115,116,111,99,107]).decode(),exchange=bytes([72,79,83,69]).decode(),show_log=False,get_all=False,get_unified=False):
		"\n        Truy xuất bảng giá realtime cho danh sách mã chứng khoán.\n\n        Unified interface để lấy dữ liệu giá từ ba loại bảng giá:\n        - stock: Lô chẵn (giao dịch thông thường)\n        - odd_lot: Lô lẻ (giao dịch lô lẻ)\n        - put_through: Thỏa thuận (giao dịch thỏa thuận)\n\n        Args:\n            symbols_list (List[str]): Danh sách mã chứng khoán (VD: ['ACB', 'VNM', 'HPG']).\n            board (str): Loại bảng giá ('stock', 'odd_lot', 'put_through'). Mặc định 'stock'.\n            exchange (str): Sàn giao dịch ('HOSE', 'HNX', 'UPCOM'). Mặc định 'HOSE'.\n            show_log (bool): Hiển thị log debug.\n            get_all (bool): Nếu True, trả về tất cả các cột. Nếu False (mặc định), chỉ trả về các cột tiêu chuẩn.\n            get_unified (bool): Nếu True, transform VCI's prefixed columns sang unified schema (khớp với KBS).\n                               Nếu False (mặc định), trả về VCI's native format (backward compatible).\n\n        Returns:\n            pd.DataFrame: DataFrame chứa thông tin giá realtime.\n            - get_unified=False (default): VCI's native format với prefixed columns (listing_*, match_*, bid_ask_*)\n            - get_unified=True: Unified schema khớp với KBS (symbol, time, exchange, close_price, ...)\n\n        Examples:\n            >>> trading = Trading('ACB')\n            >>> df = trading.price_board(['ACB', 'VNM', 'HPG'])  # VCI native format\n            >>> df = trading.price_board(['ACB', 'VNM', 'HPG'], get_unified=True)  # Unified with KBS\n            >>> df = trading.price_board(['AAA', 'AAM'], board='odd_lot')  # Odd-lot board\n            >>> df = trading.price_board(['SCR'], board='put_through')  # Put-through board\n\n        Raises:\n            ValueError: Nếu symbols_list trống hoặc board không hợp lệ.\n        ";J=get_all;H=get_unified;G=exchange;E=show_log;D=board;C=self;B=symbols_list
		if not B:raise ValueError(bytes([115,121,109,98,111,108,115,95,108,105,115,116,32,107,104,195,180,110,103,32,196,145,198,176,225,187,163,99,32,196,145,225,187,131,32,116,114,225,187,145,110,103,46]).decode())
		K=[bytes([115,116,111,99,107]).decode(),bytes([111,100,100,95,108,111,116]).decode(),bytes([112,117,116,95,116,104,114,111,117,103,104]).decode()]
		if D not in K:raise ValueError(f"board không hợp lệ. Các giá trị hợp lệ: {K}")
		B=[A.upper()for A in B]
		if D==bytes([115,116,111,99,107]).decode():A=C._fetch_stock_board(B,show_log=E,flatten_columns=False);I=bytes([108,195,180,32,99,104,225,186,181,110]).decode();F=_STOCK_BOARD_STANDARD_COLUMNS
		elif D==bytes([111,100,100,95,108,111,116]).decode():A=C.odd_lot(symbols_list=B,exchange=G,show_log=E);I=bytes([108,195,180,32,108,225,186,187]).decode();F=_ODD_LOT_STANDARD_COLUMNS
		else:
			A=C.put_through(exchange=G,show_log=E)
			if len(A)>0 and B:A=A[A[bytes([115,121,109,98,111,108]).decode()].isin(B)].reset_index(drop=True)
			I=bytes([116,104,225,187,143,97,32,116,104,117,225,186,173,110]).decode();F=_PUT_THROUGH_STANDARD_COLUMNS
		if len(A)>0:
			if H and D==bytes([115,116,111,99,107]).decode():
				from vnstock_data.explorer.vci.const import _VCI_TO_SCHEMA_MAP as L
				if isinstance(A.columns,pd.MultiIndex):A.columns=A.columns.map(lambda x:f"{x[0]}_{x[1]}"if isinstance(x,tuple)else x)
				A=A.rename(columns=L);A=C._normalize_unified_data(A);F=_PRICE_BOARD_STANDARD_COLUMNS
				if not J:M=[B for B in F if B in A.columns];A=A[M]
			else:0
			if bytes([101,120,99,104,97,110,103,101]).decode()in A.columns:A[bytes([101,120,99,104,97,110,103,101]).decode()]=A[bytes([101,120,99,104,97,110,103,101]).decode()].map(lambda x:bytes([72,79,83,69]).decode()if x==bytes([72,83,88]).decode()else x if pd.notna(x)else x)
			elif(bytes([108,105,115,116,105,110,103]).decode(),bytes([101,120,99,104,97,110,103,101]).decode())in A.columns:A[bytes([108,105,115,116,105,110,103]).decode(),bytes([101,120,99,104,97,110,103,101]).decode()]=A[bytes([108,105,115,116,105,110,103]).decode(),bytes([101,120,99,104,97,110,103,101]).decode()].map(lambda x:bytes([72,79,83,69]).decode()if x==bytes([72,83,88]).decode()else x if pd.notna(x)else x)
		A.attrs[bytes([115,121,109,98,111,108,115]).decode()]=B;A.attrs[bytes([98,111,97,114,100]).decode()]=D;A.attrs[bytes([101,120,99,104,97,110,103,101]).decode()]=G;A.attrs[bytes([115,111,117,114,99,101]).decode()]=bytes([86,67,73]).decode();A.attrs[bytes([103,101,116,95,97,108,108]).decode()]=J;A.attrs[bytes([103,101,116,95,117,110,105,102,105,101,100]).decode()]=H
		if E or C.show_log:N=bytes([117,110,105,102,105,101,100]).decode()if H else bytes([110,97,116,105,118,101]).decode();logger.info(f"Truy xuất thành công bảng giá {I} ({N}) cho {len(B)} mã chứng khoán.")
		return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def summary(self,resolution=bytes([49,68]).decode(),start=None,end=None,limit=100):
		"\n        Truy xuất thống kê giao dịch của mã chứng khoán được chọn.\n        \n        Args:\n            resolution (str): Time resolution for data (default: '1D')\n            start (str, optional): Start date in YYYY-mm-dd format\n            end (str, optional): End date in YYYY-mm-dd format\n            limit (int): Maximum number of records to return (default: 100)\n            \n        Returns:\n            pd.DataFrame: Trading summary data as DataFrame with snake_case columns\n        ";B=self;C,D=B._process_dates(start,end);E={bytes([116,105,109,101,70,114,97,109,101]).decode():_REPORT_RESOLUTION.get(resolution,bytes([79,78,69,95,68,65,89]).decode()),bytes([112,97,103,101]).decode():0,bytes([115,105,122,101]).decode():limit}
		if C and D:E.update({bytes([102,114,111,109,68,97,116,101]).decode():C,bytes([116,111,68,97,116,101]).decode():D})
		F=B._fetch_data(bytes([112,114,105,99,101,45,104,105,115,116,111,114,121,45,115,117,109,109,97,114,121]).decode(),E);A=B._to_dataframe(F,[bytes([100,97,116,97]).decode()])
		if not A.empty and any(bytes([102,111,114,101,105,103,110]).decode()in A for A in A.columns):A.columns=A.columns.str.replace(bytes([102,111,114,101,105,103,110]).decode(),bytes([102,114]).decode(),regex=False)
		return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def price_history(self,resolution=bytes([49,68]).decode(),start=None,end=None,get_all=False,limit=100):
		"\n        Retrieve price history data for the selected stock.\n        \n        Args:\n            resolution (str): Time resolution for data (default: '1D')\n            start (str, optional): Start date in YYYY-mm-dd format\n            end (str, optional): End date in YYYY-mm-dd format\n            get_all (bool, optional): Whether to get all records, including data for foreign trades, or not (default: False)\n            limit (int): Maximum number of records to return (default: 100)\n            \n        Returns:\n            pd.DataFrame: Price history data as DataFrame with snake_case columns\n        ";B=self;C,D=B._process_dates(start,end);E={bytes([116,105,109,101,70,114,97,109,101]).decode():_REPORT_RESOLUTION.get(resolution,bytes([79,78,69,95,68,65,89]).decode()),bytes([112,97,103,101]).decode():0,bytes([115,105,122,101]).decode():limit}
		if C and D:E.update({bytes([102,114,111,109,68,97,116,101]).decode():C,bytes([116,111,68,97,116,101]).decode():D})
		F=B._fetch_data(bytes([112,114,105,99,101,45,104,105,115,116,111,114,121]).decode(),E);A=B._to_dataframe(F,[bytes([100,97,116,97]).decode(),bytes([99,111,110,116,101,110,116]).decode()]);A.columns=A.columns.str.replace(bytes([102,111,114,101,105,103,110]).decode(),bytes([102,114]).decode(),regex=False);G=[bytes([105,100]).decode(),bytes([116,105,99,107,101,114]).decode(),bytes([115,116,111,99,107,95,116,121,112,101]).decode(),bytes([116,105,109,101,95,102,114,97,109,101]).decode(),bytes([105,110,100,101,120]).decode()];H={bytes([111,112,101,110,95,112,114,105,99,101]).decode():bytes([111,112,101,110]).decode(),bytes([99,108,111,115,101,95,112,114,105,99,101]).decode():bytes([99,108,111,115,101]).decode(),bytes([104,105,103,104,101,115,116,95,112,114,105,99,101]).decode():bytes([104,105,103,104]).decode(),bytes([108,111,119,101,115,116,95,112,114,105,99,101]).decode():bytes([108,111,119]).decode(),bytes([116,111,116,97,108,95,109,97,116,99,104,95,118,111,108,117,109,101]).decode():bytes([109,97,116,99,104,101,100,95,118,111,108,117,109,101]).decode(),bytes([116,111,116,97,108,95,109,97,116,99,104,95,118,97,108,117,101]).decode():bytes([109,97,116,99,104,101,100,95,118,97,108,117,101]).decode(),bytes([116,111,116,97,108,95,100,101,97,108,95,118,111,108,117,109,101]).decode():bytes([100,101,97,108,95,118,111,108,117,109,101]).decode(),bytes([116,111,116,97,108,95,100,101,97,108,95,118,97,108,117,101]).decode():bytes([100,101,97,108,95,118,97,108,117,101]).decode()};A=A.drop(columns=[B for B in G if B in A.columns])
		if bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode()in A.columns:A[bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode()]=pd.to_datetime(A[bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode()])
		if get_all is False:A=A.drop(columns=[A for A in A.columns if bytes([102,114,95]).decode()in A])
		A=A.rename(columns={B:C for(B,C)in H.items()if B in A.columns});return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def foreign_trade(self,resolution=bytes([49,68]).decode(),start=None,end=None,limit=100):A=self.price_history(resolution=resolution,start=start,end=end,get_all=True,limit=limit);A=A[[bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode()]+[A for A in A.columns if A.startswith(bytes([102,114,95]).decode())]];return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def prop_trade(self,resolution=bytes([49,68]).decode(),start=None,end=None,limit=100):
		"\n        Retrieve proprietary trading history for the selected stock.\n        \n        Args:\n            resolution (str): Time resolution for data (default: '1D')\n            start (str, optional): Start date in YYYY-mm-dd format\n            end (str, optional): End date in YYYY-mm-dd format\n            limit (int): Maximum number of records to return (default: 100)\n            \n        Returns:\n            pd.DataFrame: Proprietary trading data as DataFrame with snake_case columns\n        ";B=self;C,D=B._process_dates(start,end);E={bytes([116,105,109,101,70,114,97,109,101]).decode():_REPORT_RESOLUTION.get(resolution,bytes([79,78,69,95,68,65,89]).decode()),bytes([112,97,103,101]).decode():0,bytes([115,105,122,101]).decode():limit}
		if C and D:E.update({bytes([102,114,111,109,68,97,116,101]).decode():C,bytes([116,111,68,97,116,101]).decode():D})
		F=B._fetch_data(bytes([112,114,111,112,114,105,101,116,97,114,121,45,104,105,115,116,111,114,121]).decode(),E);A=B._to_dataframe(F,[bytes([100,97,116,97]).decode(),bytes([99,111,110,116,101,110,116]).decode()]);A.columns=A.columns.str.replace(bytes([112,114,111,112,114,105,101,116,97,114,121]).decode(),bytes([112,114,111,112]).decode(),regex=False);G=[bytes([105,100]).decode(),bytes([116,105,99,107,101,114]).decode(),bytes([111,114,103,97,110,95,99,111,100,101]).decode(),bytes([116,105,109,101,95,102,114,97,109,101]).decode()];A=A.drop(columns=[B for B in G if B in A.columns])
		if bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode()in A.columns:
			try:A[bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode()]=pd.to_datetime(A[bytes([116,114,97,100,105,110,103,95,100,97,116,101]).decode()])
			except Exception as H:logger.warning(f"Failed to convert trading_date to datetime: {H}")
		A=A.dropna(how=bytes([97,108,108]).decode());A=A.reset_index(drop=True);return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def insider_deal(self,limit=100,lang=bytes([118,105]).decode()):
		'\n        Retrieve insider transaction data for the selected stock.\n        \n        Args:\n            limit (int): Maximum number of records to return (default: 100)\n            \n        Returns:\n            pd.DataFrame: Insider transaction data as DataFrame with snake_case columns\n        ';C={bytes([112,97,103,101]).decode():0,bytes([115,105,122,101]).decode():limit};D=self._fetch_data(bytes([105,110,115,105,100,101,114,45,116,114,97,110,115,97,99,116,105,111,110]).decode(),C);A=self._to_dataframe(D,[bytes([100,97,116,97]).decode(),bytes([99,111,110,116,101,110,116]).decode()]);A=filter_columns_by_language(A,lang=lang);E=[bytes([105,100]).decode(),bytes([116,105,99,107,101,114]).decode(),bytes([111,114,103,97,110,95,99,111,100,101]).decode(),bytes([100,105,115,112,108,97,121,95,100,97,116,101,49]).decode(),bytes([100,105,115,112,108,97,121,95,100,97,116,101,50]).decode(),bytes([101,118,101,110,116,95,99,111,100,101]).decode(),bytes([97,99,116,105,111,110,95,116,121,112,101,95,99,111,100,101]).decode(),bytes([105,99,98,95,99,111,100,101,95,108,118,49]).decode()];A=A.drop(columns=[B for B in E if B in A.columns]);F=[bytes([115,116,97,114,116,95,100,97,116,101]).decode(),bytes([101,110,100,95,100,97,116,101]).decode(),bytes([112,117,98,108,105,99,95,100,97,116,101]).decode()]
		for B in F:
			if B in A.columns:
				try:A[B]=pd.to_datetime(A[B],errors=bytes([99,111,101,114,99,101]).decode())
				except Exception as G:logger.warning(f"Failed to convert {B} to datetime: {G}")
		A=A.dropna(how=bytes([97,108,108]).decode());A=A.reset_index(drop=True);return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def odd_lot(self,symbols_list=None,exchange=bytes([72,79,83,69]).decode(),show_log=False):
		"\n        Truy xuất dữ liệu giao dịch lô lẻ (odd-lot) cho danh sách mã chứng khoán.\n\n        Args:\n            symbols_list (List[str], optional): Danh sách mã chứng khoán. Nếu None, truy xuất toàn bộ sàn.\n            exchange (str): Sàn giao dịch ('HOSE', 'HNX', 'UPCOM'). Mặc định 'HOSE'.\n            show_log (bool): Hiển thị log debug.\n\n        Returns:\n            pd.DataFrame: Dữ liệu giao dịch lô lẻ với các cột chuẩn hóa.\n\n        Examples:\n            >>> trading = Trading('ACB')\n            >>> df = trading.odd_lot(symbols_list=['ACB', 'VNM'])\n            >>> df = trading.odd_lot(exchange='HOSE')\n\n        Raises:\n            ValueError: Nếu exchange không hợp lệ.\n        ";F=show_log;E=exchange;D=self;C=symbols_list;K=[bytes([72,79,83,69]).decode(),bytes([72,78,88]).decode(),bytes([85,80,67,79,77]).decode()]
		if E not in K:raise ValueError(f"Exchange không hợp lệ. Các giá trị hợp lệ: {K}")
		L=_ODD_LOT_URL
		if C:C=[A.upper()for A in C];G={bytes([115,121,109,98,111,108,115]).decode():C}
		else:G={bytes([101,120,99,104,97,110,103,101]).decode():E}
		if F or D.show_log:logger.info(f"Requested URL: {L} with payload: {G}")
		try:H=send_request(L,headers=D.headers,method=bytes([80,79,83,84]).decode(),payload=json.loads(json.dumps(G)),show_log=F or D.show_log,proxy_list=D.proxy_config.proxy_list,proxy_mode=D.proxy_config.proxy_mode,request_mode=D.proxy_config.request_mode)
		except Exception as I:logger.error(f"Failed to fetch odd_lot data: {I!s}");return pd.DataFrame()
		if not H or not isinstance(H,list):return pd.DataFrame()
		J=[]
		for M in H:
			try:
				B=M.get(bytes([109,97,116,99,104,80,114,105,99,101]).decode(),{})
				if not B:continue
				N={bytes([115,121,109,98,111,108]).decode():M.get(bytes([108,105,115,116,105,110,103,73,110,102,111]).decode(),{}).get(bytes([115,121,109,98,111,108]).decode()),bytes([112,114,105,99,101]).decode():B.get(bytes([109,97,116,99,104,80,114,105,99,101]).decode()),bytes([118,111,108,117,109,101]).decode():B.get(bytes([109,97,116,99,104,86,111,108]).decode()),bytes([104,105,103,104,101,115,116]).decode():B.get(bytes([104,105,103,104,101,115,116]).decode()),bytes([108,111,119,101,115,116]).decode():B.get(bytes([108,111,119,101,115,116]).decode()),bytes([111,112,101,110]).decode():B.get(bytes([111,112,101,110,80,114,105,99,101]).decode()),bytes([97,118,103,95,112,114,105,99,101]).decode():B.get(bytes([97,118,103,77,97,116,99,104,80,114,105,99,101]).decode()),bytes([97,99,99,117,109,117,108,97,116,101,100,95,118,111,108,117,109,101]).decode():B.get(bytes([97,99,99,117,109,117,108,97,116,101,100,86,111,108,117,109,101]).decode()),bytes([97,99,99,117,109,117,108,97,116,101,100,95,118,97,108,117,101]).decode():B.get(bytes([97,99,99,117,109,117,108,97,116,101,100,86,97,108,117,101]).decode()),bytes([115,101,115,115,105,111,110]).decode():B.get(bytes([115,101,115,115,105,111,110]).decode()),bytes([116,105,109,101]).decode():B.get(bytes([116,105,109,101]).decode())};J.append(N)
			except Exception as I:logger.warning(f"Error processing odd_lot item: {I}");continue
		if not J:logger.warning(f"No valid odd_lot data found for exchange {E}");return pd.DataFrame()
		A=pd.DataFrame(J);O=[B for B in _ODD_LOT_STANDARD_COLUMNS if B in A.columns];A=A[O]
		if bytes([116,105,109,101]).decode()in A.columns:A[bytes([116,105,109,101]).decode()]=pd.to_datetime(A[bytes([116,105,109,101]).decode()],errors=bytes([99,111,101,114,99,101]).decode())
		if C:A.attrs[bytes([115,121,109,98,111,108,115]).decode()]=C
		A.attrs[bytes([101,120,99,104,97,110,103,101]).decode()]=E;A.attrs[bytes([115,111,117,114,99,101]).decode()]=bytes([86,67,73]).decode()
		if F or D.show_log:
			if C:logger.info(f"Truy xuất thành công {len(A)} bản ghi giao dịch lô lẻ cho {len(C)} mã chứng khoán.")
			else:logger.info(f"Truy xuất thành công {len(A)} bản ghi giao dịch lô lẻ cho sàn {E}.")
		return A
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def put_through(self,exchange=bytes([72,79,83,69]).decode(),show_log=False):
		"\n        Truy xuất dữ liệu giao dịch thỏa thuận (put-through) theo sàn.\n\n        Args:\n            exchange (str): Sàn giao dịch ('HOSE', 'HNX', 'UPCOM'). Mặc định 'HOSE'.\n            show_log (bool): Hiển thị log debug.\n\n        Returns:\n            pd.DataFrame: Dữ liệu giao dịch thỏa thuận với các cột chuẩn hóa.\n\n        Examples:\n            >>> trading = Trading('ACB')\n            >>> df = trading.put_through(exchange='HOSE')\n\n        Raises:\n            ValueError: Nếu exchange không hợp lệ.\n        ";E=show_log;D=exchange;B=self;I=[bytes([72,79,83,69]).decode(),bytes([72,78,88]).decode(),bytes([85,80,67,79,77]).decode()]
		if D not in I:raise ValueError(f"Exchange không hợp lệ. Các giá trị hợp lệ: {I}")
		J=_PUT_THROUGH_URL;K={bytes([103,114,111,117,112]).decode():D}
		if E or B.show_log:logger.info(f"Requested URL: {J} with params: {K}")
		try:F=send_request(J,headers=B.headers,method=bytes([71,69,84]).decode(),params=K,show_log=E or B.show_log,proxy_list=B.proxy_config.proxy_list,proxy_mode=B.proxy_config.proxy_mode,request_mode=B.proxy_config.request_mode)
		except Exception as G:logger.error(f"Failed to fetch put_through data: {G!s}");return pd.DataFrame()
		if not F or not isinstance(F,list):return pd.DataFrame()
		H=[]
		for A in F:
			try:L={bytes([115,121,109,98,111,108]).decode():A.get(bytes([115,121,109,98,111,108]).decode()),bytes([112,114,105,99,101]).decode():A.get(bytes([112,116,77,97,116,99,104,80,114,105,99,101]).decode()),bytes([118,111,108,117,109,101]).decode():A.get(bytes([112,116,77,97,116,99,104,86,111,108,117,109,101]).decode()),bytes([99,104,97,110,103,101]).decode():A.get(bytes([112,116,67,104,97,110,103,101]).decode()),bytes([99,104,97,110,103,101,95,112,101,114,99,101,110,116]).decode():A.get(bytes([112,116,67,104,97,110,103,101,80,101,114,99,101,110,116]).decode()),bytes([109,97,116,99,104,95,118,97,108,117,101]).decode():A.get(bytes([112,116,77,97,116,99,104,86,97,108,117,101]).decode()),bytes([97,99,99,117,109,117,108,97,116,101,100,95,118,111,108,117,109,101]).decode():A.get(bytes([112,116,65,99,99,117,109,117,108,97,116,101,100,86,111,108,117,109,101]).decode()),bytes([97,99,99,117,109,117,108,97,116,101,100,95,118,97,108,117,101]).decode():A.get(bytes([112,116,65,99,99,117,109,117,108,97,116,101,100,86,97,108,117,101]).decode()),bytes([116,105,109,101]).decode():A.get(bytes([116,105,109,101]).decode())};H.append(L)
			except Exception as G:logger.warning(f"Error processing put_through item: {G}");continue
		if not H:logger.warning(f"No valid put_through data found for exchange {D}");return pd.DataFrame()
		C=pd.DataFrame(H)
		if bytes([116,105,109,101]).decode()in C.columns:C[bytes([116,105,109,101]).decode()]=pd.to_datetime(C[bytes([116,105,109,101]).decode()],errors=bytes([99,111,101,114,99,101]).decode())
		C.attrs[bytes([101,120,99,104,97,110,103,101]).decode()]=D;C.attrs[bytes([115,111,117,114,99,101]).decode()]=bytes([86,67,73]).decode()
		if E or B.show_log:logger.info(f"Truy xuất thành công {len(C)} bản ghi giao dịch thỏa thuận cho sàn {D}.")
		return C
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([116,114,97,100,105,110,103]).decode(),bytes([118,99,105]).decode(),Trading)