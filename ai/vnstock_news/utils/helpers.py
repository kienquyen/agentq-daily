import requests,pandas as pd
from functools import wraps
from typing import Dict,Any,Callable
from vnstock_news.utils.logger import setup_logger
from vnstock_news.config.sites import SITES_CONFIG
from urllib.parse import urlparse
logger=setup_logger('vnstock_news.utils.helpers')
def retry_request(max_retries=3):
	'\n    Decorator to retry a function multiple times in case of failure.\n    \n    Parameters:\n        max_retries (int): Maximum number of retry attempts.\n        \n    Returns:\n        Callable: Decorated function with retry logic.\n    ';A=max_retries
	def B(func):
		@wraps(func)
		def B(*C,**D):
			for B in range(A):
				try:return func(*C,**D)
				except Exception as E:
					logger.warning(f"Attempt {B+1} failed: {E}")
					if B==A-1:raise
			raise Exception('Max retries reached.')
		return B
	return B
@retry_request()
def fetch_url_content(url,headers=None,timeout=10):'\n    Fetch URL content with retry logic.\n\n    Parameters:\n        url (str): Target URL.\n        headers (dict): Request headers.\n        timeout (int): Timeout in seconds.\n\n    Returns:\n        bytes: Response content.\n    ';A=requests.get(url,headers=headers,timeout=timeout);A.raise_for_status();logger.info(f"Successfully fetched content from {url}");return A.content
def standardize_columns(df,mapping):'\n    Standardize DataFrame columns based on a mapping.\n\n    Parameters:\n        df (pd.DataFrame): Input DataFrame.\n        mapping (dict): Mapping of column names.\n\n    Returns:\n        pd.DataFrame: DataFrame with standardized column names.\n    ';A={A:B for(B,C)in mapping.items()for A in C if A in df.columns};return df.rename(columns=A)
def list_supported_sites(display=True):
	"\n    Lists all supported sites with their short names and domains.\n\n    Parameters:\n        display (bool): Whether to print the list to the console.\n\n    Returns:\n        list: A list of dictionaries, each containing the 'name' and 'domain' of a site.\n    ";E='domain';D='name';A=[]
	def F(config):
		"\n        Extracts the domain from a site's configuration.\n        ";G='base_url';F='current_url';E='urls';D='rss';C='sitemap_url';B='sitemap';A=config
		if A.get(C):return urlparse(A[C]).netloc
		if A.get(D,{}).get(E):return urlparse(A[D][E][0]).netloc
		if A.get(B,{}).get(F):return urlparse(A[B][F]).netloc
		if A.get(B,{}).get(G):return urlparse(A[B][G]).netloc
		return'Không xác định'
	for(B,G)in SITES_CONFIG.items():H=F(G);A.append({D:B,E:H})
	if display:
		print('DANH SÁCH CÁC TRANG WEB ĐƯỢC HỖ TRỢ:');print('='*50);I='Tên viết tắt';J='Tên miền';print(f"{I:<15} | {J}");print('-'*50)
		for C in A:B=C[D];K=C[E];print(f"{B:<15} | {K}")
		print('='*50)
	return A