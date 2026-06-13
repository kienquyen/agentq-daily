import re,unicodedata,urllib.parse
from datetime import date,datetime,timedelta
import pandas as pd
from dateutil.relativedelta import relativedelta
def get_asset_type(symbol):
	"\n    Xác định loại tài sản dựa trên mã chứng khoán được cung cấp.\n\n    Tham số: \n        - symbol (str): Mã chứng khoán hoặc mã chỉ số.\n    \n    Trả về:\n        - 'index' nếu mã chứng khoán là mã chỉ số.\n        - 'stock' nếu mã chứng khoán là mã cổ phiếu.\n        - 'derivative' nếu mã chứng khoán là mã hợp đồng tương lai hoặc quyền chọn.\n        - 'bond' nếu mã chứng khoán là mã trái phiếu (chính phủ hoặc doanh nghiệp).\n        - 'coveredWarr' nếu mã chứng khoán là mã chứng quyền.\n    ";symbol=symbol.upper()
	if symbol in[bytes([86,78,73,78,68,69,88]).decode(),bytes([72,78,88,73,78,68,69,88]).decode(),bytes([85,80,67,79,77,73,78,68,69,88]).decode(),bytes([86,78,51,48]).decode(),bytes([86,78,49,48,48]).decode(),bytes([72,78,88,51,48]).decode(),bytes([86,78,83,77,76]).decode(),bytes([86,78,77,73,68]).decode(),bytes([86,78,65,76,76]).decode(),bytes([86,78,82,69,65,76]).decode(),bytes([86,78,77,65,84]).decode(),bytes([86,78,73,84]).decode(),bytes([86,78,72,69,65,76]).decode(),bytes([86,78,70,73,78,83,69,76,69,67,84]).decode(),bytes([86,78,70,73,78]).decode(),bytes([86,78,69,78,69]).decode(),bytes([86,78,68,73,65,77,79,78,68]).decode(),bytes([86,78,67,79,78,83]).decode(),bytes([86,78,67,79,78,68]).decode()]:return bytes([105,110,100,101,120]).decode()
	elif len(symbol)==3:return bytes([115,116,111,99,107]).decode()
	elif len(symbol)in[7,9]:
		fm_pattern=re.compile(bytes([94,86,78,51,48,70,92,100,123,49,44,50,125,77,36]).decode());ym_pattern=re.compile(bytes([94,86,78,51,48,70,92,100,123,52,125,36]).decode());gov_bond_pattern=re.compile(bytes([94,71,66,92,100,123,50,125,70,92,100,123,52,125,36]).decode());comp_bond_pattern=re.compile(bytes([94,40,63,33,86,78,51,48,70,41,91,65,45,90,93,123,51,125,92,100,123,54,125,36]).decode())
		if gov_bond_pattern.match(symbol)or comp_bond_pattern.match(symbol):return bytes([98,111,110,100]).decode()
		elif fm_pattern.match(symbol)or ym_pattern.match(symbol):return bytes([100,101,114,105,118,97,116,105,118,101]).decode()
		else:raise ValueError(bytes([73,110,118,97,108,105,100,32,100,101,114,105,118,97,116,105,118,101,32,111,114,32,98,111,110,100,32,115,121,109,98,111,108,46,32,83,121,109,98,111,108,32,109,117,115,116,32,98,101,32,105,110,32,102,111,114,109,97,116,32,111,102,32,86,78,51,48,70,49,77,44,32,86,78,51,48,70,50,48,50,52,44,32,71,66,49,48,70,50,48,50,52,44,32,111,114,32,102,111,114,32,99,111,109,112,97,110,121,32,98,111,110,100,115,44,32,101,46,103,46,44,32,66,65,66,49,50,50,48,51,50]).decode())
	elif len(symbol)==8:return bytes([99,111,118,101,114,101,100,87,97,114,114]).decode()
	else:raise ValueError(bytes([73,110,118,97,108,105,100,32,115,121,109,98,111,108,46,32,89,111,117,114,32,115,121,109,98,111,108,32,102,111,114,109,97,116,32,105,115,32,110,111,116,32,114,101,99,111,103,110,105,122,101,100,33]).decode())
