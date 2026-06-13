'\nProvider Registry System for vnstock_data.\n\nHệ thống đăng ký cho phép các provider (KBS, VCI, TCBS, MSN, FMP, XNO, ...)\ntự đăng ký để trở thành available data source.\n\nModule này cho phép:\n- Đăng ký provider từ bất kỳ thư mục (explorer/, connector/, ...)\n- Tìm kiếm provider theo provider_type và source name\n- Liệt kê tất cả available providers\n'
from logging import getLogger
logger=getLogger(__name__)
class ProviderRegistry:
	'\n    Registry for vnstock_data data providers.\n    \n    Cho phép registration của các provider class từ các nguồn khác nhau:\n    - vnstock_data.explorer.* (KBS, VCI, TCBS, MSN, ...) - Web scraping\n    - vnstock_data.connector.* (FMP, XNO, Binance, ...) - REST API\n    ';_registry:dict[tuple[str,str],type]={}
	@classmethod
	def register(D,provider_type,source_name,provider_class):"\n        Register a provider class.\n\n        Tham số:\n            provider_type (str): Type của provider\n                                 (quote, company, financial, trading, listing, etc.)\n            source_name (str): Tên nguồn dữ liệu\n                              (kbs, vci, fmp, tcbs, msn, etc.)\n            provider_class (Type): Class của provider\n            \n        Ví dụ:\n            ProviderRegistry.register('quote', 'kbs', KBSQuote)\n            ProviderRegistry.register('company', 'kbs', KBSCompany)\n            ProviderRegistry.register('financial', 'kbs', KBSFinance)\n        ";C=source_name;B=provider_type;A=provider_class;E=B,C.lower();D._registry[E]=A;logger.debug(f"✓ Provider registered: {B}/{C} -> {A.__module__}.{A.__name__}")
	@classmethod
	def get(A,provider_type,source_name):
		'\n        Get a provider class by type and source name.\n        \n        Tham số:\n            provider_type (str): Type của provider (quote, company, etc.)\n            source_name (str): Tên nguồn dữ liệu\n            \n        Returns:\n            Type: Provider class nếu được tìm thấy\n            \n        Raises:\n            ValueError: Nếu provider không được tìm thấy\n        ';C=source_name;B=provider_type;D=B,C.lower()
		if D not in A._registry:E=A.list_available(B);raise ValueError(f"Provider '{B}/{C}' not found. Available: {E}")
		return A._registry[D]
	@classmethod
	def list_available(A,provider_type):'\n        List all available source names cho một provider type.\n        \n        Tham số:\n            provider_type (str): Type của provider\n            \n        Returns:\n            List[str]: Danh sách source names (sắp xếp)\n        ';B=sorted({B for(A,B)in A._registry if A==provider_type});return B
	@classmethod
	def list_all(C):
		'\n        List tất cả registered providers, grouped by type.\n        \n        Returns:\n            Dict[str, List[str]]: {provider_type: [source_names]}\n        ';A={}
		for(B,D)in C._registry:
			if B not in A:A[B]=[]
			A[B].append(D)
		for B in A:A[B].sort()
		return A
	@classmethod
	def is_registered(A,provider_type,source_name):'\n        Check xem provider có được register không.\n        \n        Tham số:\n            provider_type (str): Type của provider\n            source_name (str): Tên nguồn dữ liệu\n            \n        Returns:\n            bool: True nếu provider được register\n        ';B=provider_type,source_name.lower();return B in A._registry
	@classmethod
	def clear(A):'\n        Clear tất cả registered providers. Chủ yếu dùng cho testing.\n        ';A._registry.clear();logger.debug(bytes([82,101,103,105,115,116,114,121,32,99,108,101,97,114,101,100]).decode())
	@classmethod
	def debug_info(D):
		'\n        Get debug info về registry state.\n        \n        Returns:\n            str: Debug info\n        ';A=[];A.append(bytes([61]).decode()*60);A.append(bytes([86,78,83,84,79,67,75,95,68,65,84,65,32,80,82,79,86,73,68,69,82,32,82,69,71,73,83,84,82,89,32,68,69,66,85,71,32,73,78,70,79]).decode());A.append(bytes([61]).decode()*60);B=D.list_all()
		if not B:A.append(bytes([40,82,101,103,105,115,116,114,121,32,101,109,112,116,121,41]).decode())
		else:
			for C in sorted(B.keys()):
				G=B[C];A.append(f"\n[{C}]")
				for E in G:F=D.get(C,E);A.append(f"  • {E:12} -> {F.__module__}.{F.__name__}")
		A.append(bytes([10]).decode()+bytes([61]).decode()*60);return bytes([10]).decode().join(A)