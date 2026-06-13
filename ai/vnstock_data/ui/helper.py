'\nHelper utilities for vnstock_data Unified UI.\nProvides tools to easily explore API structure and documentation.\n'
import inspect
from typing import Any
_DEPRECATED_METHODS={bytes([112,101]).decode(),bytes([112,98]).decode(),bytes([101,118,97,108,117,97,116,105,111,110]).decode(),bytes([103,100,112]).decode(),bytes([99,112,105]).decode(),bytes([105,110,100,117,115,116,114,121,95,112,114,111,100]).decode(),bytes([105,109,112,111,114,116,95,101,120,112,111,114,116]).decode(),bytes([114,101,116,97,105,108]).decode(),bytes([102,100,105]).decode(),bytes([109,111,110,101,121,95,115,117,112,112,108,121]).decode(),bytes([112,111,112,117,108,97,116,105,111,110,95,108,97,98,111,114]).decode(),bytes([101,120,99,104,97,110,103,101,95,114,97,116,101]).decode(),bytes([105,110,116,101,114,101,115,116,95,114,97,116,101]).decode(),bytes([100,101,114,105,118,97,116,105,118,101,115]).decode()}
_BACKWARD_COMPAT_ALIASES={bytes([112,114,105,99,101,95,98,111,97,114,100]).decode(),bytes([104,105,115,116,111,114,121]).decode(),bytes([105,110,116,114,97,100,97,121]).decode(),bytes([112,114,105,99,101,95,100,101,112,116,104]).decode(),bytes([116,114,97,100,105,110,103,95,115,116,97,116,115]).decode(),bytes([112,117,116,95,116,104,114,111,117,103,104]).decode(),bytes([109,97,116,99,104,101,100,95,98,121,95,112,114,105,99,101]).decode(),bytes([98,121,95,103,114,111,117,112]).decode(),bytes([98,121,95,101,120,99,104,97,110,103,101]).decode()}
_MARKET_TOPLEVEL_ENDPOINTS_HIDE={bytes([113,117,111,116,101]).decode()}
def _is_endpoint_method(method):
	'\n    Check if a method is an endpoint (returns data/DataFrame, not a domain object).\n    Endpoints are actual data-returning methods that dispatch to providers,\n    not relay methods that call other layer methods.\n    ';C=method
	try:
		D=None
		try:
			E=inspect.signature(C)
			if E.return_annotation is not inspect.Signature.empty:D=E.return_annotation
		except Exception:pass
		if D:
			B=str(D)
			if bytes([68,97,116,97,70,114,97,109,101]).decode()in B or bytes([83,101,114,105,101,115]).decode()in B or bytes([100,105,99,116]).decode()in B or bytes([108,105,115,116]).decode()in B:
				try:
					A=inspect.getsource(C)
					if bytes([65,110,97,108,121,116,105,99,115,40,41]).decode()in A or bytes([77,97,99,114,111,40,41]).decode()in A or bytes([82,101,102,101,114,101,110,99,101,40,41]).decode()in A:return False
					return True
				except(OSError,TypeError):return True
		try:
			A=inspect.getsource(C)
			if bytes([95,100,105,115,112,97,116,99,104]).decode()in A:return True
		except(OSError,TypeError):pass
		return False
	except(OSError,TypeError):return False
def _should_include_method(name,method,is_macro_layer=False,parent_name=''):
	"Determine if a method should be displayed in the API tree.\n    \n    Args:\n        name: Method name\n        method: Method object\n        is_macro_layer: True if this is the Macro layer\n        parent_name: Parent class/layer name (e.g., 'Market' at top level)\n    ";C=parent_name;B=method;A=name
	if A.startswith(bytes([95]).decode()):return False
	if not callable(B)and not isinstance(B,property):return False
	if A in _BACKWARD_COMPAT_ALIASES:return False
	if A in _DEPRECATED_METHODS:
		if is_macro_layer or A==bytes([100,101,114,105,118,97,116,105,118,101,115]).decode()and C==bytes([82,101,102,101,114,101,110,99,101]).decode():return False
	if C==bytes([77,97,114,107,101,116]).decode()and A in _MARKET_TOPLEVEL_ENDPOINTS_HIDE:return False
	return True
