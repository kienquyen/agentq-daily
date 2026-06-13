'\nConstants for VPS WebSocket Stream\n==================================\n\nThis module defines constants used throughout the streaming package,\nincluding available data types and their descriptions.\n'
_N='psfsell'
_M='spt'
_L='soddlot'
_K='aggregateforeignmarket'
_J='aggregateforeigngroup'
_I='aggregateetf'
_H='aggregatecw'
_G='aggregateps'
_F='boardps'
_E='board'
_D='stock'
_C='aggregatemarket'
_B='stockps'
_A='index'
AVAILABLE_DATA_TYPES={_A:'Index data (VN-Index, VN30, HNX-Index, etc.)',_C:'Aggregate market statistics (volume, value, advances, declines)',_G:'Aggregate derivatives statistics',_H:'Aggregate covered warrant statistics',_I:'Aggregate ETF statistics',_D:'Individual stock price data',_B:'Stock price-size data (including derivatives)',_E:'Order book depth data (HOSE equities)',_F:'Order book depth data (derivatives)',_L:'Odd-lot trading data',_J:'Foreign trading by proprietary groups',_K:'Foreign trading by market',_M:'Special/Put-through transactions',_N:'Proprietary securities firm sell data','regs':'Registration/subscription responses'}
DATA_TYPE_GROUPS={'market':[_A,_C,_G,_H,_I],'stocks':[_D,_B,_E,_F],'foreign':[_J,_K],'transactions':[_M,_L],'all':list(AVAILABLE_DATA_TYPES.keys())}
ESSENTIAL_DATA_TYPES=[_D,_B,_E,_A,_C]
USE_CASE_DATA_TYPES={'basic_monitoring':[_D,_B,_A],'orderbook_analysis':[_E,_F],'foreign_flow':[_J,_K],'market_overview':[_A,_C,_H,_I],'derivatives':[_B,_F,_G]}
def get_data_type_description(data_type):'\n    Get description for a specific data type.\n    \n    Args:\n        data_type: The data type to get description for\n        \n    Returns:\n        Description string, or "Unknown data type" if not found\n    ';return AVAILABLE_DATA_TYPES.get(data_type,'Unknown data type')
def validate_data_types(data_types):
	'\n    Validate a list of data types.\n    \n    Args:\n        data_types: List of data type strings to validate\n        \n    Returns:\n        Tuple of (valid_types, invalid_types)\n    ';B=data_types
	if not B:return[],[]
	C=[];D=[]
	for A in B:
		if A in AVAILABLE_DATA_TYPES:C.append(A)
		else:D.append(A)
	return C,D
def print_available_data_types():
	'Print all available data types with descriptions.';D='-';A='=';print('\n'+A*70);print('AVAILABLE DATA TYPES');print(A*70+'\n');G={'Market-Level Data':[_A,_C,_G,_H,_I],'Stock/Security Data':[_D,_B,_E,_F,_L],'Foreign Trading':[_J,_K],'Special Transactions':[_M,_N],'System Events':['regs']}
	for(H,B)in G.items():
		print(f"📊 {H}");print(D*70)
		for C in B:
			if C in AVAILABLE_DATA_TYPES:print(f"  • {C:30s} - {AVAILABLE_DATA_TYPES[C]}")
		print()
	print(A*70);print('\nPre-defined Groups:');print(D*70)
	for(E,F)in DATA_TYPE_GROUPS.items():
		if E!='all':I=', '.join(F[:3]);J=' ...'if len(F)>3 else'';print(f"  --group {E:15s} → {I}{J}")
	print();print(A*70);print('\nCommon Use Cases:');print(D*70)
	for(K,B)in USE_CASE_DATA_TYPES.items():L=', '.join(B);print(f"  {K:20s} → {L}")
	print()
def expand_data_type_group(group_or_types):
	'\n    Expand data type groups to individual types.\n    \n    Args:\n        group_or_types: List that may contain group names or individual types\n        \n    Returns:\n        List of individual data types (expanded from groups)\n    ';A=[]
	for B in group_or_types:
		if B in DATA_TYPE_GROUPS:A.extend(DATA_TYPE_GROUPS[B])
		else:A.append(B)
	D=set();E=[]
	for C in A:
		if C not in D:D.add(C);E.append(C)
	return E