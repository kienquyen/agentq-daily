from vnstock_data.base import BaseAdapter,dynamic_method
class Market(BaseAdapter):
	_module_name=bytes([109,97,114,107,101,116]).decode();SUPPORTED_SOURCES=[bytes([118,110,100]).decode()]
	def __init__(C,source=bytes([118,110,100]).decode(),**D):
		A=source;B=A.lower()
		if B not in C.SUPPORTED_SOURCES:raise ValueError(bytes([76,225,187,155,112,32,77,97,114,107,101,116,32,99,104,225,187,137,32,110,104,225,186,173,110,32,103,105,195,161,32,116,114,225,187,139,32,116,104,97,109,32,115,225,187,145,32,115,111,117,114,99,101,32,108,195,160,32,39,86,78,68,39,46,32]).decode()+bytes([78,104,198,176,110,103,32,110,104,225,186,173,110,32,196,145,198,176,225,187,163,99,32,39]).decode()+A+bytes([39,46]).decode())
		super().__init__(source=B,**D)
	@dynamic_method
	def pe(self,duration=bytes([53,89]).decode()):'\n        Retrieves P/E ratio data for the given duration.\n        '
	@dynamic_method
	def pb(self,duration=bytes([53,89]).decode()):'\n        Retrieves P/B ratio data for the given duration.\n        '
	@dynamic_method
	def evaluation(self,duration=bytes([53,89]).decode()):'\n        Retrieves combined P/E and P/B data for the given duration.\n        '