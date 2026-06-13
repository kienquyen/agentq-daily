'\nData Flattener Utility\n======================\n\nFlatten nested raw JSON WebSocket data to flat dictionaries with\nreadable names. Supports field name mapping and customization via\nconfiguration dict.\n'
_J='event_counts'
_I='total_processed'
_H='quantity'
_G='change'
_F='status'
_E='time'
_D='event_type'
_C=None
_B='timestamp'
_A='data'
import json
from typing import Dict,Any
from copy import deepcopy
FIELD_MAPPING={_D:'event',_B:_E,_A:_A,'id':'id','mc':'market','vol':'volume','value':'value',_E:_E,_F:_F,'accVol':'acc_volume','ot':'other','cIndex':'index','oIndex':'open_index','ptVol':'pt_volume','ptValue':'pt_value','fBVol':'foreign_buy_vol','fSVol':'foreign_sell_vol','fBVal':'foreign_buy_val','fSVal':'foreign_sell_val','up':'up','down':'down','ref':'unchanged','hsx_ce':'hsx_ceil','hsx_fl':'hsx_floor','hnx_ce':'hnx_ceil','hnx_fl':'hnx_floor','upcom_ce':'upcom_ceil','upcom_fl':'upcom_floor','vn30_ce':'vn30_ceil','vn30_fl':'vn30_floor','vn100_ce':'vn100_ceil','vn100_fl':'vn100_floor','sym':'symbol','lastPrice':'last_price','lastVol':'last_volume',_G:_G,'changePc':'change_pct','totalVol':'total_volume','hp':'high','lp':'low','ch':'change_flag','lc':'low_flag','ap':'avg_price','ca':'ceiling','sID':'session_id','side':'side','lot':'lot_size','bid':'bid_price','ask':'ask_price','oi':'open_interest','fBVol1':'foreign_buy_vol1','fSVol1':'foreign_sell_vol1','boardId':'board_id','marketId':'market_id','sequence':'seq','hashValue':'hash','transId':'trans_id','vol4':'volume_4','timeServer':'server_time','g1':'level_1','g2':'level_2','g3':'level_3','g4':'level_4','g5':'level_5','g6':'level_6','g7':'level_7','g8':'level_8','g9':'level_9','fSVolume':'foreign_sell_volume','fBValue':'foreign_buy_value','fSValue':'foreign_sell_value','group':'group','buyerID':'buyer_id','sellerID':'seller_id','price':'price',_H:_H,'cl':'color'}
def flatten_raw_data(raw_data,field_mapping=_C):
	'\n    Flatten nested raw WebSocket data to flat dict with readable names.\n    \n    Handles:\n    - Nested data structures\n    - Pipe-delimited fields (e.g., "ot", price levels)\n    - Field name mapping to readable names\n    - Missing fields gracefully\n    \n    Args:\n        raw_data: Raw nested data from WebSocket\n        field_mapping: Custom field mapping dict (uses default if not provided)\n    \n    Returns:\n        Dict with flattened, readable field names\n    ';D=field_mapping;B=raw_data
	if D is _C:D=FIELD_MAPPING
	C={};G=B.get(_D,'unknown');C[_D]=G;A=B.get(_A,B)
	if isinstance(A,dict)and _A in A:A=A[_A]
	if G in['index','stock','stockps','board','boardps']:
		if _A in A:A=A[_A]
	for(E,F)in A.items():
		H=D.get(E,E)
		if E.startswith('g')and isinstance(F,str):_parse_price_level(F,E,C,D)
		else:C[H]=F
	if _B in B:C[_B]=B[_B]
	return C
def _parse_price_level(level_str,level_key,result,field_mapping):
	'\n    Parse price level string "price|volume|direction" into separate fields.\n    \n    Format: "24.75|8280|d"\n    Output (for g1):\n      - level_1_price: 24.75\n      - level_1_volume: 8280\n      - level_1_side: "d"\n    ';E=level_str;C=level_key;A=result
	try:
		B=E.split('|')
		if len(B)>=3:D=C[1:];A[f"level_{D}_price"]=float(B[0]);A[f"level_{D}_volume"]=int(B[1]);A[f"level_{D}_side"]=B[2]
	except(ValueError,IndexError):F=field_mapping.get(C,C);A[F]=E
def flatten_raw_json_file(input_file,output_file,field_mapping=_C,limit=_C):
	'\n    Read raw JSON messages file and flatten to CSV.\n    \n    Args:\n        input_file: Path to raw JSON messages file\n        output_file: Path to output CSV file\n        field_mapping: Custom field mapping\n        limit: Max rows to process (None = all)\n    \n    Returns:\n        Statistics dict with counts\n    ';K=limit;J=output_file;I='message';E=field_mapping;import csv
	if E is _C:E=FIELD_MAPPING
	with open(input_file,'r')as F:M=json.load(F)
	A=[];G={}
	for(N,B)in enumerate(M):
		if K and N>=K:break
		if isinstance(B.get(I),str)and B[I].startswith('42'):
			try:
				O=B[I][2:];C=json.loads(O)
				if isinstance(C,list)and len(C)>=2:H=C[0];P=C[1];Q={_D:H,_A:P,_B:B.get(_B)};R=flatten_raw_data(Q,E);A.append(R);G[H]=G.get(H,0)+1
			except json.JSONDecodeError:continue
	if A:
		D=set()
		for S in A:D.update(S.keys())
		D=sorted(list(D))
		with open(J,'w',newline='')as F:L=csv.DictWriter(F,fieldnames=D);L.writeheader();L.writerows(A)
	return{_I:len(A),_J:G,'output_file':J}
def get_field_mapping():'Get current field mapping configuration.';return deepcopy(FIELD_MAPPING)
def update_field_mapping(custom_mapping):'Update field mapping (modifies global FIELD_MAPPING).';global FIELD_MAPPING;FIELD_MAPPING.update(custom_mapping)
def export_field_mapping_to_json(output_file):
	'Export current field mapping to JSON for reference.'
	with open(output_file,'w')as A:json.dump(FIELD_MAPPING,A,indent=2)
def print_field_mapping_summary():
	'Print summary of all available field mappings.';A='=';print('\n'+A*80);print('FIELD NAME MAPPING CONFIGURATION');print(A*80)
	for(B,C)in sorted(FIELD_MAPPING.items()):
		if B!=C:print(f"  {B:20} → {C}")
	print(A*80+'\n')
if __name__=='__main__':
	import sys
	if len(sys.argv)>1:input_file=sys.argv[1];output_file=sys.argv[2]if len(sys.argv)>2 else'flattened_data.csv';print(f"Flattening {input_file} to {output_file}...");stats=flatten_raw_json_file(input_file,output_file);print(f"✓ Processed: {stats[_I]} messages");print(f"  Event types: {stats[_J]}")
	else:print_field_mapping_summary()