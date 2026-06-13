'\nVPS Data Source\n=============\n\nWebSocket client implementation for the VPS market data source with session management.\n'
_AB='net_value'
_AA='net_volume'
_A9='sell_value'
_A8='buy_value'
_A7='sell_volume'
_A6='buy_volume'
_A5='foreign_net_volume'
_A4='foreign_sell_volume'
_A3='foreign_buy_volume'
_A2='timeServer'
_A1='tradingSession'
_A0='time_server'
_z='trading_session'
_y='open_price'
_x='totalVol'
_w='changePc'
_v='lastVol'
_u='session_id'
_t='ceiling_actual'
_s='average_price'
_r='low_flag'
_q='change_flag'
_p='low_price'
_o='high_price'
_n='change_percent'
_m='event_type'
_l='ref'
_k='down'
_j='total_value'
_i='boardId'
_h='color'
_g='board_id'
_f='openPrice'
_e='lastPrice'
_d='last_volume'
_c='last_price'
_b='volume'
_a='market_code'
_Z='index'
_Y='lot'
_X='marketId'
_W='unchanged'
_V='declines'
_U='advances'
_T='vol'
_S='time'
_R='market_id'
_Q='total_volume'
_P='transId'
_O='hashValue'
_N='trans_id'
_M='hash_value'
_L='fSVol'
_K='stock_id'
_J='symbol'
_I='sym'
_H='value'
_G='change'
_F='fBVol'
_E='side'
_D='id'
_C='sequence'
_B='data'
_A=None
import json,time,logging,traceback,asyncio
from typing import Dict,Any,List,Optional,Set
from vnstock_pipeline.stream.client import BaseWebSocketClient
from vnstock_pipeline.stream.parsers import FinancialDataParser
from vnstock_pipeline.stream.utils.session_manager import SessionManager
class WSSDataParser(FinancialDataParser):
	'Parser for VPS market data with comprehensive event type support.'
	def parse_data(C,raw_data):
		'\n        Parse and normalize VPS market data with support for all event types.\n        \n        Args:\n            raw_data (Dict[str, Any]): The raw data from VPS\n            \n        Returns:\n            Dict[str, Any]: The parsed and normalized data\n        ';E=raw_data;A=super().parse_data(E);D=E.get(_m,'');B=E.get(_B,{})
		if D==_Z:C._parse_index_data(B.get(_B,{}),A)
		elif D=='stock':C._parse_stock_data(B.get(_B,{}),A)
		elif D=='stockps':C._parse_stockps_data(B,A)
		elif D=='soddlot':C._parse_soddlot_data(B.get(_B,{}),A)
		elif D=='board':C._parse_board_data(B.get(_B,{}),A)
		elif D=='boardps':C._parse_boardps_data(B,A)
		elif D=='aggregatemarket':C._parse_aggregate_market_data(B,A)
		elif D=='aggregateps':C._parse_aggregate_ps_data(B,A)
		elif D=='aggregatecw':C._parse_aggregate_cw_data(B,A)
		elif D=='aggregateetf':C._parse_aggregate_etf_data(B,A)
		elif D=='aggregateforeigngroup':C._parse_aggregate_foreign_group_data(B,A)
		elif D=='aggregateforeignmarket':C._parse_aggregate_foreign_market_data(B,A)
		elif D=='spt':C._parse_spt_data(B,A)
		elif D=='psfsell':C._parse_psfsell_data(B,A)
		elif D=='regs':C._parse_regs_data(B,A)
		else:A.update({'raw_data':B})
		return A
	def _parse_index_data(F,index_data,result):
		'Parse index data\n        \n        VPS sends index data:\n        {\n            "id": 1101,\n            "sequence": 7818,\n            "sourceMsgType": "M1",\n            "hashValue": "38",\n            "transId": "STO:M1:7818:1101",\n            "mc": "38",\n            "vol": 39961395,\n            "value": 924534.913,\n            "time": "10:05:05",\n            "status": "O",\n            "accVol": 17900,\n            "ot": "30.43|1.43%|924534.913|21|14|2",\n            "cIndex": 2092.96,\n            "oIndex": 2123.39\n        }\n        ';G='status';E=result;D='oIndex';C='cIndex';A=index_data;E.update({'index_id':A.get(_D),_a:A.get('mc'),_C:A.get(_C),_M:A.get(_O),_N:A.get(_P),'current_index':A.get(C),'open_index':A.get(D),_G:_A if not A.get(C)or not A.get(D)else A.get(C)-A.get(D),'percent_change':F.calculate_percent_change(A.get(C),A.get(D)),_b:A.get(_T),_H:A.get(_H),G:A.get(G),'acc_vol':A.get('accVol'),_S:A.get(_S)})
		if'ot'in A:
			try:
				B=A['ot'].split('|')
				if len(B)>=6:E.update({'abs_change':float(B[0])if B[0]else _A,'percent_change_text':B[1]if B[1]else _A,'value_ot':float(B[2])if B[2]else _A,_U:int(B[3])if B[3]else _A,_V:int(B[4])if B[4]else _A,_W:int(B[5])if B[5]else _A})
			except Exception as H:F.logger.warning(f"Failed to parse ot field: {H}")
		return E
	def _parse_stock_data(C,stock_data,result):
		'Parse stock data';B=result;A=stock_data;B.update({_J:A.get(_I),_K:A.get(_D),_c:A.get(_e),_d:A.get(_v),_G:A.get(_G),_n:A.get(_w),_Q:A.get(_x),_o:A.get('hp'),_p:A.get('lp'),_q:A.get('ch'),_r:A.get('lc'),_s:A.get('ap'),_t:A.get('ca'),_u:A.get('sID'),_E:A.get(_E)})
		if _f in A:B[_y]=A.get(_f)
		return B
	def _parse_stockps_data(B,data,result):
		'Parse stockps (stock price size) data\n        \n        VPS sends 2 types of stockps:\n        \n        Type 1 - Symbol data (derivatives/stocks):\n        {\n            "data": {\n                "id": 3220,\n                "sym": "41I1FB000",\n                "lastPrice": 1934,\n                "lastVol": 3,\n                "change": "13.00",\n                "totalVol": 60524,\n                ...\n            }\n        }\n        \n        Type 2 - Index/ALGO data:\n        {\n            "data": {\n                "cmd": "ALGO.VN30",\n                "date": "30/10/2025 10:10:46",\n                "index": 1932.62,\n                "change": -17.14,\n                "calculate": -17.09,\n                "ff": 0,\n                "id": 8888\n            }\n        }\n        ';G='calculate';F='date';E='cmd';D=result;C=data
		if isinstance(C,dict)and _B in C:A=C.get(_B,{})
		else:A=C
		if E in A:D.update({'command':A.get(E),F:A.get(F),_Z:A.get(_Z),_G:B._safe_convert(A.get(_G),float),G:B._safe_convert(A.get(G),float),'ff':A.get('ff'),_K:A.get(_D)})
		else:D.update({_J:A.get(_I),_K:A.get(_D),_g:A.get(_i),_R:A.get(_X),_C:A.get(_C),_M:A.get(_O),_N:A.get(_P),_z:A.get(_A1),_c:A.get(_e),_d:A.get(_v),_h:A.get('cl'),_G:B._safe_convert(A.get(_G),float),_n:B._safe_convert(A.get(_w),float),_Q:A.get(_x),_S:A.get(_S),_o:A.get('hp'),_q:A.get('ch'),_p:A.get('lp'),_r:A.get('lc'),_s:A.get('ap'),_t:A.get('ca'),_A0:A.get(_A2),'level':A.get('lv'),_y:A.get(_f),_E:A.get(_E),_u:A.get('sID')})
		return D
	def _parse_soddlot_data(D,data,result):
		'Parse soddlot data\n        \n        VPS sends soddlot with nested structure:\n        {\n            "data": {\n                "id": 9100,\n                "marketId": "G4",\n                "sequence": 721918,\n                "hashValue": "GEX",\n                "transId": "STO:VN000000GEX5:X:721918:9100",\n                "c": 54.4,\n                "f": 47.35,\n                "r": 50.9,\n                "sym": "GEX",\n                "mc": "10",\n                "lastPrice": 49.65,\n                "lastVolume": 4,\n                "lot": 0,\n                "bp1": 49.65,\n                ...\n            }\n        }\n        ';C=result;B=data
		if isinstance(B,dict)and _B in B:A=B.get(_B,{})
		else:A=B
		C.update({_J:A.get(_I),_K:A.get(_D),_R:A.get(_X),_C:A.get(_C),_M:A.get(_O),_N:A.get(_P),'ceiling_price':A.get('c'),'floor_price':A.get('f'),'reference_price':A.get('r'),_c:A.get(_e),_d:A.get('lastVolume'),_Y:A.get(_Y),_a:A.get('mc'),'bid_price_1':A.get('bp1'),'bid_volume_1':A.get('bv1'),'bid_price_2':A.get('bp2'),'bid_volume_2':A.get('bv2'),'bid_price_3':A.get('bp3'),'bid_volume_3':A.get('bv3'),'ask_price_1':A.get('sp1'),'ask_volume_1':A.get('sv1'),'ask_price_2':A.get('sp2'),'ask_volume_2':A.get('sv2'),'ask_price_3':A.get('sp3'),'ask_volume_3':A.get('sv3')});return C
	def _parse_board_data(H,board_data,result):
		'Parse board data with g1, g2, g3 fields\n        \n        VPS sends board data:\n        {\n            "id": 3210,\n            "boardId": "G1",\n            "marketId": "STO",\n            "sequence": 690238,\n            "hashValue": "FPT",\n            "transId": "STO:VN000000FPT1:X:690238:3210",\n            "sym": "FPT",\n            "side": "S",\n            "g1": "102.3|2470|i",\n            "g2": "102.4|4100|i",\n            "g3": "102.5|6290|i",\n            "vol4": 0,\n            "timeServer": "10:07:19"\n        }\n        ';D=result;A=board_data;D.update({_J:A.get(_I),_K:A.get(_D),_g:A.get(_i),_R:A.get(_X),_C:A.get(_C),_M:A.get(_O),_N:A.get(_P),_E:A.get(_E),'volume_4':A.get('vol4'),_A0:A.get(_A2)})
		for E in range(1,4):
			C=f"g{E}"
			if C in A:
				try:
					B=A[C].split('|')
					if len(B)>=3:
						try:F=float(B[0])if B[0]else _A
						except ValueError:F=B[0]
						try:G=int(B[1])if B[1]else _A
						except ValueError:G=B[1]
						D.update({f"price_{E}":F,f"volume_{E}":G,f"flag_{E}":B[2]if B[2]else _A})
				except Exception as I:H.logger.warning(f"Failed to parse {C} field: {I}");D.update({f"{C}_raw":A.get(C)})
		return D
	def _parse_boardps_data(J,data,result):
		'Parse boardps (board price size) data for derivatives\n        \n        VPS sends boardps with nested structure:\n        {\n            "data": {\n                "id": 3211,\n                "boardId": "G1",\n                "marketId": "DVX",\n                "sequence": 106574,\n                "hashValue": "41I1FB000",\n                "transId": "DVX:VN41I1FB0002:X:106574:3211",\n                "tradingSession": "40",\n                "sym": "41I1FB000",\n                "side": "B",\n                "ndata": "1934.1:13SOH1933.9:1SOH..."\n            }\n        }\n        ';I='\x01';H='ndata';B=result;A=data.get(_B,{});B.update({_J:A.get(_I),_K:A.get(_D),_E:A.get(_E),_g:A.get(_i),_R:A.get(_X),_C:A.get(_C),_M:A.get(_O),_N:A.get(_P),_z:A.get(_A1)})
		if H in A:
			try:
				C=A[H]
				if I in C:E=C.split(I)
				else:E=C.split('SOH')
				for(F,G)in enumerate(E[:10],1):
					if':'in G:
						D=G.split(':')
						if len(D)>=2:
							try:K=float(D[0]);L=int(D[1]);B[f"price_{F}"]=K;B[f"volume_{F}"]=L
							except ValueError:pass
			except Exception as M:J.logger.warning(f"Failed to parse ndata: {M}")
		return B
	def _parse_aggregate_market_data(E,data,result):
		'Parse aggregate market data\n        \n        VPS sends:\n        {\n            "vol": 224876685,\n            "value": 5915671.331,\n            "ptVol": 5672585,\n            "ptValue": 349914209.08,\n            "fBVol": 17025970,\n            "fSVol": 34143370,\n            "fBVal": 727041856500,\n            "fSVal": 1210325565000,\n            "up": 307,\n            "down": 327,\n            "ref": 165,\n            "hsx_ce": 5,\n            "hsx_fl": 1,\n            ...\n        }\n        ';D='fSVal';C='fBVal';B=result;A=data;B.update({_Q:A.get(_T),_j:A.get(_H),'put_through_volume':A.get('ptVol'),'put_through_value':A.get('ptValue'),_A3:A.get(_F),_A4:A.get(_L),'foreign_buy_value':A.get(C),'foreign_sell_value':A.get(D),_U:A.get('up'),_V:A.get(_k),_W:A.get(_l),'hsx_ceiling':A.get('hsx_ce'),'hsx_floor':A.get('hsx_fl'),'hnx_ceiling':A.get('hnx_ce'),'hnx_floor':A.get('hnx_fl'),'upcom_ceiling':A.get('upcom_ce'),'upcom_floor':A.get('upcom_fl'),'vn30_ceiling':A.get('vn30_ce'),'vn30_floor':A.get('vn30_fl'),'vn100_ceiling':A.get('vn100_ce'),'vn100_floor':A.get('vn100_fl')})
		if A.get(_F)and A.get(_L):B[_A5]=A.get(_F)-A.get(_L)
		if A.get(C)and A.get(D):B['foreign_net_value']=A.get(C)-A.get(D)
		return B
	def _parse_aggregate_ps_data(C,data,result):
		'Parse aggregate price-size data (derivatives)\n        \n        VPS sends:\n        {\n            "lot": 72940,\n            "fBVol": 1396,\n            "fSVol": 2763,\n            "bid": 6135,\n            "ask": 9127,\n            "oi": 37358\n        }\n        ';B=result;A=data;B.update({_Y:A.get(_Y),_A3:A.get(_F),_A4:A.get(_L),'bid_volume':A.get('bid'),'ask_volume':A.get('ask'),'open_interest':A.get('oi')})
		if A.get(_F)and A.get(_L):B[_A5]=A.get(_F)-A.get(_L)
		return B
	def _parse_aggregate_cw_data(C,data,result):'Parse aggregate covered warrant data\n        \n        VPS sends:\n        {\n            "vol": 8292100,\n            "value": 26147706000,\n            "up": 54,\n            "down": 115,\n            "ref": 25\n        }\n        ';B=result;A=data;B.update({_Q:A.get(_T),_j:A.get(_H),_U:A.get('up'),_V:A.get(_k),_W:A.get(_l)});return B
	def _parse_aggregate_etf_data(C,data,result):'Parse aggregate ETF data\n        \n        VPS sends:\n        {\n            "vol": 202900,\n            "value": 5029388000,\n            "up": 6,\n            "down": 4,\n            "ref": 2\n        }\n        ';B=result;A=data;B.update({_Q:A.get(_T),_j:A.get(_H),_U:A.get('up'),_V:A.get(_k),_W:A.get(_l)});return B
	def _parse_aggregate_foreign_group_data(B,data,result):'Parse aggregate foreign group (proprietary trading) data\n        \n        Note: This is called with `data` parameter which is already\n        raw_data.get("data", {})\n        \n        VPS sends: fBVol, fSVolume, fBValue, fSValue, group\n        ';H='group';G=result;A=data;C=B._safe_convert(A.get(_F),int);D=B._safe_convert(A.get('fSVolume'),int);E=B._safe_convert(A.get('fBValue'),float);F=B._safe_convert(A.get('fSValue'),float);G.update({H:A.get(H),_A6:C,_A7:D,_A8:E,_A9:F,_AA:_A if C is _A or D is _A else C-D,_AB:_A if E is _A or F is _A else E-F});return G
	def _parse_aggregate_foreign_market_data(B,data,result):'Parse aggregate foreign market data\n        \n        Note: This is called with `data` parameter which is already\n        raw_data.get("data", {})\n        \n        VPS sends: fBVol, fSVolume, fBValue, fSValue, mc\n        ';H='room';G=result;A=data;C=B._safe_convert(A.get(_F),int);D=B._safe_convert(A.get('fSVolume'),int);E=B._safe_convert(A.get('fBValue'),float);F=B._safe_convert(A.get('fSValue'),float);I=B._safe_convert(A.get(H),int);J=B._safe_convert(A.get('cRoom'),int);G.update({_a:A.get('mc'),_A6:C,_A7:D,_A8:E,_A9:F,H:I,'current_room':J,_AA:_A if C is _A or D is _A else C-D,_AB:_A if E is _A or F is _A else E-F});return G
	def _parse_spt_data(B,data,result):'Parse spt (special transaction) data';D='price';C=result;A=data.get(_B,{});C.update({'transaction_id':A.get(_D),'transaction_type':A.get('type'),_J:A.get(_I),_h:A.get(_h),D:B._safe_convert(A.get(D),float),_b:B._safe_convert(A.get(_b),int),_H:B._safe_convert(A.get(_H),float),_R:A.get('marketID'),'firm_no':A.get('firmNo')});return C
	def _parse_psfsell_data(B,data,result):'Parse psfsell (proprietary securities firm sell) data';A=result;C=data.get(_B);A.update({'psf_sell_value':B._safe_convert(C,float)});return A
	def _parse_regs_data(E,data,result):'Parse registration response data';D='list';C='action';B=result;A=data;B.update({C:A.get(C),'symbols':A.get(D,'').split(',')if isinstance(A.get(D),str)else[]});return B
	def _safe_convert(B,value,convert_func):
		'Safely convert a value using the provided conversion function';A=value
		if A is _A:return
		try:return convert_func(A)
		except(ValueError,TypeError):return A
