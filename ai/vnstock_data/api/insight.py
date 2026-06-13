from vnstock_data.base import BaseAdapter,dynamic_method
class TopStock(BaseAdapter):
	'\n    Adapter for VND TopStock “insight” APIs.  Only supports source="vnd".\n    ';_module_name=bytes([105,110,115,105,103,104,116]).decode();SUPPORTED_SOURCES=[bytes([118,110,100]).decode()]
	def __init__(C,source=bytes([118,110,100]).decode(),**D):
		A=source;B=A.lower()
		if B not in C.SUPPORTED_SOURCES:raise ValueError(bytes([76,225,187,155,112,32,84,111,112,83,116,111,99,107,32,99,104,225,187,137,32,110,104,225,186,173,110,32,103,105,195,161,32,116,114,225,187,139,32,116,104,97,109,32,115,225,187,145,32,115,111,117,114,99,101,32,108,195,160,32,39,86,78,68,39,46,32]).decode()+bytes([78,104,198,176,110,103,32,110,104,225,186,173,110,32,196,145,198,176,225,187,163,99,32,39]).decode()+A+bytes([39,46]).decode())
		super().__init__(source=B,**D)
	@dynamic_method
	def gainer(self,index=bytes([86,78,73,78,68,69,88]).decode(),limit=10):'\n        Top 10 gainers in the given index.\n        '
	@dynamic_method
	def loser(self,index=bytes([86,78,73,78,68,69,88]).decode(),limit=10):'\n        Top 10 losers in the given index.\n        '
	@dynamic_method
	def value(self,index=bytes([86,78,73,78,68,69,88]).decode(),limit=10):'\n        Top 10 by trading value in the given index.\n        '
	@dynamic_method
	def volume(self,index=bytes([86,78,73,78,68,69,88]).decode(),limit=10):'\n        Top 10 by abnormal volume in the given index.\n        '
	@dynamic_method
	def deal(self,index=bytes([86,78,73,78,68,69,88]).decode(),limit=10):'\n        Top 10 by block trade volume in the given index.\n        '
	@dynamic_method
	def foreign_buy(self,date=None,limit=10):'\n        Top 10 net foreign buys on the given date.\n        '
	@dynamic_method
	def foreign_sell(self,date=None,limit=10):'\n        Top 10 net foreign sells on the given date.\n        '