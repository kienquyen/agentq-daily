'\nvnstock/api/trading.py\n\nUnified Trading adapter with dynamic method detection and parameter filtering.\n'
from typing import Any
from tenacity import retry,stop_after_attempt,wait_exponential
from vnstock_data.base import BaseAdapter,dynamic_method
from vnstock_data.config import Config
class Trading(BaseAdapter):
	_module_name=bytes([116,114,97,100,105,110,103]).decode();bytes([10,32,32,32,32,65,100,97,112,116,101,114,32,102,111,114,32,116,114,97,100,105,110,103,32,100,97,116,97,58,32,116,114,97,100,105,110,103,95,115,116,97,116,115,44,32,115,105,100,101,95,115,116,97,116,115,44,32,112,114,105,99,101,95,98,111,97,114,100,46,10,10,32,32,32,32,85,115,97,103,101,58,10,32,32,32,32,32,32,32,32,116,32,61,32,84,114,97,100,105,110,103,40,115,111,117,114,99,101,61,34,118,99,105,34,44,32,115,121,109,98,111,108,61,34,86,67,73,34,44,32,114,97,110,100,111,109,95,97,103,101,110,116,61,70,97,108,115,101,44,32,115,104,111,119,95,108,111,103,61,84,114,117,101,41,10,32,32,32,32,32,32,32,32,100,102,32,61,32,116,46,116,114,97,100,105,110,103,95,115,116,97,116,115,40,115,116,97,114,116,61,34,50,48,50,52,45,48,49,45,48,49,34,44,32,101,110,100,61,34,50,48,50,52,45,49,50,45,51,49,34,44,32,108,105,109,105,116,61,49,48,48,48,41,10,32,32,32,32,32,32,32,32,98,105,100,115,44,32,97,115,107,115,32,61,32,116,46,115,105,100,101,95,115,116,97,116,115,40,100,114,111,112,110,97,61,84,114,117,101,41,10,32,32,32,32,32,32,32,32,98,111,97,114,100,32,61,32,116,46,112,114,105,99,101,95,98,111,97,114,100,40,115,121,109,98,111,108,115,95,108,105,115,116,61,91,34,86,67,73,34,44,32,34,86,67,66,34,93,44,32,42,42,107,119,97,114,103,115,41,10,32,32,32,32]).decode()
	def __init__(C,source=bytes([75,66,83]).decode(),symbol='',random_agent=False,show_log=False):
		B=source;A=symbol
		if B.lower()not in[bytes([118,99,105]).decode(),bytes([107,98,115]).decode(),bytes([118,110,100]).decode(),bytes([99,97,102,101,102]).decode()]:raise ValueError(bytes([76,225,187,155,112,32,84,114,97,100,105,110,103,32,99,104,225,187,137,32,110,104,225,186,173,110,32,103,105,195,161,32,116,114,225,187,139,32,116,104,97,109,32,115,225,187,145,32,115,111,117,114,99,101,32,108,195,160,32,39,86,67,73,39,44,32,39,75,66,83,39,44,32,39,86,78,68,39,32,104,111,225,186,183,99,32,39,67,65,70,69,70,39,46]).decode())
		if not A or A.strip()=='':A=bytes([86,67,73]).decode()
		super().__init__(source=B,symbol=A,random_agent=random_agent,show_log=show_log)
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def trading_stats(self,*A,**B):'\n        Retrieve trading statistics for the given symbol.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def side_stats(self,*A,**B):'\n        Retrieve bid/ask side statistics for the given symbol.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def price_board(self,*A,**B):'\n        Retrieve the price board (order book) for a list of symbols.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def price_history(self,*A,**B):'\n        Retrieve the price history for a list of symbols.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def foreign_trade(self,*A,**B):'\n        Retrieve foreign trade data for the given symbol.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def prop_trade(self,*A,**B):'\n        Retrieve property trade data for the given symbol.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def insider_deal(self,*A,**B):'\n        Retrieve insider deal data for the given symbol.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def order_stats(self,*A,**B):'\n        Retrieve order statistics for the given symbol.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def matched_by_price(self,*A,**B):'\n        Retrieve trade data matched by price level for the given symbol.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def odd_lot(self,*A,**B):'\n        Retrieve odd-lot (lô lẻ) trading data.\n        '
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def put_through(self,*A,**B):'\n        Retrieve put-through (thỏa thuận) trading data.\n        '