def _get_public_methods(obj,include_intermediate=False,parent_name=''):
	"\n    Helper to extract public callable methods from an object, excluding dunders and unwanted methods.\n    \n    Args:\n        obj: Object to extract methods from\n        include_intermediate: If True, include navigation methods (returns domain objects).\n                            If False, only include endpoint methods (returns data).\n        parent_name: Parent class name for context-aware filtering (e.g., 'Market')\n    ";B=[];D=type(obj).__name__;E=D==bytes([77,97,99,114,111]).decode()
	for(C,A)in inspect.getmembers(obj,predicate=inspect.ismethod):
		if not _should_include_method(C,A,E,parent_name):continue
		if not include_intermediate:
			if not _is_endpoint_method(A):continue
		B.append((C,A))
	return B
def show_doc(obj):
	"\n    Prints the complete docstring and signature of a function or class.\n    \n    Args:\n        obj: Function, method, class or its name as string (e.g., 'Market', 'Reference').\n             When using strings, the object will be automatically resolved from vnstock_data UI.\n    ";B=obj
	if isinstance(B,str):
		try:
			from vnstock_data import ui;L=B.replace(bytes([40,41]).decode(),'').strip();G=L.split(bytes([46]).decode())
			if hasattr(ui,G[0]):
				H=getattr(ui,G[0]);E=H()if inspect.isclass(H)else H;I=True
				for D in G[1:]:
					if hasattr(E,D):
						F=getattr(E,D)
						if inspect.ismethod(F)or inspect.isfunction(F):
							J=inspect.signature(F);C={}
							for A in J.parameters.values():
								if A.default==inspect.Parameter.empty and A.name!=bytes([115,101,108,102]).decode():
									if A.name==bytes([115,121,109,98,111,108]).decode():
										if bytes([99,114,121,112,116,111]).decode()in D:C[A.name]=bytes([66,84,67]).decode()
										elif bytes([102,111,114,101,120]).decode()in D:C[A.name]=bytes([85,83,68,86,78,68]).decode()
										elif bytes([99,111,109,109,111,100,105,116,121]).decode()in D:C[A.name]=bytes([71,67,61,70]).decode()
										elif bytes([105,110,100,101,120]).decode()in D:C[A.name]=bytes([86,78,73,78,68,69,88]).decode()
										else:C[A.name]=bytes([86,73,67]).decode()
									elif A.name==bytes([105,110,100,101,120]).decode():C[A.name]=bytes([86,78,73,78,68,69,88]).decode()
									else:C[A.name]=None
							try:E=F(**C)
							except Exception:I=False;break
						else:E=F
					else:I=False;break
				if I:B=E
		except Exception:pass
	if isinstance(B,str):print(f"Could not resolve documentation for: '{B}'");print(bytes([84,105,112,58,32,85,115,101,32,116,104,101,32,111,98,106,101,99,116,32,100,105,114,101,99,116,108,121,32,40,105,102,32,105,109,112,111,114,116,101,100,41,32,111,114,32,105,116,115,32,110,97,109,101,32,97,115,32,97,32,115,116,114,105,110,103,32,40,101,46,103,46,44,32,115,104,111,119,95,100,111,99,40,39,77,97,114,107,101,116,39,41,41,46]).decode());return
	try:J=inspect.signature(B);print(f"Signature: [92m{B.__name__}{J}[0m\n")
	except(ValueError,TypeError,AttributeError):pass
	K=inspect.getdoc(B)
	if K:print(K)
	else:M=getattr(B,bytes([95,95,110,97,109,101,95,95]).decode(),type(B).__name__);print(f"No documentation available for {M}.")
