from vnstock_data.base import BaseAdapter,dynamic_method
class Macro(BaseAdapter):
	'\n    Adapter for macroeconomic data from multiple providers (e.g. MBK).\n    \n    Usage:\n        from vnstock_data.api.macro import Macro\n        m = Macro(source="mbk", random_agent=False, show_log=False)\n        df = m.gdp(start="2015-01", end="2025-04", period="quarter")\n    ';_module_name=bytes([109,97,99,114,111]).decode()
	def __init__(B,source=bytes([109,98,107]).decode(),random_agent=False,show_log=False):
		A=source
		if A!=bytes([109,98,107]).decode():raise ValueError(bytes([76,225,187,155,112,32,77,97,99,114,111,32,107,104,195,180,110,103,32,104,225,187,151,32,116,114,225,187,163,32,116,104,97,121,32,196,145,225,187,149,105,32,116,104,97,109,32,115,225,187,145,32,115,111,117,114,99,101,46]).decode())
		super().__init__(source=A,random_agent=random_agent,show_log=show_log)
	@dynamic_method
	def gdp(self,start=None,end=None,period=bytes([113,117,97,114,116,101,114]).decode(),keep_label=False,length=None):'\n        Fetch GDP series.\n        '
	@dynamic_method
	def cpi(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):'\n        Fetch CPI series.\n        '
	@dynamic_method
	def industry_prod(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):'\n        Fetch Industrial Production series.\n        '
	@dynamic_method
	def import_export(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):'\n        Fetch Import-Export series.\n        '
	@dynamic_method
	def retail(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):'\n        Fetch Retail sales series.\n        '
	@dynamic_method
	def fdi(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):'\n        Fetch Foreign Direct Investment series.\n        '
	@dynamic_method
	def money_supply(self,start=None,end=None,period=bytes([109,111,110,116,104]).decode(),length=None):'\n        Fetch Money Supply series.\n        '
	@dynamic_method
	def exchange_rate(self,start=None,end=None,period=bytes([100,97,121]).decode(),length=None):'\n        Fetch Exchange Rate series.\n        '
	@dynamic_method
	def interest_rate(self,start=None,end=None,period=bytes([100,97,121]).decode(),format=bytes([112,105,118,111,116]).decode(),length=None):'\n        Fetch Interest Rate series.\n        '
	@dynamic_method
	def population_labor(self,start=None,end=None,period=bytes([121,101,97,114]).decode(),length=None):'\n        Fetch Population and Labor series.\n        '