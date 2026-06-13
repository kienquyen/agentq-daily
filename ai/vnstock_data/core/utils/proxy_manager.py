'\nProxy manager for vnstock_data.\n\nProvides functionality to fetch, test, and manage proxies with speed tracking\nand intelligent selection strategies.\n'
from datetime import datetime
from typing import Any
import requests
from vnstock.core.utils.logger import get_logger
from.proxy import Proxy
logger=get_logger(__name__)
class ProxyManager:
	'\n    Manages proxy fetching, testing, and selection.\n    \n    Features:\n    - Fetch proxies from proxyscrape API\n    - Test proxy connectivity and speed\n    - Track proxy metadata (speed, last_checked, country)\n    - Select proxies based on different strategies\n    - Maintain proxy cache\n    ';PROXYSCRAPE_API=bytes([104,116,116,112,115,58,47,47,97,112,105,46,112,114,111,120,121,115,99,114,97,112,101,46,99,111,109,47,118,50,47]).decode()
	def __init__(A,timeout=5):'\n        Initialize ProxyManager.\n        \n        Args:\n            timeout: Request timeout in seconds (default: 5)\n        ';A.timeout=timeout;A.proxy_cache={};A.last_fetch=None
	def fetch_proxies(A,limit=10,protocol=bytes([104,116,116,112]).decode(),ssl=bytes([97,108,108]).decode(),anonymity=bytes([97,108,108]).decode(),country=None):
		'\n        Fetch proxies from proxyscrape API.\n        \n        Args:\n            limit: Number of proxies to fetch (default: 10)\n            protocol: Protocol type - http, socks4, socks5 (default: http)\n            ssl: SSL support - yes, no, all (default: all)\n            anonymity: Anonymity level - elite, anonymous, transparent, all (default: all)\n            country: Country code filter (optional)\n        \n        Returns:\n            List[Proxy]: List of fetched proxies\n        \n        Raises:\n            requests.RequestException: If API request fails\n        ';G=country;F=protocol;E=limit
		try:
			H={bytes([114,101,113,117,101,115,116]).decode():bytes([103,101,116,112,114,111,120,105,101,115]).decode(),bytes([102,111,114,109,97,116]).decode():bytes([106,115,111,110]).decode(),bytes([112,114,111,116,111,99,111,108]).decode():F,bytes([115,115,108]).decode():ssl,bytes([97,110,111,110,121,109,105,116,121]).decode():anonymity,bytes([108,105,109,105,116]).decode():E,bytes([115,105,109,112,108,105,102,105,101,100]).decode():bytes([116,114,117,101]).decode()}
			if G:H[bytes([99,111,117,110,116,114,121]).decode()]=G
			logger.info(f"Fetching {E} proxies from proxyscrape API...");I=requests.get(A.PROXYSCRAPE_API,params=H,timeout=A.timeout);I.raise_for_status();J=I.json();B=[]
			if J.get(bytes([112,114,111,120,105,101,115]).decode()):
				for C in J[bytes([112,114,111,120,105,101,115]).decode()]:D=Proxy(protocol=F.upper(),ip=C.get(bytes([105,112]).decode()),port=int(C.get(bytes([112,111,114,116]).decode(),0)),country=C.get(bytes([99,111,117,110,116,114,121]).decode()),last_checked=datetime.now());B.append(D);A.proxy_cache[str(D)]=D
			A.last_fetch=datetime.now();logger.info(f"Successfully fetched {len(B)} proxies");return B
		except requests.RequestException as K:logger.error(f"Failed to fetch proxies: {K}");raise
	def test_proxies(F,proxies,test_url=bytes([104,116,116,112,115,58,47,47,104,116,116,112,98,105,110,46,111,114,103,47,105,112]).decode(),timeout=None):
		'\n        Test proxy connectivity and measure speed.\n        \n        Args:\n            proxies: List of proxies to test\n            test_url: URL to test proxy against (default: httpbin.org)\n            timeout: Request timeout in seconds (default: self.timeout)\n        \n        Returns:\n            List[Proxy]: List of valid proxies with speed measurements\n        ';D=proxies;B=timeout
		if B is None:B=F.timeout
		C=[]
		for A in D:
			try:
				G={bytes([104,116,116,112]).decode():str(A),bytes([104,116,116,112,115]).decode():str(A)};H=datetime.now();I=requests.get(test_url,proxies=G,timeout=B);J=datetime.now()
				if I.status_code==200:E=(J-H).total_seconds()*1000;A.speed=E;A.last_checked=datetime.now();C.append(A);logger.debug(f"Proxy {A} is valid (speed: {E:.2f}ms)")
			except(requests.RequestException,Exception)as K:logger.debug(f"Proxy {A} failed: {K}");continue
		logger.info(f"Tested {len(D)} proxies, {len(C)} are valid");return C
	def get_best_proxy(D,proxies):
		'\n        Get proxy with best speed.\n        \n        Args:\n            proxies: List of proxies to choose from\n        \n        Returns:\n            Optional[Proxy]: Proxy with best speed, or None if list is empty\n        ';A=proxies
		if not A:return
		C=[A for A in A if A.speed is not None]
		if not C:return A[0]
		B=min(C,key=lambda p:p.speed);logger.debug(f"Best proxy selected: {B} (speed: {B.speed:.2f}ms)");return B
	def select_proxy(C,proxies,mode=bytes([98,101,115,116]).decode()):
		'\n        Select proxy based on mode.\n        \n        Args:\n            proxies: List of proxies to choose from\n            mode: Selection mode - best, random, first (default: best)\n        \n        Returns:\n            Optional[Proxy]: Selected proxy, or None if list is empty\n        ';B=mode;A=proxies
		if not A:return
		if B==bytes([98,101,115,116]).decode():return C.get_best_proxy(A)
		elif B==bytes([114,97,110,100,111,109]).decode():import random as D;return D.choice(A)
		elif B==bytes([102,105,114,115,116]).decode():return A[0]
		else:logger.warning(f"Unknown selection mode: {B}, using 'first'");return A[0]
	def validate_proxy(B,proxy):
		'\n        Validate if proxy is still working.\n        \n        Args:\n            proxy: Proxy to validate\n        \n        Returns:\n            bool: True if proxy is valid, False otherwise\n        ';A=proxy
		try:
			C={bytes([104,116,116,112]).decode():str(A),bytes([104,116,116,112,115]).decode():str(A)};D=requests.get(bytes([104,116,116,112,115,58,47,47,104,116,116,112,98,105,110,46,111,114,103,47,105,112]).decode(),proxies=C,timeout=B.timeout)
			if D.status_code==200:A.last_checked=datetime.now();return True
			return False
		except Exception as E:logger.debug(f"Proxy validation failed: {E}");return False
	def get_cached_proxies(A):'\n        Get all cached proxies.\n        \n        Returns:\n            List[Proxy]: List of cached proxies\n        ';return list(A.proxy_cache.values())
	def clear_cache(A):'Clear proxy cache.';A.proxy_cache.clear();logger.info(bytes([80,114,111,120,121,32,99,97,99,104,101,32,99,108,101,97,114,101,100]).decode())
	def get_cache_stats(A):'\n        Get cache statistics.\n        \n        Returns:\n            Dict: Cache statistics including size, last fetch time, etc.\n        ';B=[A for A in A.proxy_cache.values()if A.is_valid()];return{bytes([116,111,116,97,108,95,99,97,99,104,101,100]).decode():len(A.proxy_cache),bytes([118,97,108,105,100,95,112,114,111,120,105,101,115]).decode():len(B),bytes([108,97,115,116,95,102,101,116,99,104]).decode():A.last_fetch.isoformat()if A.last_fetch else None,bytes([99,97,99,104,101,95,115,105,122,101]).decode():len(A.proxy_cache)}