class WSSClient(BaseWebSocketClient):
	'WebSocket client for VPS market data with session management.'
	def __init__(A,uri='wss://bgdatafeed.vps.com.vn/socket.io/?EIO=4&transport=websocket',ping_interval=25,market='HOSE',enable_session_manager=True,session_check_interval=60):'\n        Initialize the VPS WebSocket client.\n        \n        Args:\n            uri (str): The WebSocket URI to connect to\n            ping_interval (int): Interval in seconds to send ping messages\n            market (str): Market to monitor for trading sessions\n            enable_session_manager (bool): Whether to enable automatic session management\n            session_check_interval (int): Interval in seconds to check market status\n        ';super().__init__(uri,ping_interval);A.raw_messages=[];A.data_parser=WSSDataParser();A.last_data_timestamp=_A;A.message_count=0;A.received_symbols=set();A.market=market;A.enable_session_manager=enable_session_manager;A.session_manager=_A;A.session_check_interval=session_check_interval;A.data_freeze_check_task=_A;A.data_freeze_threshold=120
	def add_raw_message(A,raw_message):'\n        Add a raw message to be sent after connection.\n        \n        Args:\n            raw_message (str): The raw message to send\n        ';A.raw_messages.append(raw_message)
	def clear_raw_messages(A):'Clear all raw messages.';A.raw_messages=[]
	def subscribe_symbols(A,symbols):'\n        Subscribe to a list of symbols.\n        \n        Args:\n            symbols (List[str]): List of stock symbols to subscribe to\n        ';B=','.join(symbols);C=f'42["regs","{{\\"action\\":\\"join\\",\\"list\\":\\"{B}\\"}}"]';A.add_raw_message(C);A.logger.info(f"Added subscription for symbols: {B}")
	async def connect(A):
		'\n        Connect to the WebSocket server and start processing messages.\n        \n        This overrides the base class method to add session management.\n        Returns immediately after starting session management or connection.\n        '
		if A.enable_session_manager and not A.session_manager:A.session_manager=SessionManager(market=A.market,check_interval=A.session_check_interval);A.session_manager.register_connect_handler(A._session_connect);A.session_manager.register_disconnect_handler(A._session_disconnect);A.session_manager.register_connection_health_checker(A._is_websocket_healthy);return
		await A._session_connect()
	def _is_websocket_healthy(A):'Check if WebSocket connection is actually healthy.';return A.is_connected()
	def _on_connection_closed(A):
		'Notify session manager when WebSocket connection closes.'
		if A.session_manager:A.logger.info('WebSocket closed - notifying session manager');A.session_manager.mark_disconnected()
	async def disconnect(A):
		'\n        Disconnect from the WebSocket server.\n        \n        This overrides the base class method to add session management cleanup.\n        '
		if A.session_manager:await A.session_manager.stop_monitoring();A.session_manager=_A
		if A.data_freeze_check_task and not A.data_freeze_check_task.done():
			A.data_freeze_check_task.cancel()
			try:await A.data_freeze_check_task
			except asyncio.CancelledError:pass
			A.data_freeze_check_task=_A
		await super().disconnect()
	async def start_session_monitoring(A):
		'\n        Start the session manager monitoring loop.\n        \n        This should be called after connect() when session management is enabled.\n        This method will block until shutdown, managing connections throughout\n        the trading day.\n        '
		if not A.session_manager:raise RuntimeError('Session manager not initialized. Call connect() with enable_session_manager=True first.')
		await A.session_manager.start_monitoring()
	async def _session_connect(A):
		'Internal method for session-managed connection.';A.logger.info('Session manager initiating connection');A.message_count=0;A.last_data_timestamp=_A;A.received_symbols.clear();await super().connect()
		if not A.data_freeze_check_task or A.data_freeze_check_task.done():A.data_freeze_check_task=asyncio.create_task(A._monitor_data_freeze())
	async def _session_disconnect(A):
		'Internal method for session-managed disconnection.';A.logger.info('Session manager initiating disconnection')
		if A.data_freeze_check_task and not A.data_freeze_check_task.done():
			A.data_freeze_check_task.cancel()
			try:await A.data_freeze_check_task
			except asyncio.CancelledError:pass
			A.data_freeze_check_task=_A
		await super().disconnect()
	async def _send_initial_messages(A):
		'Send all configured raw messages.'
		if not A.websocket:A.logger.warning('No websocket connection available');return
		try:
			if'EIO=4'in A.uri:D=await asyncio.wait_for(A.websocket.recv(),timeout=5);A.logger.info(f"Received Socket.IO handshake: {D[:50]}...");await A.websocket.send('40');A.logger.info('Sent Socket.IO connect packet');E=await asyncio.wait_for(A.websocket.recv(),timeout=5);A.logger.info(f"Received connect response: {E[:50]}...")
			if not A.raw_messages:A.logger.warning('No raw messages configured. You may not receive any data.');return
			for C in A.raw_messages:
				try:await A.websocket.send(C);A.logger.info(f"Sent raw message: {C[:50]}...")
				except Exception as B:A.logger.error(f"Error sending raw message: {B}");A.logger.error(traceback.format_exc())
		except asyncio.TimeoutError:A.logger.error('Timeout during initial message exchange')
		except Exception as B:A.logger.error(f"Error in initial message exchange: {B}");A.logger.error(traceback.format_exc())
	def _parse_message(A,message):
		'\n        Parse the received VPS-specific message.\n        \n        Args:\n            message (str): The raw message received from the WebSocket\n            \n        Returns:\n            Optional[Dict[str, Any]]: Parsed data or None if message should be ignored\n        ';B=message
		try:
			A.logger.debug(f"Raw message received: {B[:100]}...");A.last_data_timestamp=time.time();A.message_count+=1
			if B.startswith('42'):
				F=B[2:];D=json.loads(F)
				if isinstance(D,list)and len(D)>=2:
					G=D[0];C=D[1]
					if isinstance(C,str):
						try:C=json.loads(C)
						except json.JSONDecodeError:A.logger.warning(f"Failed to parse payload as JSON: {C[:100]}...")
					H={_m:G,_B:C,'timestamp':time.time()}
					if isinstance(C,dict)and _B in C and isinstance(C[_B],dict):
						E=C[_B].get(_I)
						if E:A.received_symbols.add(E)
					return A.data_parser.parse_data(H)
			elif B=='2':A.logger.debug('Received ping response')
			elif B=='3':A.logger.debug('Received pong message')
			elif B.startswith('0'):A.logger.info(f"Connection established: {B}")
			elif B.startswith('40'):A.logger.info(f"Socket.IO connection established: {B}")
			elif B.startswith('41'):A.logger.warning(f"Socket.IO disconnected: {B}")
			else:A.logger.debug(f"Received unknown message type: {B[:50]}...")
			return
		except Exception as I:A.logger.error(f"Error parsing message: {I}");A.logger.error(traceback.format_exc());A.logger.debug(f"Problematic message: {B[:200]}...");return
	async def _monitor_data_freeze(A):
		'\n        Monitor for data freezing conditions.\n        \n        This is particularly important during session transitions (e.g., lunch break).\n        '
		try:
			B=0;D=min(30,A.data_freeze_threshold//4)
			while A.running:
				await asyncio.sleep(D)
				if A.last_data_timestamp is _A:continue
				E=time.time();C=E-A.last_data_timestamp
				if C>A.data_freeze_threshold:
					B+=1;A.logger.warning(f"Potential data freeze detected! No data for {C:.1f}s (Detection #{B})")
					if B>=2:
						A.logger.warning('Multiple data freezes detected, triggering reconnection')
						if A.session_manager:await A.session_manager.trigger_reconnect()
						else:await A._handle_data_freeze()
						B=0
				else:B=0
		except asyncio.CancelledError:A.logger.info('Data freeze monitoring cancelled');raise
		except Exception as F:A.logger.error(f"Error in data freeze monitoring: {F}");A.logger.error(traceback.format_exc())
	async def _handle_data_freeze(A):
		'Handle a detected data freeze by triggering reconnection.';A.logger.info('Handling data freeze - requesting reconnection')
		if A.session_manager:await A.session_manager.trigger_reconnect()
		else:await A._session_disconnect();await asyncio.sleep(2);await A._session_connect()
	def get_connection_stats(A):
		'\n        Get statistics about the current connection.\n        \n        Returns:\n            Dict[str, Any]: Connection statistics\n        ';B={'connected':A.websocket is not _A and A.running,'message_count':A.message_count,'received_symbols_count':len(A.received_symbols),'received_symbols':list(A.received_symbols)}
		if A.last_data_timestamp:B['last_data_time']=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(A.last_data_timestamp));B['seconds_since_last_data']=time.time()-A.last_data_timestamp
		return B