def encode_url(string,safe=''):'\n    Encode a string to url format.\n    ';return urllib.parse.quote(string,safe=safe)
def days_between(start,end,format=bytes([37,109,47,37,100,47,37,89]).decode()):"\n    Calculate the number of days between two given datestrings.\n\n    Parameters:\n        start (str): The start date string.\n        end (str): The end date string.\n        format (str): The format of the date strings. Default is '%m/%d/%Y'.\n        \n    Returns:\n        int: The number of days between the two dates.\n    ";start=pd.to_datetime(start,format=format);end=pd.to_datetime(end,format=format);days=(end-start).days;return days
def lookback_date(period):
	"\n    Calculates the start date based on a lookback period.\n\n    Parameters:\n        period (str): Lookback period (e.g., '1D', '5M', '10Y').\n                      D = days, M = months, Y = years.\n\n    Returns:\n        str: Calculated start date in YYYY-MM-DD format.\n\n    Raises:\n        ValueError: If the period format is invalid.\n    "
	try:
		unit=period[-1].upper();value=int(period[:-1])
		if unit==bytes([68]).decode():start_date=datetime.now()-timedelta(days=value)
		elif unit==bytes([77]).decode():start_date=datetime.now()-timedelta(days=value*30)
		elif unit==bytes([89]).decode():start_date=datetime.now()-timedelta(days=value*365)
		else:raise ValueError(bytes([73,110,118,97,108,105,100,32,112,101,114,105,111,100,32,102,111,114,109,97,116,46,32,85,115,101,32,39,68,39,44,32,39,77,39,44,32,111,114,32,39,89,39,32,102,111,114,32,100,97,121,115,44,32,109,111,110,116,104,115,44,32,111,114,32,121,101,97,114,115,46]).decode())
		return start_date.strftime(bytes([37,89,45,37,109,45,37,100]).decode())
	except Exception as e:raise ValueError(f"Error parsing period: {e}")
def filter_columns_by_language(df,lang):
	'\n    Filter DataFrame columns based on language preference.\n    \n    Args:\n        df (pd.DataFrame): Input DataFrame with multilingual columns\n        lang (str): Language preference ("vi", "en", or "both")\n        \n    Returns:\n        pd.DataFrame: DataFrame with filtered columns based on language preference\n    '
	if lang.lower()==bytes([98,111,116,104]).decode():return df
	all_columns=df.columns.tolist();vi_columns=[col for col in all_columns if col.endswith(bytes([95,118,105]).decode())];en_columns=[col for col in all_columns if col.endswith(bytes([95,101,110]).decode())];base_columns=[col for col in all_columns if not(col.endswith(bytes([95,118,105]).decode())or col.endswith(bytes([95,101,110]).decode()))]
	if lang.lower()==bytes([118,105]).decode():columns_to_keep=base_columns+vi_columns;filtered_df=df[columns_to_keep].copy();rename_dict={col:col.replace(bytes([95,118,105]).decode(),'')for col in vi_columns};filtered_df=filtered_df.rename(columns=rename_dict)
	elif lang.lower()==bytes([101,110]).decode():columns_to_keep=base_columns+en_columns;filtered_df=df[columns_to_keep].copy();rename_dict={col:col.replace(bytes([95,101,110]).decode(),'')for col in en_columns};filtered_df=filtered_df.rename(columns=rename_dict)
	else:logger.warning(f"Invalid language parameter '{lang}'. Use 'vi', 'en', or 'both'. Returning all columns.");return df
	return filtered_df
def vn_to_snake_case(text):
	'\n    Convert Vietnamese text with diacritics to unaccented, lowercase, snake_case string.\n    ';text=unicodedata.normalize(bytes([78,70,68]).decode(),text);text=''.join([c for c in text if unicodedata.category(c)!=bytes([77,110]).decode()]);VN_CHAR_MAP={bytes([196,145]).decode():bytes([100]).decode(),bytes([196,144]).decode():bytes([100]).decode(),bytes([195,180]).decode():bytes([111]).decode(),bytes([195,148]).decode():bytes([111]).decode(),bytes([198,176]).decode():bytes([117]).decode(),bytes([198,175]).decode():bytes([117]).decode(),bytes([195,170]).decode():bytes([101]).decode(),bytes([195,138]).decode():bytes([101]).decode(),bytes([196,131]).decode():bytes([97]).decode(),bytes([196,130]).decode():bytes([97]).decode(),bytes([195,162]).decode():bytes([97]).decode(),bytes([195,130]).decode():bytes([97]).decode()}
	for(src,tgt)in VN_CHAR_MAP.items():text=text.replace(src,tgt)
	text=text.lower();text=re.sub(bytes([91,94,97,45,122,48,45,57,93,43]).decode(),bytes([95]).decode(),text);text=text.strip(bytes([95]).decode());text=re.sub(bytes([95,43]).decode(),bytes([95]).decode(),text);return text