def show_api(layer=None,show_navigation=True):
	"\n    Displays a visual API Tree of available endpoints.\n    Only shows endpoint methods (returning data), hiding backward compatible aliases.\n    \n    Args:\n        layer: (Optional) Limit display to a specific Layer (e.g., Market(), 'Market'). \n               If empty (None), displays all 6 library layers.\n        show_navigation: If True, displays intermediate navigation methods (returning domain objects).\n                        Default is True.\n    ";H=show_navigation;E=layer;G=''
	if isinstance(E,str):
		try:
			from vnstock_data import ui;L=E.replace(bytes([40,41]).decode(),'').strip();I=L.split(bytes([46]).decode())
			if hasattr(ui,I[0]):
				J=getattr(ui,I[0])
				if inspect.isclass(J):B=J()
				else:B=J
				K=True
				for D in I[1:]:
					if hasattr(B,D):
						F=getattr(B,D)
						if inspect.ismethod(F)or inspect.isfunction(F):
							O=inspect.signature(F);C={}
							for A in O.parameters.values():
								if A.default==inspect.Parameter.empty and A.name!=bytes([115,101,108,102]).decode():
									if A.name==bytes([115,121,109,98,111,108]).decode():
										if bytes([99,114,121,112,116,111]).decode()in D:C[A.name]=bytes([66,84,67]).decode()
										elif bytes([102,111,114,101,120]).decode()in D:C[A.name]=bytes([85,83,68,86,78,68]).decode()
										elif bytes([99,111,109,109,111,100,105,116,121]).decode()in D:C[A.name]=bytes([71,67,61,70]).decode()
										elif bytes([105,110,100,101,120]).decode()in D:C[A.name]=bytes([86,78,73,78,68,69,88]).decode()
										else:C[A.name]=bytes([86,73,67]).decode()
									elif A.name==bytes([105,110,100,101,120]).decode():C[A.name]=bytes([86,78,73,78,68,69,88]).decode()
									else:C[A.name]=None
							try:B=F(**C)
							except Exception:K=False;break
						else:B=F
					else:K=False;break
				if K:E=B;G=L
		except Exception:pass
	def e(method):
		'Check if method returns a domain object (navigation, not data).'
		try:
			A=None
			try:
				C=inspect.signature(method)
				if C.return_annotation is not inspect.Signature.empty:A=C.return_annotation
			except Exception:pass
			if A:
				if isinstance(A,str):
					D=bytes([77,97,114,107,101,116]).decode(),bytes([82,101,102,101,114,101,110,99,101]).decode(),bytes([73,110,115,105,103,104,116,115]).decode(),bytes([70,117,110,100,97,109,101,110,116,97,108]).decode(),bytes([77,97,99,114,111]).decode(),bytes([65,110,97,108,121,116,105,99,115]).decode()
					if any(B in A for B in D):return True
					return False
				B=str(A)
				if bytes([68,97,116,97,70,114,97,109,101]).decode()not in B and bytes([83,101,114,105,101,115]).decode()not in B and bytes([100,105,99,116]).decode()not in B and bytes([108,105,115,116]).decode()not in B:
					try:
						if A.__module__!=bytes([98,117,105,108,116,105,110,115]).decode():return True
					except AttributeError:pass
			return False
		except(AttributeError,TypeError):return False
	def M(node,prefix='',is_last=True,title='',level=0,show_nav=False,parent_name='',title_suffix=''):
		W=show_nav;V=level;R=is_last;Q=prefix;B=node
		if not hasattr(B,bytes([95,95,99,108,97,115,115,95,95]).decode())or type(B).__module__.split(bytes([46]).decode())[0]not in(bytes([118,110,115,116,111,99,107,95,100,97,116,97]).decode(),bytes([95,95,109,97,105,110,95,95]).decode()):return
		f=bytes([226,148,148,226,148,128,226,148,128,32]).decode()if R else bytes([226,148,156,226,148,128,226,148,128,32]).decode();g=title or(B.__name__ if hasattr(B,bytes([95,95,110,97,109,101,95,95]).decode())else type(B).__name__);X=type(B).__name__==bytes([77,97,99,114,111]).decode();S=parent_name or type(B).__name__;print(f"{Q}{f}[96m{g}[0m{title_suffix}")
		if hasattr(B,bytes([95,95,99,108,97,115,115,95,95]).decode())and not inspect.isroutine(B):
			Y=_get_public_methods(B,include_intermediate=False,parent_name=S)
			for(T,(A,F))in enumerate(Y):
				G=T==len(Y)-1 if not W else False;H=Q+(bytes([32,32,32,32]).decode()if R else bytes([226,148,130,32,32,32]).decode());Z=''
				try:
					N=F.__annotations__.get(bytes([114,101,116,117,114,110]).decode())
					if N:
						if hasattr(N,bytes([95,95,110,97,109,101,95,95]).decode()):J=N.__name__
						else:
							J=str(N).replace(bytes([116,121,112,105,110,103,46]).decode(),'').replace(bytes([112,97,110,100,97,115,46,99,111,114,101,46,102,114,97,109,101,46]).decode(),'').replace(bytes([112,97,110,100,97,115,46,99,111,114,101,46,115,101,114,105,101,115,46]).decode(),'')
							if bytes([79,112,116,105,111,110,97,108]).decode()in J:J=J.replace(bytes([79,112,116,105,111,110,97,108,91]).decode(),'').replace(bytes([93]).decode(),'')+bytes([32,124,32,78,111,110,101]).decode()
						Z=f" -> [90m{J}[0m"
				except Exception:pass
				a=''
				try:
					if hasattr(B,bytes([95,100,111,109,97,105,110,95,110,97,109,101]).decode())and hasattr(B,bytes([95,115,111,117,114,99,101,115,95,99,111,110,102,105,103]).decode()):from vnstock_data.ui.config import get_route as h;i=h(B._domain_name,A,B._sources_config);a=f" [93m[{i[0].upper()}][0m"
				except Exception:pass
				b='';I=inspect.getdoc(F)
				if I:
					D=I.split(bytes([10]).decode())[0].strip()
					if len(D)>100:D=D[:97]+bytes([46,46,46]).decode()
					b=f" [90m# {D}[0m"
				K=bytes([226,148,148,226,148,128,226,148,128,32]).decode()if G else bytes([226,148,156,226,148,128,226,148,128,32]).decode();print(f"{H}{K}[92m{A}()[0m{a}{Z}{b}")
			if W:
				L=[]
				for(A,F)in inspect.getmembers(B,predicate=inspect.ismethod):
					if not _should_include_method(A,F,is_macro_layer=X,parent_name=S):continue
					if e(F):L.append((A,F,bytes([109,101,116,104,111,100]).decode()))
				for(A,c)in inspect.getmembers(type(B)):
					if isinstance(c,property):
						if not _should_include_method(A,c,is_macro_layer=X,parent_name=S):continue
						try:
							U=getattr(B,A)
							if U is not None and type(U).__module__.startswith(bytes([118,110,115,116,111,99,107,95,100,97,116,97]).decode()):L.append((A,U,bytes([112,114,111,112,101,114,116,121]).decode()))
						except Exception:pass
				L.sort(key=lambda x:x[0])
				for(T,(A,O,d))in enumerate(L):
					G=T==len(L)-1;H=Q+(bytes([32,32,32,32]).decode()if R else bytes([226,148,130,32,32,32]).decode());P=''
					if d==bytes([109,101,116,104,111,100]).decode():I=inspect.getdoc(O)
					else:j=getattr(type(B),A);I=inspect.getdoc(j)
					if I:
						D=I.split(bytes([10]).decode())[0].strip()
						if len(D)>100:D=D[:97]+bytes([46,46,46]).decode()
						P=f" [90m# {D}[0m"
					if d==bytes([112,114,111,112,101,114,116,121]).decode():M(O,H,G,A,V+1,show_nav=True,parent_name='',title_suffix=P)
					else:
						try:
							k=inspect.signature(O);E={}
							for C in k.parameters.values():
								if C.default==inspect.Parameter.empty and C.name!=bytes([115,101,108,102]).decode():
									if C.name==bytes([115,121,109,98,111,108]).decode():
										if bytes([99,114,121,112,116,111]).decode()in A:E[C.name]=bytes([66,84,67]).decode()
										elif bytes([102,111,114,101,120]).decode()in A:E[C.name]=bytes([85,83,68,86,78,68]).decode()
										elif bytes([99,111,109,109,111,100,105,116,121]).decode()in A:E[C.name]=bytes([71,67,61,70]).decode()
										elif bytes([105,110,100,101,120]).decode()in A:E[C.name]=bytes([86,78,73,78,68,69,88]).decode()
										else:E[C.name]=bytes([86,73,67]).decode()
									elif C.name==bytes([105,110,100,101,120]).decode():E[C.name]=bytes([86,78,73,78,68,69,88]).decode()
									else:E[C.name]=None
							l=O(**E);M(l,H,G,A+bytes([40,41]).decode(),V+1,show_nav=True,parent_name='',title_suffix=P)
						except Exception:K=bytes([226,148,148,226,148,128,226,148,128,32]).decode()if G else bytes([226,148,156,226,148,128,226,148,128,32]).decode();print(f"{H}{K}[94m{A}()[0m{P}")
						except Exception:K=bytes([226,148,148,226,148,128,226,148,128,32]).decode()if G else bytes([226,148,156,226,148,128,226,148,128,32]).decode();print(f"{H}{K}[94m{A}()  [Navigation][0m")
	if E is not None:P=f" - {G}"if G else'';print(f"\n[1mAPI STRUCTURE TREE{P}[0m");M(E,'',True,G,0,show_nav=H)
	else:
		from vnstock_data.ui import Analytics as Q,Fundamental as R,Insights as S,Macro,Market as T,Reference as U;print(bytes([10,27,91,49,109,65,80,73,32,83,84,82,85,67,84,85,82,69,32,84,82,69,69,32,45,32,86,78,83,84,79,67,75,95,68,65,84,65,32,40,85,110,105,102,105,101,100,32,85,73,32,69,110,100,112,111,105,110,116,115,41,27,91,48,109]).decode());print(bytes([118,110,115,116,111,99,107,95,100,97,116,97]).decode());N=[(bytes([82,101,102,101,114,101,110,99,101]).decode(),U()),(bytes([77,97,114,107,101,116]).decode(),T()),(bytes([70,117,110,100,97,109,101,110,116,97,108]).decode(),R()),(bytes([65,110,97,108,121,116,105,99,115]).decode(),Q()),(bytes([77,97,99,114,111]).decode(),Macro()),(bytes([73,110,115,105,103,104,116,115]).decode(),S())]
		for(V,(W,B))in enumerate(N):X=V==len(N)-1;M(B,'',X,W,0,show_nav=H)
	if H:print(bytes([10,27,91,57,48,109,84,105,112,58,32,83,225,187,173,32,100,225,187,165,110,103,32,115,104,111,119,95,100,111,99,40,110,111,100,101,41,32,196,145,225,187,131,32,196,145,225,187,141,99,32,100,111,99,115,116,114,105,110,103,46,27,91,48,109]).decode());print(bytes([27,91,57,48,109,91,78,97,118,105,103,97,116,105,111,110,93,32,61,32,73,110,116,101,114,109,101,100,105,97,116,101,32,109,101,116,104,111,100,115,32,114,101,116,117,114,110,105,110,103,32,100,111,109,97,105,110,32,111,98,106,101,99,116,115,27,91,48,109,10]).decode())
	else:print(bytes([10,27,91,57,48,109,84,105,112,58,32,83,225,187,173,32,100,225,187,165,110,103,32,115,104,111,119,95,100,111,99,40,110,111,100,101,41,32,196,145,225,187,131,32,196,145,225,187,141,99,32,100,111,99,115,116,114,105,110,103,46,27,91,48,109]).decode());print(bytes([27,91,57,48,109,72,105,110,116,58,32,115,104,111,119,95,97,112,105,40,41,32,196,145,225,187,131,32,104,105,225,187,131,110,32,116,104,225,187,139,32,99,195,162,121,32,196,145,225,186,167,121,32,196,145,225,187,167,32,118,225,187,155,105,32,110,97,118,105,103,97,116,105,111,110,32,109,101,116,104,111,100,115,46,27,91,48,109,10]).decode())