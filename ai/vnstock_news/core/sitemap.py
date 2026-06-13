_C='coerce'
_B=None
_A='lastmod'
import requests,pandas as pd
from io import StringIO
from datetime import datetime
from typing import Optional
from vnstock_news.config.const import DEFAULT_HEADERS
from vnstock_news.core.base import BaseParser
class Sitemap(BaseParser):
	'\n    Parser for XML sitemaps into a DataFrame of URLs and optional lastmod dates.\n    '
	def __init__(A,url,show_log=False):'\n        Parameters:\n            url (str): The sitemap URL to download.\n            show_log (bool): Turn debug logging on/off.\n        ';super().__init__(show_log);A.url=url
	def fetch(A):'\n        Download the sitemap XML as text.\n        ';A.logger.info(f"Fetching sitemap from {A.url}");B=requests.get(A.url,headers=DEFAULT_HEADERS,timeout=30);B.raise_for_status();return B.text
	def parse(D,raw):
		"\n        Parse sitemap XML string manually into DataFrame ['url', 'lastmod'].\n        ";B='url';from bs4 import BeautifulSoup as I
		try:
			J=I(raw,'xml');K=J.find_all(B);C=[]
			for E in K:
				F=E.find('loc');G=E.find(_A)
				if F:
					H={B:F.text.strip()}
					if G:H[_A]=G.text.strip()
					C.append(H)
			if not C:D.logger.warning('No URLs found in sitemap.')
			A=pd.DataFrame(C)
			if _A in A.columns:A[_A]=pd.to_datetime(A[_A],errors=_C)
			return A[[B,_A]]if _A in A.columns else A[[B]]
		except Exception as L:D.logger.error(f"Failed to parse sitemap manually: {L}");return pd.DataFrame(columns=[B,_A])
	def filter_by_date(C,df,start=_B,end=_B):
		'\n        Filter DataFrame rows by lastmod between `start` and `end`.\n        If no lastmod column, returns df unchanged.\n        ';B=start;A=df
		if _A not in A.columns or A[_A].isnull().all():return A
		A[_A]=pd.to_datetime(A[_A],errors=_C).dt.tz_localize(_B)
		if B:A=A[A[_A]>=pd.Timestamp(B).tz_localize(_B)]
		if end:A=A[A[_A]<=pd.Timestamp(end).tz_localize(_B)]
		return A