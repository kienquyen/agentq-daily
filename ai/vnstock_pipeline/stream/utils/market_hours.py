'\nMarket Trading Hours Utility\n\nSimple utility to check market trading hours and data availability.\n'
_D='en'
_C=False
_B=None
_A='HOSE'
import datetime,pytz,logging
from typing import Dict,Any,Optional
logger=logging.getLogger(__name__)
def trading_hours(market=_A,custom_time=_B,enable_log=_C,language=_D):
	'\n    Check if current time is within trading hours with data availability context.\n    \n    Args:\n        market (str): Market to check (\'HOSE\', \'HNX\', \'UPCOM\', \'Futures\', or None)\n                     If None, returns simplified data based on common market hours\n        custom_time (datetime.datetime, optional): Custom time for testing\n        enable_log (bool): Whether to enable funny log messages\n        language (str): Language for messages (\'en\' for English, \'vi\' for Vietnamese)\n        \n    Returns:\n        dict: Trading status information with keys:\n            - is_trading_hour (bool): Whether it\'s currently trading hours\n            - trading_session (str): Current trading session type\n            - data_status (str): Data availability status\n            - time (str): Current time in HH:MM:SS format\n            - market (str): Market being checked or "general" if market is None\n    ';A0='general';z='%H:%M:%S';y='market';x='time';w='data_status';v='trading_session';u='is_trading_hour';t='15:00';o=custom_time;n=True;m='historical_only';l='historical';k='Futures';j='UPCOM';i='HNX';f=language;e='weekend';d='post_market';c='post_close';b='atc';a='lunch_break';Z='continuous';Y='ato';X='pre_market';W='14:45';V='14:30';U='13:00';T='11:30';S='09:00';R='ato_end';Q='real_time';P='trading_end';O='atc_start';N='lunch_end';M='lunch_start';L='trading_start';I='atc_end';H='%H:%M';F=market;B=enable_log;A8=[_A,i,j,k,_B]
	if F is not _B and F not in[_A,i,j,k]:raise ValueError(f"Unknown market: {F}. Valid markets: HOSE, HNX, UPCOM, Futures, None")
	if f not in[_D,'vi']:f=_D
	if B and not logger.handlers:p=logging.StreamHandler();A1=logging.Formatter('%(asctime)s - %(levelname)s - %(message)s');p.setFormatter(A1);logger.addHandler(p);logger.setLevel(logging.INFO)
	q={_A:{L:S,R:'09:15',M:T,N:U,O:V,I:W,P:t},i:{L:S,M:T,N:U,O:V,I:W,P:t},j:{L:S,M:T,N:U,P:V},k:{L:'08:45',R:S,M:T,N:U,O:V,I:W,P:W}};r=pytz.timezone('Asia/Ho_Chi_Minh')
	if o:K=o.astimezone(r)
	else:K=datetime.datetime.now(r)
	A2={X:'[PRE-MARKET] Markets still snoozing! Your data might be wearing pajamas too.',Y:'[ATO] ATO in progress! Prices are playing musical chairs.',Z:'[TRADING] Trading in full swing! Money printer go brrrr!',a:'[LUNCH] Lunch break! Even algorithms need to slurp some digital noodles.',b:'[ATC] ATC time! Final sprint to determine closing prices.',c:'[POST-CLOSE] Post-close cleanup. Last chance to sweep up some bargains!',d:"[POST-MARKET] Markets closed but data's still settling in... like your food after dinner.",e:'[WEEKEND] Weekend mode! Markets closed. Time to touch grass instead of charts.',l:'[HISTORICAL] Deep in after-hours territory. Only historical data here, like dinosaur fossils.'};A3={X:'[TRUOC-GD] Thị trường vẫn đang ngủ! Dữ liệu của bạn cũng có thể đang nghỉ ngơi.',Y:'[ATO] ATO đang diễn ra! Giá cả đang định hình.',Z:'[GD-SOI-DONG] Giao dịch đang diễn ra sôi động! Thị trường đang hoạt động mạnh.',a:'[NGHI-TRUA] Giờ nghỉ trưa! Ngay cả thuật toán cũng cần nghỉ ngơi.',b:'[ATC] Giờ ATC! Nước rút cuối cùng để xác định giá đóng cửa.',c:'[SAU-GD] Dọn dẹp sau giờ đóng cửa. Cơ hội cuối để giao dịch thỏa thuận!',d:'[SAU-THI-TRUONG] Thị trường đã đóng cửa nhưng dữ liệu vẫn đang ổn định...',e:'[CUOI-TUAN] Chế độ cuối tuần! Thị trường đóng cửa. Thời gian để nghỉ ngơi.',l:'[LICH-SU] Ngoài giờ giao dịch. Chỉ có dữ liệu lịch sử ở đây.'};D=A2 if f==_D else A3
	if K.weekday()>=5:
		if B:logger.info(D[e])
		return{u:_C,v:e,w:m,x:K.strftime(z),y:A0 if F is _B else F}
	if F is _B:A=q[_A];s=A0
	else:A=q[F];s=F
	g=datetime.datetime.strptime(A[L],H).time();A4=datetime.datetime.strptime(A[M],H).time();A5=datetime.datetime.strptime(A[N],H).time();h=datetime.datetime.strptime(A[P],H).time();A6=(datetime.datetime.combine(datetime.date.today(),g)-datetime.timedelta(hours=2)).time();A7=(datetime.datetime.combine(datetime.date.today(),h)+datetime.timedelta(hours=4)).time();G=K.time();J=_C;E='';C=''
	if G<g:
		E=X
		if G>=A6:C='preparing'
		else:C=m
		if B:logger.info(D[X])
	elif G>=h:
		if G<=A7:
			E=d;C='settling'
			if B:logger.info(D[d])
		else:
			E='after_hours';C=m
			if B:logger.info(D[l])
	elif R in A and g<=G<datetime.datetime.strptime(A[R],H).time():
		E=Y;J=n;C=Q
		if B:logger.info(D[Y])
	elif A4<=G<A5:
		E=a;J=_C;C=Q
		if B:logger.info(D[a])
	elif O in A and I in A and datetime.datetime.strptime(A[O],H).time()<=G<datetime.datetime.strptime(A[I],H).time():
		E=b;J=n;C=Q
		if B:logger.info(D[b])
	elif I in A and datetime.datetime.strptime(A[I],H).time()<=G<h:
		E=c;J=_C;C=Q
		if B:logger.info(D[c])
	else:
		E=Z;J=n;C=Q
		if B:logger.info(D[Z])
	return{u:J,v:E,w:C,x:K.strftime(z),y:s}