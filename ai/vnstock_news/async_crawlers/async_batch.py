_I='lastmod'
_H='feed_time'
_G='feed_source'
_F='sitemap'
_E='rss'
_D='publish_time'
_C=False
_B='link'
_A=None
import os,aiohttp,asyncio,pandas as pd
from datetime import datetime,timedelta,timezone
from tqdm.asyncio import tqdm_asyncio
from vnstock_news.core.crawler import Crawler
from vnstock_news.core.rss import RSS
from vnstock_news.core.sitemap import Sitemap
from vnstock_news.utils import setup_logger
from typing import List,Union,Dict,Optional
from..config.const import DEFAULT_HEADERS
import logging
class AsyncBatchCrawler:
	'\n    Asynchronous BatchCrawler for fetching articles dynamically.\n    Supports both RSS feeds and XML sitemaps with advanced concurrency support.\n    '
	def __init__(A,site_name=_A,custom_config=_A,debug=_C,max_concurrency=5,temp_file='temp_articles.csv',output_path=_A):"\n        Initialize the AsyncBatchCrawler.\n\n        Parameters:\n            site_name (str, optional): Name of the predefined site to use.\n            custom_config (dict, optional): Custom configuration for parsing.\n            debug (bool): Enable debug logging. Defaults to False.\n            max_concurrency (int): Maximum number of concurrent requests. Defaults to 5.\n            temp_file (str): Path to the temporary file for saving progress. Defaults to 'temp_articles.csv'.\n            output_path (str, optional): Path to save the final output file.\n        ";E=max_concurrency;D=debug;C=custom_config;B=site_name;A.logger=setup_logger(A.__class__.__name__,D);A.logger.debug('Initializing AsyncBatchCrawler...');A.use_predefined_config=bool(B);A.site_name=B;A.custom_config=C;A.max_concurrency=E;A.temp_file=temp_file;A.output_path=output_path;A.crawler=Crawler(B,custom_config=C,debug=D)if A.use_predefined_config else _A;A.semaphore=asyncio.Semaphore(E)
	async def _detect_source_type_async(C,url,session):
		"\n        Asynchronously detect the source type (RSS or sitemap) based on the URL extension.\n\n        Parameters:\n            url (str): The source URL.\n            session (aiohttp.ClientSession): The aiohttp session to use for requests.\n\n        Returns:\n            str: 'rss' if the URL points to an RSS feed, 'sitemap' otherwise.\n        ";A=url
		if A.endswith('.rss'):return _E
		elif A.endswith('.xml'):return _F
		else:
			try:
				async with C.semaphore,session.get(A,headers=DEFAULT_HEADERS,timeout=10)as D:
					D.raise_for_status();B=await D.text()
					if'<rss'in B or'<channel>'in B:return _E
					elif'<urlset'in B:return _F
			except Exception as E:C.logger.error(f"Failed to detect source type for {A}: {E}");raise ValueError(f"Failed to detect source type for {A}: {E}")
			raise ValueError('Unknown source format.')
	async def prepare_feeder_async(A,sources,top_n_per_feed=_A):
		'\n        Asynchronously prepare the feeder DataFrame by detecting the source type.\n\n        Parameters:\n            sources (list): List of source URLs (RSS feeds or XML sitemaps).\n            top_n_per_feed (int, optional): Number of top links to fetch per feed.\n\n        Returns:\n            pd.DataFrame: Combined DataFrame containing article metadata or URLs.\n        ';C=[]
		async with aiohttp.ClientSession()as E:
			D=[]
			for F in sources:D.append(A._process_source(F,E,top_n_per_feed))
			G=await asyncio.gather(*D,return_exceptions=True)
			for B in G:
				if isinstance(B,Exception):A.logger.error(f"Error processing source: {B}")
				elif isinstance(B,pd.DataFrame)and not B.empty:C.append(B)
		if C:A.feed_df=pd.concat(C,ignore_index=True);return A.feed_df
		else:A.logger.warning('No valid data fetched from the provided sources.');return pd.DataFrame(columns=[_B,_D,'title','description'])
	async def _process_source(B,source,session,top_n_per_feed):
		'\n        Process a single source asynchronously.\n        \n        Parameters:\n            source (str): The source URL.\n            session (aiohttp.ClientSession): The aiohttp session to use for requests.\n            top_n_per_feed (int, optional): Number of top links to fetch per feed.\n            \n        Returns:\n            pd.DataFrame: DataFrame containing article metadata from this source.\n        ';E=top_n_per_feed;D=session;A=source
		try:
			B.logger.info(f"Checking source: {A}");F=await B._detect_source_type_async(A,D)
			if F==_E:B.logger.info(f"Parsing RSS feed: {A}");G=RSS(rss_url=A);C=await B._fetch_rss_async(G,D)
			elif F==_F:B.logger.info(f"Parsing XML sitemap: {A}");C=await B._fetch_sitemap_async(A,D)
			C[_G]=A;C[_H]=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
			if not C.empty:
				if E:C=C.head(E)
				return C
			else:B.logger.warning(f"No articles found for {A}.");return pd.DataFrame()
		except Exception as H:B.logger.error(f"Error processing {A}: {H}");raise
	async def _fetch_rss_async(C,rss_parser,session):
		'\n        Fetch RSS feed data asynchronously.\n        \n        Parameters:\n            rss_parser (RSS): The RSS parser instance.\n            session (aiohttp.ClientSession): The aiohttp session to use.\n            \n        Returns:\n            pd.DataFrame: DataFrame containing RSS feed data.\n        ';A=rss_parser;B=asyncio.get_event_loop()
		try:D=await B.run_in_executor(_A,A.fetch);return await B.run_in_executor(_A,lambda:A.parse(D))
		except Exception as E:C.logger.error(f"Error fetching RSS: {E}");return pd.DataFrame()
	async def _fetch_sitemap_async(C,sitemap_url,session):
		'\n        Fetch sitemap data asynchronously.\n        \n        Parameters:\n            sitemap_url (str): The sitemap URL.\n            session (aiohttp.ClientSession): The aiohttp session to use.\n            \n        Returns:\n            pd.DataFrame: DataFrame containing sitemap data.\n        ';A=asyncio.get_event_loop();B=Sitemap(sitemap_url)
		try:D=await A.run_in_executor(_A,B.fetch);return await A.run_in_executor(_A,lambda:B.parse(D))
		except Exception as E:C.logger.error(f"Error fetching sitemap: {E}");return pd.DataFrame()
	def filter_feeder(D,feeder,top_n=_A,within=_A,sort_order='desc'):
		'\n        Filter and sort the feeder DataFrame.\n\n        Parameters:\n            feeder (pd.DataFrame): DataFrame with article metadata.\n            top_n (int): Number of top links to fetch.\n            within (str): Time frame (e.g., "1h", "2d", "30m") to filter links.\n            sort_order (str): \'asc\' for ascending, \'desc\' for descending order.\n\n        Returns:\n            pd.DataFrame: Filtered and sorted DataFrame.\n        ';E=within;C=top_n;A=feeder.copy();F=[_D,_I,'pubDate'];B=next((B for B in F if B in A.columns),_A)
		if not B:D.logger.warning('No valid time column found. Skipping sorting/filtering by time.');return A.head(C)if C else A
		A[B]=pd.to_datetime(A[B],errors='coerce').dt.tz_localize(_A)
		if E:G=datetime.now(timezone.utc).replace(tzinfo=_A);H=D._parse_time_frame(E);I=G-H;A=A[A[B]>=I]
		J=sort_order=='asc';A=A.sort_values(by=B,ascending=J)
		if C:A=A.head(C)
		return A
	def _parse_time_frame(D,time_str):
		"\n        Parse a time frame string like '1h', '2d', or '30m' into a timedelta.\n\n        Parameters:\n            time_str (str): Time frame string.\n\n        Returns:\n            timedelta: Corresponding timedelta object.\n        ";C=time_str;A=C[-1];B=int(C[:-1])
		if A=='h':return timedelta(hours=B)
		elif A=='d':return timedelta(days=B)
		elif A=='m':return timedelta(minutes=B)
		else:raise ValueError("Invalid time frame format. Use 'h' for hours, 'd' for days, or 'm' for minutes.")
	async def _save_temp_data_async(A,data):
		'\n        Save intermediate data to a temporary file asynchronously.\n\n        Parameters:\n            data (pd.DataFrame): DataFrame containing the fetched articles.\n        ';B=asyncio.get_event_loop()
		try:await B.run_in_executor(_A,lambda:data.to_csv(A.temp_file,index=_C));A.logger.info(f"Intermediate data saved to {A.temp_file}")
		except Exception as C:A.logger.error(f"Failed to save intermediate data: {C}")
	def _load_temp_data(A):
		'\n        Load intermediate data from the temporary file if it exists.\n\n        Returns:\n            pd.DataFrame: DataFrame containing the previously saved intermediate data.\n        '
		if os.path.exists(A.temp_file):
			try:A.logger.info(f"Loading intermediate data from {A.temp_file}");return pd.read_csv(A.temp_file)
			except Exception as B:A.logger.error(f"Failed to load intermediate data: {B}")
		return pd.DataFrame()
	async def get_article_details_async(A,url,session):
		'\n        Asynchronously fetch detailed metadata and content for a specific article URL.\n\n        Parameters:\n            url (str): The URL of the article.\n            session (aiohttp.ClientSession): The aiohttp session to use.\n\n        Returns:\n            dict: Metadata and content in Markdown format.\n        ';B=url
		try:
			async with A.semaphore:D=asyncio.get_event_loop();E=await D.run_in_executor(_A,A.crawler.get_article_details,B);return E
		except Exception as C:A.logger.error(f"Failed to fetch article details for {B}: {C}");return{'error':str(C),_B:B}
	async def fetch_articles_async(A,sources,top_n=10,top_n_per_feed=_A,within=_A,sort_order='desc',save_to_file=_C):
		"\n        Asynchronously fetch detailed articles from the given sources.\n\n        Parameters:\n            sources (list | str): List of source URLs (RSS feeds or XML sitemaps).\n            top_n (int): Number of top links to fetch globally.\n            top_n_per_feed (int): Number of top links to fetch per feed.\n            within (str): Time frame to filter links (e.g., '1h', '2d').\n            sort_order (str): 'asc' for ascending, 'desc' for descending order.\n            save_to_file (bool): Save the final output directly to the specified path.\n\n        Returns:\n            pd.DataFrame: DataFrame containing article metadata and content.\n        ";E=sources
		if isinstance(E,str):E=[E]
		C=await A.prepare_feeder_async(E,top_n_per_feed=top_n_per_feed);C.columns=[A.lower()for A in C.columns];C=C.rename(columns={'url':_B,'loc':_B,'pubdate':_D,_I:_D});K=A.filter_feeder(C,top_n=top_n,within=within,sort_order=sort_order)
		if not A.crawler:A.crawler=Crawler(custom_config=A.custom_config,debug=A.logger.level<=logging.DEBUG)
		F=[];H=A._load_temp_data();G=[]
		for(V,B)in K.iterrows():
			if B[_B]in H.get(_B,[]):A.logger.info(f"Skipping already fetched article: {B[_B]}");L=H[H[_B]==B[_B]].to_dict('records')[0];F.append(L)
			else:G.append((B[_B],B[_G],B.get(_H)))
		if G:
			A.logger.info(f"Fetching details for {len(G)} new articles...")
			async with aiohttp.ClientSession()as M:
				I=[]
				for(N,O,P)in G:Q=asyncio.create_task(A._process_article(N,O,P,M));I.append(Q)
				R=await tqdm_asyncio.gather(*I,desc='Fetching Articles')
				for(S,J)in enumerate(R):
					if J is not _A:F.append(J)
					if(S+1)%10==0:T=pd.DataFrame(F);await A._save_temp_data_async(T)
		D=pd.DataFrame(F)
		if save_to_file and A.output_path and not D.empty:
			try:D.to_csv(A.output_path,index=_C);A.logger.info(f"Final data saved to {A.output_path}")
			except Exception as U:A.logger.error(f"Failed to save final data: {U}")
		if not D.empty:await A._save_temp_data_async(D)
		return D
	async def _process_article(B,url,feed_source,feed_time,session):
		'\n        Process a single article asynchronously.\n        \n        Parameters:\n            url (str): The article URL.\n            feed_source (str): The source of the feed.\n            feed_time (str): The time the feed was fetched.\n            session (aiohttp.ClientSession): The aiohttp session to use.\n            \n        Returns:\n            dict: Article details or None if processing failed.\n        '
		try:A=await B.get_article_details_async(url,session);A[_G]=feed_source;A[_H]=feed_time;return A
		except Exception as C:B.logger.error(f"Failed to process {url}: {C}");return
	def fetch_articles(A,*B,**C):'\n        Synchronous wrapper for fetch_articles_async.\n        ';return asyncio.run(A.fetch_articles_async(*B,**C))