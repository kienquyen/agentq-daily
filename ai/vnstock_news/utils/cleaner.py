_H='html.parser'
_G='multiple_newlines'
_F='multiple_spaces'
_E='html_tags'
_D=False
_C=' '
_B=True
_A=None
import re,unicodedata
from typing import List,Dict,Optional,Any,Union
import html
from bs4 import BeautifulSoup,Comment
from vnstock_news.utils.logger import setup_logger
class ContentCleaner:
	'\n    Cleans and normalizes article content.\n    '
	def __init__(A,debug=_D):'\n        Initialize the content cleaner.\n        \n        Parameters:\n            debug (bool): Enable debug logging.\n        ';C="'";B='"';A.logger=setup_logger(A.__class__.__name__,debug);A.patterns={'email':'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b','phone':'\\b(\\+?[0-9]{1,3}[-.\\s]?)?(\\([0-9]{1,4}\\)|[0-9]{1,4})[-.\\s]?[0-9]{1,4}[-.\\s]?[0-9]{1,9}\\b','url':'https?://[^\\s]+',_E:'<[^>]*>',_F:'\\s+',_G:'\\n{3,}','special_chars':'[^\\w\\s\\.,;:!?\\(\\)\\[\\]\\{\\}\\-\\\'\\"\\/]','copyright':'©.*?\\d{4}','advertisement':'(advert(isement)?s?|sponsored content|promoted by)','social_media':'(follow us on|twitter|facebook|instagram|linkedin|subscribe)'};A.replacements={'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':B,'&apos;':C,'\xa0':_C,'‘':C,'’':C,'“':B,'”':B,'–':'-','—':'--','…':'...'};A.compiled_patterns={A:re.compile(B,re.IGNORECASE)for(A,B)in A.patterns.items()}
	def clean_html(Q,html_content,remove_tags=_A,keep_tags=_A,remove_attrs=_A,keep_attrs=_A,remove_classes=_A,remove_ids=_A):
		'\n        Clean HTML content, removing unwanted elements while preserving structure.\n        \n        Parameters:\n            html_content (str): HTML content to clean.\n            remove_tags (list): List of tag names to remove entirely.\n            keep_tags (list): List of tag names to keep (removes all others).\n            remove_attrs (list): List of attribute names to remove from all tags.\n            keep_attrs (list): List of attribute names to keep (removes all others).\n            remove_classes (list): List of class names to remove elements with.\n            remove_ids (list): List of id values to remove elements with.\n            \n        Returns:\n            str: Cleaned HTML content.\n        ';M='style';L=remove_ids;K=remove_classes;J=keep_attrs;I=keep_tags;H=html_content;F=remove_attrs;E=remove_tags
		if not H:return''
		if E is _A:E=['script',M,'iframe','noscript','meta','link','button','form','input','textarea','select','option']
		if F is _A:F=['onclick','onload','onerror','onmouseover','onmouseout',M,'data-','aria-']
		B=BeautifulSoup(H,_H)
		for N in B.find_all(text=lambda text:isinstance(text,Comment)):N.extract()
		if E:
			for A in E:
				for D in B.find_all(A):D.extract()
		if I:
			for A in B.find_all():
				if A.name not in I:A.extract()
		if K:
			for O in K:
				for D in B.find_all(class_=O):D.extract()
		if L:
			for P in L:
				for D in B.find_all(id=P):D.extract()
		for A in B.find_all():
			if F:
				for C in list(A.attrs.keys()):
					for G in F:
						if G.endswith('-')and C.startswith(G[:-1]):del A[C]
						elif C==G:del A[C]
			if J:
				for C in list(A.attrs.keys()):
					if C not in J:del A[C]
		return str(B)
	def clean_text(B,text,remove_urls=_B,remove_emails=_B,remove_phones=_B,normalize_whitespace=_B,normalize_unicode=_B,convert_html_entities=_B,remove_html_tags=_B,limit_newlines=_B):
		'\n        Clean plain text content.\n        \n        Parameters:\n            text (str): Text content to clean.\n            remove_urls (bool): Remove URLs.\n            remove_emails (bool): Remove email addresses.\n            remove_phones (bool): Remove phone numbers.\n            normalize_whitespace (bool): Normalize whitespace.\n            normalize_unicode (bool): Normalize Unicode characters.\n            convert_html_entities (bool): Convert HTML entities.\n            remove_html_tags (bool): Remove any HTML tags.\n            limit_newlines (bool): Limit consecutive newlines.\n            \n        Returns:\n            str: Cleaned text content.\n        '
		if not text:return''
		A=text
		if convert_html_entities:A=html.unescape(A)
		if normalize_unicode:
			for(C,D)in B.replacements.items():A=A.replace(C,D)
			A=unicodedata.normalize('NFKC',A)
		if remove_urls:A=B.compiled_patterns['url'].sub(_C,A)
		if remove_emails:A=B.compiled_patterns['email'].sub(_C,A)
		if remove_phones:A=B.compiled_patterns['phone'].sub(_C,A)
		if remove_html_tags:A=B.compiled_patterns[_E].sub(_C,A)
		if normalize_whitespace:A=B.compiled_patterns[_F].sub(_C,A)
		if limit_newlines:A=B.compiled_patterns[_G].sub('\n\n',A)
		return A.strip()
	def extract_main_content(M,html_content,content_selectors=_A):
		'\n        Extract the main content from an HTML document.\n        \n        Parameters:\n            html_content (str): HTML content.\n            content_selectors (list): List of dictionaries with css selectors to try.\n            \n        Returns:\n            str: Extracted main content HTML.\n        ';L='post-content';K='article-content';J='content';H=content_selectors;G=html_content;E='tag';C='id';B='class'
		if not G:return''
		F=BeautifulSoup(G,_H)
		if H is _A:H=[{E:'article'},{B:J},{B:K},{B:L},{B:'entry-content'},{C:J},{C:'main-content'},{C:K},{C:L}]
		for A in H:
			D=_A
			if E in A and B in A:D=F.find(A[E],class_=A[B])
			elif E in A and C in A:D=F.find(A[E],id=A[C])
			elif E in A:D=F.find(A[E])
			elif B in A:D=F.find(class_=A[B])
			elif C in A:D=F.find(id=A[C])
			if D:return str(D)
		I=F.find('body')
		if I:return str(I)
		return G
	def remove_boilerplate(E,text,boilerplate_phrases=_A,remove_author_line=_B,remove_publication_info=_B):
		'\n        Remove common boilerplate content from text.\n        \n        Parameters:\n            text (str): Text content.\n            boilerplate_phrases (list): List of boilerplate phrases to remove.\n            remove_author_line (bool): Remove author line at beginning/end.\n            remove_publication_info (bool): Remove publication info.\n            \n        Returns:\n            str: Text with boilerplate removed.\n        ';B=boilerplate_phrases
		if not text:return''
		A=text
		if B is _A:B=['Share this article','Follow us on','Read more:','Click here to','Sign up for our newsletter','Related articles:','Source:','Credit:','Image credit:','Photo credit:','For more information','All rights reserved','Copyright ©']
		for C in B:D=re.compile(f"{re.escape(C)}.*?(\\n|$)",re.IGNORECASE);A=D.sub('\n',A)
		if remove_author_line:A=re.sub('^By\\s+[A-Z][a-z]+(\\s+[A-Z][a-z]+)*\\s*\\n','',A);A=re.sub('\\n[Bb]y\\s+[A-Z][a-z]+(\\s+[A-Z][a-z]+)*\\s*$','',A)
		if remove_publication_info:A=re.sub('^(Published|Updated|Posted)(\\s+on)?\\s+\\w+,\\s+\\w+\\s+\\d{1,2},\\s+\\d{4}.*?\\n','',A);A=re.sub('\\n(Published|Updated|Posted)(\\s+on)?\\s+\\w+,\\s+\\w+\\s+\\d{1,2},\\s+\\d{4}.*?$','',A)
		return A.strip()
	def normalize_title(D,title):
		'\n        Normalize article title.\n        \n        Parameters:\n            title (str): Article title.\n            \n        Returns:\n            str: Normalized title.\n        ';A=title
		if not A:return''
		A=html.unescape(A);A=re.sub('<[^>]+>','',A);A=re.sub('\\s+',_C,A).strip();B=['\\[sponsored\\]','\\[exclusive\\]','\\[update\\]','\\[video\\]','\\[photos\\]','\\[opinion\\]','\\|.*$','-\\s*\\w+\\.\\w+$']
		for C in B:A=re.sub(C,'',A,flags=re.IGNORECASE)
		if A:A=A[0].upper()+A[1:]
		return A.strip()
	def clean_article(B,article):
		'\n        Clean all components of an article dictionary.\n        \n        Parameters:\n            article (dict): Article dictionary with title, content, etc.\n            \n        Returns:\n            dict: Cleaned article dictionary.\n        ';I=article;H='html_content';G='markdown_content';F='short_description';E='title';D='author';C='publish_time'
		if not I:return{}
		A=I.copy()
		if E in A:A[E]=B.normalize_title(A[E])
		if F in A:A[F]=B.clean_text(A[F])
		if G in A:J=B.remove_boilerplate(A[G]);A[G]=B.clean_text(J,remove_urls=_D,remove_html_tags=_D)
		if H in A:K=B.extract_main_content(A[H]);A[H]=B.clean_html(K)
		if C in A and A[C]:A[C]=str(A[C])
		if D in A and A[D]:A[D]=B.clean_text(A[D])
		return A
	def clean_articles_batch(A,articles):'\n        Clean a batch of articles.\n        \n        Parameters:\n            articles (list): List of article dictionaries.\n            \n        Returns:\n            list: List of cleaned article dictionaries.\n        ';return[A.clean_article(B)for B in articles]