from vnstock_data.base import BaseAdapter,dynamic_method
class CommodityPrice(BaseAdapter):
	'\n    Adapter for commodity prices from various SPL‐based providers.\n\n    Usage:\n        from vnstock_data.api.commodity import CommodityPrice\n        c = CommodityPrice(source="spl", start="2024-01-01", end="2024-04-01", show_log=False)\n        df = c.gold_vn()\n    ';_module_name=bytes([99,111,109,109,111,100,105,116,121]).decode()
	def __init__(B,source=bytes([115,112,108]).decode(),start=None,end=None,length=None,show_log=False):
		A=source
		if A.lower()!=bytes([115,112,108]).decode():raise ValueError(bytes([76,225,187,155,112,32,67,111,109,109,111,100,105,116,121,32,99,104,225,187,137,32,110,104,225,186,173,110,32,103,105,195,161,32,116,114,225,187,139,32,116,104,97,109,32,115,225,187,145,32,115,111,117,114,99,101,32,108,195,160,32,39,83,80,76,39,46]).decode())
		super().__init__(source=A,symbol=None,start=start,end=end,length=length,show_log=show_log)
	@dynamic_method
	def gold_vn(self,start=None,end=None,length=None):'Vietnam gold prices (buy & sell).'
	@dynamic_method
	def gold_global(self,start=None,end=None,length=None):'Global gold price.'
	@dynamic_method
	def gas_vn(self,start=None,end=None,length=None):'Vietnam gasoline & diesel prices.'
	@dynamic_method
	def oil_crude(self,start=None,end=None,length=None):'Crude oil price.'
	@dynamic_method
	def gas_natural(self,start=None,end=None,length=None):'Natural gas price.'
	@dynamic_method
	def coke(self,start=None,end=None,length=None):'Coke price.'
	@dynamic_method
	def steel_d10(self,start=None,end=None,length=None):'Vietnam rebar D10 price.'
	@dynamic_method
	def iron_ore(self,start=None,end=None,length=None):'Iron ore price.'
	@dynamic_method
	def steel_hrc(self,start=None,end=None,length=None):'Hot‑rolled coil (HRC) steel price.'
	@dynamic_method
	def fertilizer_ure(self,start=None,end=None,length=None):'Urea fertilizer price.'
	@dynamic_method
	def soybean(self,start=None,end=None,length=None):'Soybean price.'
	@dynamic_method
	def corn(self,start=None,end=None,length=None):'Corn price.'
	@dynamic_method
	def sugar(self,start=None,end=None,length=None):'Sugar price.'
	@dynamic_method
	def pork_north_vn(self,start=None,end=None,length=None):'Northern Vietnam live hog price.'
	@dynamic_method
	def pork_china(self,start=None,end=None,length=None):'China live hog price.'