def get_derivative_maturity_date(symbol_suffix,reference_date=None):
	"\n    Calculate the maturity date for a derivative symbol suffix.\n    \n    Args:\n        symbol_suffix: Suffix like 'F2506' (explicit) or 'F1M', 'F1Q' (relative).\n        reference_date: Reference date for relative calculation (default: today).\n        \n    Returns:\n        date: The maturity date (3rd Thursday of the month).\n    "
	if reference_date is None:reference_date=date.today()
	maturity_month=reference_date.month;maturity_year=reference_date.year
	if len(symbol_suffix)==5 and symbol_suffix.startswith(bytes([70]).decode())and symbol_suffix[1:].isdigit():yy=int(symbol_suffix[1:3]);mm=int(symbol_suffix[3:5]);maturity_year=2000+yy;maturity_month=mm
	elif symbol_suffix.startswith(bytes([70]).decode())and len(symbol_suffix)==3:
		def get_expiry(y,m):d=date(y,m,1);days_to_thursday=(3-d.weekday()+7)%7;return d+timedelta(days=days_to_thursday+14)
		current_expiry=get_expiry(reference_date.year,reference_date.month);base_date=reference_date
		if reference_date>current_expiry:base_date=reference_date+relativedelta(months=1)
		if symbol_suffix==bytes([70,49,77]).decode():target_date=base_date
		elif symbol_suffix==bytes([70,50,77]).decode():target_date=base_date+relativedelta(months=1)
		elif symbol_suffix==bytes([70,49,81]).decode():
			current_month=base_date.month;quarter_months=[3,6,9,12];target_month=next((m for m in quarter_months if m>=current_month),None)
			if target_month is None:target_date=date(base_date.year+1,3,1)
			else:target_date=date(base_date.year,target_month,1)
		elif symbol_suffix==bytes([70,50,81]).decode():
			current_month=base_date.month;quarter_months=[3,6,9,12];target_month=next((m for m in quarter_months if m>=current_month),None)
			if target_month is None:target_date=date(base_date.year+1,6,1)
			else:
				idx=quarter_months.index(target_month)
				if idx+1<len(quarter_months):target_date=date(base_date.year,quarter_months[idx+1],1)
				else:target_date=date(base_date.year+1,3,1)
		else:return reference_date
		if bytes([116,97,114,103,101,116,95,100,97,116,101]).decode()in locals():maturity_year=target_date.year;maturity_month=target_date.month
	d=date(maturity_year,maturity_month,1);days_to_thursday=(3-d.weekday()+7)%7;maturity_date=d+timedelta(days=days_to_thursday+14);return maturity_date
def convert_derivative_symbol(symbol,reference_date=None):
	'\n    Convert old derivative symbol (e.g. VN30F2506, GB05F2506) to new KRX format (e.g. 41I1F7000).\n    Effective from May 2025.\n    \n    Format: 41 + Underlying + Year + Month + 000\n    Length: 9 chars.\n    Reference: https://owa.hnx.vn/ftp//PORTALNEW/HEADER_IMAGES/20250428/21.04.2025_Tai%20lieu%20huong%20dan%20quy%20uoc%20ma%20giao%20dich%20moi%20ckps_final.pdf\n    ';symbol=symbol.upper();underlying_map={bytes([86,78,51,48]).decode():bytes([73,49]).decode(),bytes([86,78,49,48,48]).decode():bytes([73,50]).decode(),bytes([71,66,48,53]).decode():bytes([66,53]).decode(),bytes([71,66,49,48]).decode():bytes([66,65]).decode()};underlying_code=None;suffix=None
	for(prefix,code)in underlying_map.items():
		if symbol.startswith(prefix):underlying_code=code;suffix=symbol[len(prefix):];break
	if not underlying_code:raise ValueError(bytes([85,110,107,110,111,119,110,32,117,110,100,101,114,108,121,105,110,103,32,97,115,115,101,116,32,102,111,114,32,115,121,109,98,111,108,32,123,125,46,32,83,117,112,112,111,114,116,101,100,32,112,114,101,102,105,120,101,115,58,32,123,125]).decode().format(symbol,bytes([44,32]).decode().join(underlying_map.keys())))
	if reference_date is None:0
	mat_date=get_derivative_maturity_date(suffix,reference_date);mat_year=mat_date.year;mat_month=mat_date.month;year_cycle_index=(mat_year-2010)%30;alphabet=bytes([65,66,67,68,69,70,71,72,74,75,76,77,78,80,81,82,83,84,86,87]).decode()
	if 0<=year_cycle_index<=9:year_code=str(year_cycle_index)
	else:year_code=alphabet[year_cycle_index-10]
	if 1<=mat_month<=9:month_code=str(mat_month)
	else:month_codes={10:bytes([65]).decode(),11:bytes([66]).decode(),12:bytes([67]).decode()};month_code=month_codes[mat_month]
	krx_symbol=f"41{underlying_code}{year_code}{month_code}000";return krx_symbol
def safe_convert_derivative_symbol(symbol,reference_date=None):
	"\n    Safely convert derivative symbol to KRX format. If it's already KRX or an error occurs,\n    returns the original symbol.\n    "
	try:
		if len(symbol)==9 and symbol.startswith(bytes([52,49]).decode()):return symbol
		return convert_derivative_symbol(symbol,reference_date)
	except Exception:return symbol