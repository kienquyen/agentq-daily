'\nCore standardization logic for UI Reference Layer.\n'
from typing import Any
_SCHEMA_REGISTRY={}
_STANDARD_COLS_REGISTRY={}
_ENUM_REGISTRY={}
def register_schemas(schema_map,standard_cols,enum_map=None):
	'Register schema maps, standard columns, and optional enum value maps.';A=enum_map;_SCHEMA_REGISTRY.update(schema_map);_STANDARD_COLS_REGISTRY.update(standard_cols)
	if A:_ENUM_REGISTRY.update(A)
def standardize_columns(df,domain_method,source,strict=False,filter_unmapped=False):
	"\n    Standardize dataframe columns based on registered native schema mappings.\n    \n    Args:\n        df: Pandas DataFrame from provider.\n        domain_method: Key representing the domain method (e.g., 'company.profile').\n        source: Provider source (e.g., 'vci').\n        strict: If True, filters out any columns not part of the standard schema.\n        filter_unmapped: If True, filters out columns that aren't natively mapped or standard.\n    ";C=domain_method;A=df;import unicodedata as D,pandas as E
	if not isinstance(A,E.DataFrame):return A
	if A.empty:return A
	J=_SCHEMA_REGISTRY.get(C,{}).get(source)
	if J:
		F={D.normalize(bytes([78,70,67]).decode(),str(A)):B for(A,B)in J.items()};M={A:F[D.normalize(bytes([78,70,67]).decode(),str(A))]for A in A.columns if D.normalize(bytes([78,70,67]).decode(),str(A))in F};A=A.rename(columns=M)
		if any(A.columns.duplicated()):
			K=[]
			for L in range(len(A.columns)):
				N=A.columns[L];G=A.iloc[:,L]
				if N not in[bytes([116,105,99,107,101,114]).decode(),bytes([112,101,114,105,111,100]).decode()]:G=E.to_numeric(G,errors=bytes([99,111,101,114,99,101]).decode())
				K.append(G)
			A=E.concat(K,axis=1);A=A.T.groupby(level=0).sum(min_count=1).T
		if filter_unmapped:B=_STANDARD_COLS_REGISTRY.get(C,[]);O=list(F.values());H=[A for A in A.columns if A in O or A in B];A=A[H]
	if strict:
		B=_STANDARD_COLS_REGISTRY.get(C,[])
		if B:H=[B for B in B if B in A.columns];A=A[H]
	for(I,P)in _ENUM_REGISTRY.items():
		if I in A.columns:A[I]=A[I].replace(P)
	return A