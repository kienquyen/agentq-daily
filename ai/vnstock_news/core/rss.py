_B='markdown'
_A='text'
import requests,pandas as pd
from bs4 import BeautifulSoup
from typing import List,Dict,Any
from vnstock_news.config.const import DEFAULT_HEADERS
from vnstock_news.config.sites import DEFAULT_RSS_MAPPING
from vnstock_news.core.base import BaseParser
class RSS(BaseParser):
	'\n    Parser for RSS feeds into a DataFrame of articles.\n    '
	def __init__(A,site_name=None,description_format=_A,rss_url=None,show_log=False):
		"\n        Parameters:\n            site_name (str): Use predefined config if provided.\n            description_format (str): 'text', 'html' or 'markdown'.\n            rss_url (str): Custom RSS URL (overrides site_name).\n            show_log (bool): Turn debug logging on/off.\n        ";C=site_name;B=rss_url;super().__init__(show_log);A.description_format=description_format.lower();A.rss_urls=[];A.mapping=DEFAULT_RSS_MAPPING
		if C:from vnstock_news.config.sites import SITES_CONFIG as E;F=E.get(C,{});D=F.get('rss',{});A.rss_urls=D.get('urls',[]);A.mapping=D.get('mapping',DEFAULT_RSS_MAPPING);A.logger.debug(f"Using RSS URLs from config: {A.rss_urls}")
		if B:A.rss_urls=[B];A.logger.debug(f"Manual RSS URL provided: {B}")
		if not A.rss_urls:raise ValueError('No RSS feed URLs available')
		if A.description_format not in{_A,'html',_B}:raise ValueError("description_format must be 'text', 'html', or 'markdown'")
	def fetch(A):
		'\n        Download each RSS URL, parse <item> tags into dicts.\n        ';E=[]
		for C in A.rss_urls:
			try:
				A.logger.info(f"Fetching RSS feed: {C}");F=requests.get(C,headers=DEFAULT_HEADERS,timeout=10);F.raise_for_status();J=BeautifulSoup(F.content,'xml')
				for K in J.find_all('item'):
					G={}
					for(H,L)in A.mapping.items():
						D=K.find(L)
						if D and D.text:
							B=D.text.strip()
							if H=='description':
								if A.description_format==_A:B=BeautifulSoup(B,'html.parser').get_text()
								elif A.description_format==_B:import html2text as M;I=M.HTML2Text();I.ignore_links=False;B=I.handle(B)
							G[H]=B
					E.append(G)
			except Exception as N:A.logger.error(f"Error fetching RSS {C}: {N}")
		return E
	def parse(A,raw):
		'\n        Normalize list of dicts into a pandas DataFrame.\n        '
		if not raw:return pd.DataFrame(columns=list(A.mapping.keys()))
		B=pd.DataFrame(raw);B=B.rename(columns=A.mapping);return B[list(A.mapping.values())]