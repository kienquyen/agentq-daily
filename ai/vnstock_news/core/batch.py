_D='Fetching article details'
_C='url'
_B=False
_A=None
import os,pandas as pd
from time import sleep
from typing import List,Optional,Union,Dict,Any
from tqdm import tqdm
from vnstock_news.utils.logger import setup_logger
from vnstock_news.core.crawler import Crawler
class BatchCrawler:
	'\n    Batch fetch detailed articles from multiple sources (RSS or sitemap),\n    with optional resume via a temp file and final output path.\n    '
	def __init__(A,site_name=_A,custom_config=_A,debug=_B,request_delay=1.,temp_file='temp_articles.csv',output_path=_A):'\n        Parameters:\n            site_name (str): Predefined site to use.\n            custom_config (dict): User-defined config.\n            debug (bool): Turn debug logging on/off.\n            request_delay (float): Seconds to sleep between requests.\n            temp_file (str): Path for interim save.\n            output_path (str): Path for final CSV.\n        ';B=debug;A.logger=setup_logger(A.__class__.__name__,B);A.crawler=Crawler(site_name=site_name,custom_config=custom_config,debug=B);A.request_delay=request_delay;A.temp_file=temp_file;A.output_path=output_path
	def _load_temp(A):
		'\n        Load interim DataFrame if exists, else empty DataFrame.\n        '
		if os.path.exists(A.temp_file):
			try:return pd.read_csv(A.temp_file)
			except Exception:A.logger.warning('Could not load temp file, starting fresh')
		return pd.DataFrame()
	def _save_temp(A,df):
		'\n        Save interim DataFrame to CSV.\n        '
		try:df.to_csv(A.temp_file,index=_B)
		except Exception as B:A.logger.error(f"Failed saving temp file: {B}")
	def fetch_articles(A,sitemap_url=_A,limit=10,top_n=_A,top_n_per_feed=_A,within=_A):
		'\n        Fetch detailed articles.\n\n        Parameters:\n            sitemap_url (str or list, optional): Custom sitemap URL(s) to fetch articles from.\n            limit (int): Maximum total number of articles.\n            top_n (int, optional): Alias for limit (for backward compatibility).\n            top_n_per_feed (int, optional): Limit per feed when multiple feeds are provided.\n            within (str): Reserved for future use (time filter).\n        ';F=top_n;E=limit
		if F is not _A:E=F
		J=A._load_temp();G=[]
		try:
			H=A.crawler.get_articles(sitemap_url=sitemap_url,limit=E,limit_per_feed=top_n_per_feed)
			if not H:A.logger.warning('No articles fetched from source.');return pd.DataFrame()
		except Exception as B:A.logger.error(f"Failed fetching article metadata: {B}");return pd.DataFrame()
		for I in tqdm(H,desc=_D):
			C=I.get('link')or I.get(_C)
			if not C:A.logger.warning("Article metadata missing 'url'. Skipping.");continue
			if C in J.get(_C,[]):A.logger.info(f"Skipping already fetched article: {C}");continue
			try:K=A.crawler.get_article_details(C);G.append(K);sleep(A.request_delay)
			except Exception as B:A.logger.error(f"Failed fetching article detail {C}: {B}");continue
		D=pd.DataFrame(G)
		if A.output_path:
			try:D.to_csv(A.output_path,index=_B);A.logger.info(f"Saved output to {A.output_path}")
			except Exception as B:A.logger.error(f"Failed saving output: {B}")
		A._save_temp(D);return D
	def fetch_details_for_urls(A,urls):
		'\n        Fetches detailed articles for a given list of URLs.\n        This method is useful when you already have a list of article URLs\n        and want to fetch their full content in batch.\n\n        Parameters:\n            urls (List[str]): A list of article URLs to fetch details for.\n        ';F=A._load_temp();E=[]
		for B in tqdm(urls,desc=_D):
			if B in F.get(_C,[]):A.logger.info(f"Skipping already fetched article: {B}");continue
			try:G=A.crawler.get_article_details(B);E.append(G);sleep(A.request_delay)
			except Exception as C:A.logger.error(f"Failed fetching article detail {B}: {C}");continue
		D=pd.DataFrame(E)
		if A.output_path:
			try:D.to_csv(A.output_path,index=_B);A.logger.info(f"Saved output to {A.output_path}")
			except Exception as C:A.logger.error(f"Failed saving output: {C}")
		A._save_temp(D);return D