_A='html.parser'
import requests
from bs4 import BeautifulSoup
import html2text
from typing import Dict,Any,Optional
from vnstock_news.config.const import DEFAULT_HEADERS
from vnstock_news.utils.logger import setup_logger
from vnstock_news.core.base import BaseParser
class News(BaseParser):
	'\n    Parser for extracting metadata and content from a single news article.\n    '
	def __init__(A,url,config,show_log=False):'\n        Parameters:\n            url (str): Optional sitemap URL placeholder (ignored).\n            config (dict): CSS selectors for title/content/etc.\n            show_log (bool): Turn debug logging on/off.\n        ';super().__init__(show_log);A.config=config
	def fetch(A):'\n        Download the HTML of one article.\n        ';raise NotImplementedError('Use fetch_article(url) instead')
	def fetch_article(B,url):'\n        Fetch and return raw HTML for a given article URL.\n        ';B.logger.info(f"Fetching article HTML: {url}");A=requests.get(url,headers=DEFAULT_HEADERS,timeout=60);A.raise_for_status();return A.text
	def parse(A,raw_html):
		'\n        Extract metadata fields from HTML string.\n        ';C=BeautifulSoup(raw_html,_A)
		def B(sel):
			A=sel
			if not A:return
			B=C.find(A.get('tag'),class_=A.get('class'));return B.get_text(strip=True)if B else None
		return{'title':B(A.config.get('title_selector')),'short_description':B(A.config.get('short_desc_selector')),'publish_time':B(A.config.get('publish_time_selector')),'author':B(A.config.get('author_selector'))}
	def to_markdown(D,raw_html,retain_links=True,retain_images=True):
		'\n        Convert main article content into Markdown.\n        ';E=BeautifulSoup(raw_html,_A);A=D.config.get('content_selector')
		if not A:raise ValueError("Missing 'content_selector'")
		C=E.find(A.get('tag'),class_=A.get('class'))
		if not C:raise ValueError('Article content not found')
		B=html2text.HTML2Text();B.ignore_links=not retain_links;B.ignore_images=not retain_images;return B.handle(str(C))