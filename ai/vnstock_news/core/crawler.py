_D='sitemap'
_C='sitemap_url'
_B='records'
_A=None
from typing import List,Dict,Any,Optional,Union
from vnstock_news.config.sites import SITES_CONFIG
from vnstock_news.utils.logger import setup_logger
from vnstock_news.core.rss import RSS
from vnstock_news.core.sitemap import Sitemap
from vnstock_news.core.news import News
from vnstock_news.config.sitemap_resolver import DynamicSitemapResolver
class Crawler:
	'\n    Unified crawler: fetches lists of links via RSS or sitemap,\n    and retrieves detailed content via News parser.\n    '
	def __init__(A,site_name=_A,custom_config=_A,use_predefined_config=True,debug=False):
		'\n        Parameters:\n            site_name (str): Use a predefined site config.\n            custom_config (dict): Override config dynamically.\n            use_predefined_config (bool): Whether to use predefined config when site_name is provided.\n            debug (bool): Turn debug logging on/off.\n        ';F='config';D=debug;C=custom_config;B=site_name;A.logger=setup_logger(A.__class__.__name__,D);A.debug=D;A.sitemap_resolver=DynamicSitemapResolver(debug=D)
		if B and use_predefined_config:
			if B not in SITES_CONFIG:raise ValueError(f"Unsupported site: {B}")
			E=SITES_CONFIG[B];A.site_name=B;A.rss_urls=E.get('rss',{}).get('urls',[]);A.parser_config=E.get(F,{});A.sitemap_url=A._get_sitemap_url(B,E)
		elif C:
			A.site_name=C.get('site_name','custom')if not B else B;A.rss_urls=C.get('rss_urls',[]);A.parser_config=C.get(F,{});A.sitemap_url=C.get(_C)
			if not A.sitemap_url and _D in C:A.sitemap_url=A.sitemap_resolver.get_sitemap_url(A.site_name,C)
		else:raise ValueError('Either site_name with use_predefined_config=True or custom_config must be provided')
	def _get_sitemap_url(B,site_name,config):
		'\n        Get the appropriate sitemap URL based on the configuration structure.\n        \n        Parameters:\n            site_name: The name of the site\n            config: The site configuration\n            \n        Returns:\n            The sitemap URL or None if not available\n        ';A=config
		if _D in A:return B.sitemap_resolver.get_sitemap_url(site_name,A)
		return A.get(_C)
	def get_articles_from_feed(A,limit_per_feed=10):
		'\n        Fetch metadata only from RSS feeds.\n        ';E='link'
		if not A.rss_urls:raise ValueError('No RSS URLs configured')
		C=RSS(site_name=A.site_name,show_log=A.debug);C.rss_urls=A.rss_urls;D=C.fetch()
		for B in D:
			if E in B:B['url']=B.pop(E)
		return D[:limit_per_feed]
	def get_latest_articles(A,limit=10):
		'\n        Fetch the latest links from sitemap.\n        '
		if not A.sitemap_url:raise ValueError('No sitemap URL configured')
		B=Sitemap(A.sitemap_url,show_log=A.debug);C=B.run();return C.head(limit).to_dict(_B)
	def get_articles(A,sitemap_url=_A,limit=10,limit_per_feed=_A):
		'\n        Smart fetch articles: prioritize RSS if available, fallback to sitemap.\n        \n        Parameters:\n            sitemap_url (str or list, optional): Override the default sitemap URL(s).\n            limit (int): Maximum total number of articles to fetch.\n            limit_per_feed (int, optional): Maximum number of articles to fetch per feed.\n                                           Only applies when multiple feeds are provided.\n        ';J=limit_per_feed;D=limit;B=sitemap_url
		if A.rss_urls:
			A.logger.info('Fetching articles via RSS (preferred)')
			try:return A.get_articles_from_feed(limit_per_feed=D)
			except Exception as C:A.logger.warning(f"RSS fetch failed: {C}. Trying sitemap as fallback...")
		if isinstance(B,list):
			A.logger.info(f"Processing multiple sitemap URLs: {len(B)} sources");E=[];K=J if J is not _A else D
			for F in B:
				try:A.logger.info(f"Fetching from sitemap: {F} (limit per feed: {K})");G=Sitemap(F,show_log=A.debug);H=G.run();L=H.head(K).to_dict(_B);E.extend(L)
				except Exception as C:A.logger.warning(f"Failed to fetch from {F}: {C}")
			if E:return E[:D]
		I=B if isinstance(B,str)else A.sitemap_url
		if I:
			A.logger.info(f"Fetching articles via Sitemap (fallback): {I}")
			try:G=Sitemap(I,show_log=A.debug);H=G.run();return H.head(D).to_dict(_B)
			except Exception as C:A.logger.warning(f"Sitemap fetch failed: {C}.")
		raise ValueError('No valid RSS or Sitemap source available for fetching articles.')
	def get_article_details(D,url):'\n        Fetch full metadata + markdown content for a single URL.\n        ';A=url;B=News(A,D.parser_config,show_log=D.debug);E=B.fetch_article(A);C=B.parse(E);C['markdown_content']=B.to_markdown(E);C['url']=A;return C