from typing import Any
from tenacity import retry,stop_after_attempt,wait_exponential
from vnstock_data.base import BaseAdapter,dynamic_method
from vnstock_data.config import Config
class Company(BaseAdapter):
	_module_name=bytes([99,111,109,112,97,110,121]).decode();bytes([10,32,32,32,32,65,100,97,112,116,101,114,32,102,111,114,32,99,111,109,112,97,110,121,45,114,101,108,97,116,101,100,32,100,97,116,97,58,10,32,32,32,32,32,32,45,32,111,118,101,114,118,105,101,119,10,32,32,32,32,32,32,45,32,115,104,97,114,101,104,111,108,100,101,114,115,10,32,32,32,32,32,32,45,32,111,102,102,105,99,101,114,115,10,32,32,32,32,32,32,45,32,115,117,98,115,105,100,105,97,114,105,101,115,10,32,32,32,32,32,32,45,32,97,102,102,105,108,105,97,116,101,10,32,32,32,32,32,32,45,32,110,101,119,115,10,32,32,32,32,32,32,45,32,101,118,101,110,116,115,10,10,32,32,32,32,85,115,97,103,101,58,10,32,32,32,32,32,32,32,32,99,32,61,32,67,111,109,112,97,110,121,40,115,111,117,114,99,101,61,34,75,66,83,34,44,32,115,121,109,98,111,108,61,34,86,67,73,34,44,32,114,97,110,100,111,109,95,97,103,101,110,116,61,70,97,108,115,101,44,32,115,104,111,119,95,108,111,103,61,84,114,117,101,41,10,32,32,32,32,32,32,32,32,100,102,95,111,118,32,61,32,99,46,111,118,101,114,118,105,101,119,40,41,10,32,32,32,32,32,32,32,32,100,102,95,115,104,32,61,32,99,46,115,104,97,114,101,104,111,108,100,101,114,115,40,41,10,32,32,32,32,32,32,32,32,100,102,95,111,102,32,61,32,99,46,111,102,102,105,99,101,114,115,40,102,105,108,116,101,114,95,98,121,61,34,97,108,108,34,41,10,32,32,32,32,32,32,32,32,100,102,95,115,117,98,32,61,32,99,46,115,117,98,115,105,100,105,97,114,105,101,115,40,102,105,108,116,101,114,95,98,121,61,34,115,117,98,115,105,100,105,97,114,121,34,41,10,32,32,32,32,32,32,32,32,100,102,95,97,102,102,32,61,32,99,46,97,102,102,105,108,105,97,116,101,40,41,10,32,32,32,32,32,32,32,32,100,102,95,110,101,119,115,32,61,32,99,46,110,101,119,115,40,41,10,32,32,32,32,32,32,32,32,100,102,95,101,118,116,32,61,32,99,46,101,118,101,110,116,115,40,41,10,32,32,32,32]).decode()
	def __init__(B,source=bytes([75,66,83]).decode(),symbol=None,random_agent=False,show_log=False):
		A=source
		if A.lower()not in[bytes([118,99,105]).decode(),bytes([107,98,115]).decode()]:raise ValueError(bytes([76,225,187,155,112,32,67,111,109,112,97,110,121,32,99,104,225,187,137,32,110,104,225,186,173,110,32,103,105,195,161,32,116,114,225,187,139,32,116,104,97,109,32,115,225,187,145,32,115,111,117,114,99,101,32,108,195,160,32,39,86,67,73,39,32,104,111,225,186,183,99,32,39,75,66,83,39,46]).decode())
		super().__init__(source=A,symbol=symbol,random_agent=random_agent,show_log=show_log)
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def overview(self,*A,**B):'Retrieve company overview data.'
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def shareholders(self,*A,**B):'Retrieve company shareholders data.'
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def officers(self,*A,**B):"\n        Retrieve company officers data.\n        Supports kwargs like filter_by='working'|'resigned'|'all'.\n        "
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def subsidiaries(self,*A,**B):"\n        Retrieve company subsidiaries data.\n        Supports kwargs like filter_by='all'|'subsidiary'.\n        "
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def affiliate(self,*A,**B):'Retrieve company affiliate data.'
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def news(self,*A,**B):'Retrieve company news.'
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def events(self,*A,**B):'Retrieve company events.'
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def capital_history(self,*A,**B):'Retrieve company charter capital history.'
	@retry(stop=stop_after_attempt(Config.RETRIES),wait=wait_exponential(multiplier=Config.BACKOFF_MULTIPLIER,min=Config.BACKOFF_MIN,max=Config.BACKOFF_MAX))
	@dynamic_method
	def insider_trading(self,*A,**B):'Retrieve insider trading data for the given symbol.'