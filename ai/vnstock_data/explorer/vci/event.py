'\nVCI Events Explorer module.\n'
from datetime import datetime
import pandas as pd
from vnai import agg_execution
from vnstock.core.utils.logger import get_logger
from vnstock.core.utils.parser import camel_to_snake
from vnstock_data.core.utils.client import send_request
from vnstock_data.core.utils.user_agent import get_headers
from vnstock_data.explorer.vci.const import _VCI_EVENTS_URL
logger=get_logger(__name__)
class Event:
	'\n    Class to manage event information from the VCI data source.\n    '
	def __init__(A,random_agent=False,show_log=False):
		B=show_log;A.headers=get_headers(data_source=bytes([86,67,73]).decode(),random_agent=random_agent);A.show_log=B
		if not B:logger.setLevel(bytes([67,82,73,84,73,67,65,76]).decode())
	@agg_execution(bytes([86,67,73,46,101,120,116]).decode())
	def calendar(self,start=None,end=None,event_type=None,page=0,limit=20000,show_log=False):
		"\n        Retrieve events calendar (dividends, AGM, new listings, ...) from VCI.\n        \n        Args:\n            start (str): Start date (YYYY-MM-DD). If None, defaults to the current date.\n            end (str): End date (YYYY-MM-DD). If None, defaults to the current date.\n            event_type (str, optional): Type of event or event group:\n                - 'dividend': Returns dividends, share issuance (ISS, DIV)\n                - 'insider': Returns insider trading, major shareholders (DDIND, DDRP, DDINS)\n                - 'agm': Returns shareholder meetings (EGME, AGME, AGMR)\n                - 'others': Returns other fluctuations (MOVE, MA, NLIS, AIS, RETU, OTHE, SUSP)\n                - Or a specific eventCode (e.g., 'ISS,DIV')\n            page (int): Page index. Defaults to 0.\n            limit (int): Number of records per page. Defaults to 20000.\n            show_log (bool): Show logs.\n            \n        Returns:\n            pd.DataFrame: List of events.\n        ";H=show_log;F=self;D=event_type;C=end;B=start
		if B is None:B=datetime.now().strftime(bytes([37,89,45,37,109,45,37,100]).decode())
		if C is None:C=B
		K=B.replace(bytes([45]).decode(),'').replace(bytes([47]).decode(),'');L=C.replace(bytes([45]).decode(),'').replace(bytes([47]).decode(),'');I=f"{_VCI_EVENTS_URL}?fromDate={K}&toDate={L}&page={page}&size={limit}";M={bytes([100,105,118,105,100,101,110,100]).decode():bytes([73,83,83,44,68,73,86]).decode(),bytes([105,110,115,105,100,101,114]).decode():bytes([68,68,73,78,68,44,68,68,82,80,44,68,68,73,78,83]).decode(),bytes([97,103,109]).decode():bytes([69,71,77,69,44,65,71,77,69,44,65,71,77,82]).decode(),bytes([111,116,104,101,114,115]).decode():bytes([77,79,86,69,44,77,65,44,78,76,73,83,44,65,73,83,44,82,69,84,85,44,79,84,72,69,44,83,85,83,80]).decode()}
		if D:N=M.get(D.lower(),D);O=N.replace(bytes([44]).decode(),bytes([37,50,67]).decode());I+=f"&eventCode={O}"
		J=F.headers.copy();J.update({bytes([65,99,99,101,112,116]).decode():bytes([97,112,112,108,105,99,97,116,105,111,110,47,106,115,111,110]).decode(),bytes([65,99,99,101,112,116,45,76,97,110,103,117,97,103,101]).decode():bytes([101,110,45,85,83,44,101,110,59,113,61,48,46,57,44,118,105,59,113,61,48,46,56]).decode(),bytes([67,111,110,110,101,99,116,105,111,110]).decode():bytes([107,101,101,112,45,97,108,105,118,101]).decode(),bytes([68,78,84]).decode():bytes([49]).decode(),bytes([79,114,105,103,105,110]).decode():bytes([104,116,116,112,115,58,47,47,116,114,97,100,105,110,103,46,118,105,101,116,99,97,112,46,99,111,109,46,118,110]).decode(),bytes([82,101,102,101,114,101,114]).decode():bytes([104,116,116,112,115,58,47,47,116,114,97,100,105,110,103,46,118,105,101,116,99,97,112,46,99,111,109,46,118,110,47]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,68,101,115,116]).decode():bytes([101,109,112,116,121]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,77,111,100,101]).decode():bytes([99,111,114,115]).decode(),bytes([83,101,99,45,70,101,116,99,104,45,83,105,116,101]).decode():bytes([115,97,109,101,45,115,105,116,101]).decode(),bytes([115,101,99,45,99,104,45,117,97]).decode():bytes([34,78,111,116,58,65,45,66,114,97,110,100,34,59,118,61,34,57,57,34,44,32,34,71,111,111,103,108,101,32,67,104,114,111,109,101,34,59,118,61,34,49,52,53,34,44,32,34,67,104,114,111,109,105,117,109,34,59,118,61,34,49,52,53,34]).decode(),bytes([115,101,99,45,99,104,45,117,97,45,109,111,98,105,108,101]).decode():bytes([63,48]).decode(),bytes([115,101,99,45,99,104,45,117,97,45,112,108,97,116,102,111,114,109]).decode():bytes([34,109,97,99,79,83,34]).decode()})
		if H or F.show_log:logger.info(f"Fetching events calendar from {B} to {C} (type: {D})")
		E=send_request(url=I,headers=J,method=bytes([71,69,84]).decode(),show_log=H or F.show_log)
		if not E or bytes([100,97,116,97]).decode()not in E or bytes([99,111,110,116,101,110,116]).decode()not in E[bytes([100,97,116,97]).decode()]:return pd.DataFrame()
		A=pd.DataFrame(E[bytes([100,97,116,97]).decode()][bytes([99,111,110,116,101,110,116]).decode()])
		if A.empty:return A
		A.columns=[camel_to_snake(A)for A in A.columns];P=[bytes([100,105,115,112,108,97,121,95,100,97,116,101,49]).decode(),bytes([100,105,115,112,108,97,121,95,100,97,116,101,50]).decode(),bytes([112,117,98,108,105,99,95,100,97,116,101]).decode(),bytes([105,115,115,117,101,95,100,97,116,101]).decode(),bytes([114,101,99,111,114,100,95,100,97,116,101]).decode(),bytes([101,120,114,105,103,104,116,95,100,97,116,101]).decode(),bytes([112,97,121,111,117,116,95,100,97,116,101]).decode()]
		for G in P:
			if G in A.columns:A[G]=pd.to_datetime(A[G],format=bytes([73,83,79,56,54,48,49]).decode(),errors=bytes([99,111,101,114,99,101]).decode())
		return A
from vnstock_data.core.registry import ProviderRegistry
ProviderRegistry.register(bytes([101,118,101,110,116]).decode(),bytes([118,99,105]).decode(),Event)