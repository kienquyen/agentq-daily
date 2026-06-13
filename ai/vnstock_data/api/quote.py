'\nvnstock/api/quote.py\n\nUnified Quote adapter with dynamic method detection and parameter filtering.\n'
from typing import Any
from tenacity import retry,stop_after_attempt,wait_exponential
from vnstock_data.base import BaseAdapter,dynamic_method
from vnstock_data.config import Config
class Quote(BaseAdapter):
	_module_name=bytes([113,117,111,116,101]).decode();bytes([10,32,32,32,32,65,100,97,112,116,101,114,32,102,111,114,32,104,105,115,116,111,114,105,99,97,108,32,97,110,100,32,105,110,116,114,97,100,97,121,32,113,117,111,116,101,32,100,97,116,97,46,10,10,32,32,32,32,85,115,97,103,101,58,10,32,32,32,32,32,32,32,32,113,32,61,32,81,117,111,116,101,40,115,111,117,114,99,101,61,34,118,99,105,34,44,32,115,121,109,98,111,108,61,34,86,67,73,34,44,32,114,97,110,100,111,109,95,97,103,101,110,116,61,70,97,108,115,101,44,32,115,104,111,119,95,108,111,103,61,84,114,117,101,41,10,32,32,32,32,32,32,32,32,100,102,32,61,32,113,46,104,105,115,116,111,114,121,40,115,116,97,114,116,61,34,50,48,50,52,45,48,49,45,48,49,34,44,32,101,110,100,61,34,50,48,50,52,45,48,52,45,49,56,34,44,32,105,110,116,101,114,118,97,108,61,34,49,68,34,41,10,32,32,32,32,32,32,32,32,100,102,50,32,61,32,113,46,105,110,116,114,97,100,97,121,40,112,97,103,101,95,115,105,122,101,61,49,48,48,41,10,32,32,32,32,32,32,32,32,100,101,112,116,104,32,61,32,113,46,112,114,105,99,101,95,100,101,112,116,104,40,41,10,32,32,32,32]).decode()
	def __init__(B,source=bytes([75,66,83]).decode(),symbol='',random_agent=False,show_log=False):
		A=source
		if A.lower()not in[bytes([118,99,105]).decode(),bytes([107,98,115]).decode(),bytes([118,110,100]).decode(),bytes([109,97,115]).decode()]:raise ValueError(bytes([76,225,187,155,112,32,81,117,111,116,101,32,99,104,225,187,137,32,110,104,225,186,173,110,32,103,105,195,161,32,116,114,225,187,139,32,116,104,97,109,32,115,225,187,145,32,115,111,117,114,99,101,32,108,195,160,32,39,86,67,73,39,44,32,39,75,66,83,39,44,32,39,86,78,68,39,32,104,111,225,186,183,99,32,39,77,65,83,39,46]).decode())
		super().__init__(source=A,symbol=symbol,random_agent=random_agent,show_log=show_log)
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def history(self,*A,**B):'\n        Load historical OHLC data for the symbol.\n\n        Forwards only supported kwargs to provider.history().\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def intraday(self,*A,**B):'\n        Load intraday trade data for the symbol.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def price_depth(self,*A,**B):'\n        Load price depth (order book) data for the symbol.\n        '