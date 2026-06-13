'\nBase classes for UI domains and details.\n'
import pandas as pd
from vnstock_data.core.registry import ProviderRegistry
class BaseDomain:
	'\n    Abstract base class for domain objects (e.g., Equity, Industry).\n    Handles dispatching calls to the registered data provider.\n    '
	def __init__(A,domain_name,layer_sources):A._domain_name=domain_name;A._sources_config=layer_sources
	def _dispatch(D,method_name,**E):
		'\n        Dispatches a method call to the underlying provider.\n        ';I=method_name;from vnstock_data.ui.config import get_route as M;A,B,N,F=M(D._domain_name,I,D._sources_config)
		if not ProviderRegistry.is_registered(B,A):
			import importlib as O
			try:O.import_module(f"vnstock_data.explorer.{A}.{B}")
			except ImportError:pass
		C=ProviderRegistry.get(B,A)
		if not C:C=ProviderRegistry.get(B,A)
		if not C:raise ValueError(f"Provider not found for {A}.{B}")
		try:G=C()
		except TypeError:G=C()
		if not hasattr(G,F):raise AttributeError(f"Provider {N} has no method {F}")
		J=getattr(G,F);import inspect as K;P=K.signature(J);L=P.parameters;Q=any(A.kind==K.Parameter.VAR_KEYWORD for A in L.values())
		if not Q:E={A:B for(A,B)in E.items()if A in L}
		H=J(**E);R=f"{D._domain_name}.{I}";from vnstock_data.ui.schemas import standardize_columns as S;H=S(H,R,A,strict=True);return H
class BaseDetail:
	'\n    Abstract base class for symbol-specific detailed views (e.g., Company Profile).\n    '
	def __init__(A,symbol,domain_name,layer_sources,**B):A.symbol=symbol;A._domain_name=domain_name;A._sources_config=layer_sources;A._kwargs=B
	def _dispatch(A,method_name,**F):
		'\n        Dispatches a method call to the underlying provider for a specific symbol.\n        ';I=method_name;from vnstock_data.ui.config import get_route as M;B,C,N,G=M(A._domain_name,I,A._sources_config)
		if not ProviderRegistry.is_registered(C,B):
			import importlib as O
			try:O.import_module(f"vnstock_data.explorer.{B}.{C}")
			except ImportError:pass
		D=ProviderRegistry.get(C,B)
		if not D:raise ValueError(f"Provider not found for {B}.{C}")
		try:E=D(symbol=A.symbol,**A._kwargs)
		except TypeError:
			try:E=D(symbol=A.symbol)
			except TypeError:E=D(A.symbol)
		if not hasattr(E,G):raise AttributeError(f"Provider {N} has no method {G}")
		J=getattr(E,G);import inspect as K;P=K.signature(J);L=P.parameters;Q=any(A.kind==K.Parameter.VAR_KEYWORD for A in L.values())
		if not Q:F={A:B for(A,B)in F.items()if A in L}
		H=J(**F);R=f"{A._domain_name}.{I}";from vnstock_data.ui.schemas import standardize_columns as S;H=S(H,R,B,strict=True);return H