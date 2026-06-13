_D='desc'
_C=False
_B=True
_A=None
from typing import List,Dict,Union,Optional,Any
import pandas as pd,asyncio
from vnstock_news.async_crawlers.async_batch import AsyncBatchCrawler
from vnstock_news.utils.cache import Cache,cached
from vnstock_news.utils.validators import InputValidator,ValidationError
from vnstock_news.utils.cleaner import ContentCleaner
from vnstock_news.config.sites import SITES_CONFIG
from vnstock_news.utils.logger import setup_logger
class EnhancedNewsCrawler:
	'\n    Enhanced news crawler that integrates async processing, caching,\n    validation, and content cleaning.\n    '
	def __init__(A,cache_enabled=_B,cache_type='sqlite',cache_ttl=86400,max_concurrency=5,debug=_C):
		"\n        Initialize the enhanced news crawler.\n        \n        Parameters:\n            cache_enabled (bool): Enable result caching.\n            cache_type (str): Cache backend type ('memory', 'file', or 'sqlite').\n            cache_ttl (int): Cache time-to-live in seconds.\n            max_concurrency (int): Maximum number of concurrent requests.\n            debug (bool): Enable debug logging.\n        ";E=cache_enabled;D=cache_type;C=debug;B=cache_ttl;A.logger=setup_logger(A.__class__.__name__,C);A.debug=C;A.max_concurrency=max_concurrency;A.cache_enabled=E;A.cache_ttl=B;A.validator=InputValidator(debug=C);A.cleaner=ContentCleaner(debug=C)
		if E:
			if D=='memory':A.cache=Cache(Cache.MEMORY,ttl=B)
			elif D=='file':A.cache=Cache(Cache.FILE,cache_dir='.vnnews_cache',ttl=B)
			else:A.cache=Cache(Cache.SQLITE,db_file='vnnews_cache.db',ttl=B)
			A.logger.info(f"Cache initialized: {D} with TTL {B} seconds")
		else:A.cache=_A;A.logger.info('Caching disabled')
	async def fetch_articles_async(A,sources,max_articles=10,time_frame='1d',site_name=_A,custom_config=_A,sort_order=_D,clean_content=_B,save_to_file=_A):
		'\n        Asynchronously fetch articles with validation, caching, and cleaning.\n        \n        Parameters:\n            sources (str, list, dict): Source URLs or dict mapping site names to URL lists.\n            max_articles (int): Maximum number of articles to fetch per site.\n            time_frame (str): Time frame to filter articles by (e.g., "1d", "6h").\n            site_name (str, optional): Name of the site if using predefined configs.\n            custom_config (dict, optional): Custom configuration for parsing.\n            sort_order (str): Sort order for articles (\'asc\' or \'desc\').\n            clean_content (bool): Whether to clean the content.\n            save_to_file (str, optional): Path to save results to CSV.\n            \n        Returns:\n            pd.DataFrame: DataFrame containing articles.\n        ';D=save_to_file;C=clean_content;B=sources
		try:E=A.validator.validate_positive_int(max_articles,'max_articles');F=A.validator.validate_time_frame(time_frame);G=A.validator.validate_sort_order(sort_order)
		except ValidationError as H:A.logger.error(f"Validation error: {H}");return pd.DataFrame()
		if isinstance(B,dict):return await A._fetch_from_multiple_sites(B,E,F,G,C,D)
		else:return await A._fetch_from_single_source(B,E,F,site_name,custom_config,G,C,D)
	async def _fetch_from_single_source(A,sources,max_articles,time_frame,site_name=_A,custom_config=_A,sort_order=_D,clean_content=_B,save_to_file=_A):
		'\n        Fetch articles from a single source or site.\n        \n        Parameters identical to fetch_articles_async but for a single source.\n            \n        Returns:\n            pd.DataFrame: DataFrame containing articles.\n        ';Q='custom source';M=clean_content;L=sort_order;K=site_name;J=time_frame;I=max_articles;H=sources;E=save_to_file
		if K:
			try:B=A.validator.validate_site_name(K,list(SITES_CONFIG.keys()),required=_B)
			except ValidationError as C:A.logger.error(f"Invalid site name: {C}");return pd.DataFrame()
		else:B=_A
		try:
			if isinstance(H,(str,list)):N=A.validator.validate_urls(H)
			else:A.logger.error('Sources must be a URL string or list of URLs');return pd.DataFrame()
		except ValidationError as C:A.logger.error(f"Invalid sources: {C}");return pd.DataFrame()
		if A.cache_enabled:
			O={'site':B,'sources':tuple(N),'max':I,'time_frame':J,'sort':L,'clean':M};P=A.cache.get(O)
			if P is not _A:F=B or Q;A.logger.info(f"Using cached results for {F}");return P
		R=B or'custom';S=AsyncBatchCrawler(site_name=B,custom_config=custom_config,debug=A.debug,max_concurrency=A.max_concurrency,temp_file=f"temp_{R}.csv")
		try:
			G=await S.fetch_articles_async(sources=N,top_n=I,within=J,sort_order=L,save_to_file=_C)
			if G.empty:F=B or Q;A.logger.warning(f"No articles found for {F}");return pd.DataFrame()
			if M:T=G.to_dict('records');U=A.cleaner.clean_articles_batch(T);D=pd.DataFrame(U)
			else:D=G
			if B:D['site_name']=B
			if A.cache_enabled:A.cache.set(O,D)
			if E:D.to_csv(E,index=_C);A.logger.info(f"Results saved to {E}")
			return D
		except Exception as C:A.logger.error(f"Error fetching articles: {C}");return pd.DataFrame()
	async def _fetch_from_multiple_sites(A,sites_dict,max_articles,time_frame,sort_order=_D,clean_content=_B,save_to_file=_A):
		'\n        Fetch articles from multiple sites concurrently.\n        \n        Parameters:\n            sites_dict (dict): Dictionary mapping site names to URL lists.\n            Other parameters identical to _fetch_from_single_source.\n            \n        Returns:\n            pd.DataFrame: Combined DataFrame containing articles from all sites.\n        ';F=sites_dict;D=save_to_file;E=[];G=[]
		for(C,I)in F.items():J=A._fetch_from_single_source(sources=I,max_articles=max_articles,time_frame=time_frame,site_name=C,sort_order=sort_order,clean_content=clean_content,save_to_file=_A);G.append(J)
		K=await asyncio.gather(*G,return_exceptions=_B)
		for(L,B)in enumerate(K):
			C=list(F.keys())[L]
			if isinstance(B,Exception):A.logger.error(f"Error fetching from {C}: {B}");continue
			if not isinstance(B,pd.DataFrame)or B.empty:A.logger.warning(f"No results from {C}");continue
			E.append(B)
		if not E:A.logger.warning('No results from any site');return pd.DataFrame()
		H=pd.concat(E,ignore_index=_B)
		if D:H.to_csv(D,index=_C);A.logger.info(f"Combined results saved to {D}")
		return H
	def fetch_articles(A,*B,**C):'\n        Synchronous wrapper for fetch_articles_async.\n        \n        Parameters:\n            Same as fetch_articles_async.\n            \n        Returns:\n            pd.DataFrame: DataFrame containing articles.\n        ';return asyncio.run(A.fetch_articles_async(*B,**C))
	@cached(ttl=3600)
	def get_SITES_CONFIG(self):
		'\n        Get information about supported sites with caching.\n        \n        Returns:\n            dict: Dictionary with site information.\n        ';E='urls';B='rss';C={}
		for(D,A)in SITES_CONFIG.items():F={'name':D,'has_sitemap':bool(A.get('sitemap_url')),'has_rss':B in A and bool(A[B].get(E)),'rss_count':len(A.get(B,{}).get(E,[]))if B in A else 0,'selectors':list(A.get('config',{}).keys())};C[D]=F
		return C