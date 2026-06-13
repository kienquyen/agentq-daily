'\nAPI client utilities for vnstock data sources.\n\nModule này cung cấp các tiện ích để gửi request tới các nguồn dữ liệu của vnstock, hỗ trợ nhiều chế độ gửi (trực tiếp, qua proxy) và nhiều chế độ chọn proxy (try, rotate, random, single).\n\nCác hàm chính:\n- send_request: interface trung tâm cho tất cả các mode gửi request\n- send_request_direct: gửi request trực tiếp\n- send_proxy_request: gửi request qua proxy thông thường\n'
import json,random
from enum import Enum
from typing import Any
import requests
from pydantic import BaseModel
from vnstock.core.utils.logger import get_logger
logger=get_logger(__name__)
class ProxyMode(Enum):'\n    Các chế độ sử dụng proxy khi gửi request:\n    - TRY: Thử lần lượt từng proxy cho đến khi thành công\n    - ROTATE: Luân phiên proxy sau mỗi lần gọi\n    - RANDOM: Chọn ngẫu nhiên proxy cho mỗi lần gọi\n    - SINGLE: Luôn dùng proxy đầu tiên\n    ';TRY=bytes([116,114,121]).decode();ROTATE=bytes([114,111,116,97,116,101]).decode();RANDOM=bytes([114,97,110,100,111,109]).decode();SINGLE=bytes([115,105,110,103,108,101]).decode()
class RequestMode(Enum):'\n    Các chế độ gửi request:\n    - DIRECT: Gửi trực tiếp không qua proxy\n    - PROXY: Gửi qua proxy thông thường\n    ';DIRECT=bytes([100,105,114,101,99,116]).decode();PROXY=bytes([112,114,111,120,121]).decode()
class ProxyConfig(BaseModel):
	'\n    Cấu hình proxy cho các request API.\n    Sử dụng cho các class/module cần truyền proxy.\n    \n    Attributes:\n        proxy_list: Danh sách proxy URL (định dạng string)\n        proxy_objects: Danh sách Proxy objects với metadata\n        proxy_mode: Chế độ chọn proxy (TRY, ROTATE, RANDOM, SINGLE)\n        request_mode: Chế độ gửi request (DIRECT, PROXY)\n        auto_fetch: Tự động lấy proxy từ API\n        validate_proxies: Kiểm tra tính hợp lệ của proxy\n        prefer_speed: Ưu tiên proxy có tốc độ tốt nhất\n    ';proxy_list:list[str]|None=None;proxy_objects:list[Any]|None=None;proxy_mode:ProxyMode=ProxyMode.TRY;request_mode:RequestMode=RequestMode.DIRECT;auto_fetch:bool=False;validate_proxies:bool=False;prefer_speed:bool=False
	class Config:arbitrary_types_allowed=True
logger=get_logger(__name__)
_current_proxy_index=0
def build_proxy_dict(proxy_url):'\n    Chuyển đổi proxy URL thành dict format cho requests.\n    Args:\n        proxy_url (str): URL của proxy\n    Returns:\n        Dict[str, str]: Dict cấu hình proxy cho requests\n    ';A=proxy_url;return{bytes([104,116,116,112]).decode():A,bytes([104,116,116,112,115]).decode():A}
def get_proxy_by_mode(proxy_list,mode):
	'\n    Lấy proxy từ danh sách proxy theo chế độ đã chọn.\n    Args:\n        proxy_list (List[str]): Danh sách proxy URL\n        mode (ProxyMode): Chế độ chọn proxy\n    Returns:\n        str: Proxy URL được chọn\n    ';B=mode;A=proxy_list;global _current_proxy_index
	if not A:raise ValueError(bytes([80,114,111,120,121,32,108,105,115,116,32,105,115,32,101,109,112,116,121]).decode())
	if B==ProxyMode.SINGLE:return A[0]
	elif B==ProxyMode.RANDOM:return random.choice(A)
	elif B==ProxyMode.ROTATE:C=A[_current_proxy_index%len(A)];_current_proxy_index+=1;return C
	else:return A[0]
def send_request(url,headers,method=bytes([71,69,84]).decode(),params=None,payload=None,show_log=False,timeout=30,proxy_list=None,proxy_mode=ProxyMode.TRY,request_mode=RequestMode.DIRECT,auto_fetch=False,validate_proxies=False,prefer_speed=False,raw=False):
	'\n    Interface trung tâm cho tất cả các mode gửi request.\n    Tùy theo request_mode và proxy_mode sẽ chọn cách gửi request phù hợp.\n    \n    Args:\n        url (str): Địa chỉ endpoint\n        headers (Dict[str, str]): Header cho request\n        method (str): "GET" hoặc "POST". Mặc định "GET"\n        params (Optional[Dict]): Tham số query cho GET\n        payload (Optional[Union[Dict, str]]): Dữ liệu gửi đi (POST)\n        show_log (bool): Bật log chi tiết\n        timeout (int): Timeout (giây)\n        proxy_list (Optional[List[str]]): Danh sách proxy URLs (cho PROXY mode)\n        proxy_mode (Union[ProxyMode, str]): Chế độ sử dụng proxy\n        request_mode (Union[RequestMode, str]): Chế độ gửi request\n        auto_fetch (bool): Tự động lấy proxy từ API\n        validate_proxies (bool): Kiểm tra tính hợp lệ của proxy\n        prefer_speed (bool): Ưu tiên proxy có tốc độ tốt nhất\n    \n    Returns:\n        Dict[str, Any]: Dữ liệu JSON trả về\n    \n    Raises:\n        ConnectionError: Nếu tất cả proxy đều thất bại hoặc request lỗi\n    ';T=prefer_speed;S=validate_proxies;R=auto_fetch;L=raw;K=headers;J=timeout;I=method;H=url;G=payload;F=params;E=request_mode;C=proxy_mode;B=show_log;A=proxy_list
	if R or S or T:
		from.proxy_manager import ProxyManager as W;M=W(timeout=J)
		if R:
			if B:logger.info(bytes([65,117,116,111,45,102,101,116,99,104,105,110,103,32,112,114,111,120,105,101,115,32,102,114,111,109,32,112,114,111,120,121,115,99,114,97,112,101,32,65,80,73,46,46,46]).decode())
			try:
				A=[str(A)for A in M.fetch_proxies(limit=10)];E=RequestMode.PROXY
				if B:logger.info(f"Fetched {len(A)} proxies")
			except Exception as D:logger.warning(f"Failed to auto-fetch proxies: {D}")
		if S and A:
			if B:logger.info(bytes([86,97,108,105,100,97,116,105,110,103,32,112,114,111,120,105,101,115,46,46,46]).decode())
			try:
				from.proxy import Proxy;N=[Proxy(protocol=bytes([72,84,84,80]).decode(),ip=A.split(bytes([58,47,47]).decode())[-1].split(bytes([58]).decode())[0],port=int(A.split(bytes([58]).decode())[-1]))for A in A];X=M.test_proxies(N);A=[str(A)for A in X]
				if B:logger.info(f"{len(A)} proxies are valid")
			except Exception as D:logger.warning(f"Failed to validate proxies: {D}")
		if T and A:
			if B:logger.info(bytes([83,101,108,101,99,116,105,110,103,32,102,97,115,116,101,115,116,32,112,114,111,120,121,46,46,46]).decode())
			try:
				from.proxy import Proxy;N=[Proxy(protocol=bytes([72,84,84,80]).decode(),ip=A.split(bytes([58,47,47]).decode())[-1].split(bytes([58]).decode())[0],port=int(A.split(bytes([58]).decode())[-1]))for A in A];O=M.get_best_proxy(N)
				if O:
					A=[str(O)];C=ProxyMode.SINGLE
					if B:logger.info(f"Using fastest proxy: {O}")
			except Exception as D:logger.warning(f"Failed to select fastest proxy: {D}")
	if isinstance(C,str):
		try:C=ProxyMode(C)
		except ValueError:raise ValueError(f"Invalid proxy_mode: {C}")
	if isinstance(E,str):
		try:E=RequestMode(E)
		except ValueError:raise ValueError(f"Invalid request_mode: {E}")
	if B:
		logger.info(f"{I.upper()} request to {H} (mode: {E.value})")
		if F:logger.info(f"Params: {F}")
		if G:logger.info(f"Payload: {G}")
	if E==RequestMode.PROXY:
		if not A:raise ValueError(bytes([112,114,111,120,121,95,108,105,115,116,32,105,115,32,114,101,113,117,105,114,101,100,32,102,111,114,32,80,82,79,88,89,32,109,111,100,101]).decode())
		if C==ProxyMode.TRY:
			U=None
			for P in A:
				try:
					if B:logger.info(f"Trying proxy: {P}")
					Q=build_proxy_dict(P);return send_request_direct(H,K,I,F,G,J,Q,raw=L)
				except ConnectionError as D:
					U=D
					if B:logger.warning(f"Proxy {P} failed: {D}")
					continue
			raise ConnectionError(f"All proxies failed. Last error: {U}")
		else:
			V=get_proxy_by_mode(A,C);Q=build_proxy_dict(V)
			if B:logger.info(f"Using proxy ({C.value} mode): {V}")
			return send_request_direct(H,K,I,F,G,J,Q,raw=L)
	else:
		if B:logger.info(bytes([83,101,110,100,105,110,103,32,100,105,114,101,99,116,32,114,101,113,117,101,115,116,32,40,110,111,32,112,114,111,120,121,41]).decode())
		return send_request_direct(H,K,I,F,G,J,proxies=None,raw=L)
def send_request_direct(url,headers,method=bytes([71,69,84]).decode(),params=None,payload=None,timeout=30,proxies=None,raw=False):
	'\n    Gửi request trực tiếp tới endpoint, không qua proxy đặc biệt.\n    Args:\n        url (str): Endpoint URL\n        headers (Dict[str, str]): Header cho request\n        method (str): "GET" hoặc "POST"\n        params (Optional[Dict]): Tham số query cho GET\n        payload (Optional[Union[Dict, str]]): Dữ liệu gửi đi (POST)\n        timeout (int): Timeout (giây)\n        proxies (Optional[Dict[str, str]]): Dict proxy nếu có\n    Returns:\n        Dict[str, Any]: Dữ liệu JSON trả về\n    Raises:\n        ConnectionError: Nếu request thất bại hoặc trả về mã lỗi\n    ';F=proxies;E=timeout;D=headers;B=payload
	try:
		if method.upper()==bytes([71,69,84]).decode():A=requests.get(url,headers=D,params=params,timeout=E,proxies=F)
		else:
			if B is not None:
				if isinstance(B,dict):C=json.dumps(B)
				elif isinstance(B,str):C=B
				else:raise ValueError(bytes([80,97,121,108,111,97,100,32,109,117,115,116,32,98,101,32,101,105,116,104,101,114,32,97,32,100,105,99,116,105,111,110,97,114,121,32,111,114,32,97,32,114,97,119,32,115,116,114,105,110,103,46]).decode())
			else:C=None
			A=requests.post(url,headers=D,data=C,timeout=E,proxies=F)
		if not raw and A.status_code!=200:raise ConnectionError(f"Failed to fetch data: {A.status_code} - {A.reason}")
		if raw:return A
		return A.json()
	except requests.exceptions.RequestException as H:G=f"API request failed: {H!s}";logger.error(G);raise ConnectionError(G)
def reset_proxy_rotation():'\n    Reset proxy rotation index về 0.\n    Dùng khi muốn bắt đầu lại vòng quay proxy ở chế độ ROTATE.\n    ';global _current_proxy_index;_current_proxy_index=0
def send_direct_request(url,headers,**A):'\n    Gửi request trực tiếp không qua proxy.\n    Args:\n        url (str): Endpoint URL\n        headers (Dict[str, str]): Header cho request\n        **kwargs: Các tham số bổ sung cho send_request\n    Returns:\n        Dict[str, Any]: Dữ liệu JSON trả về\n    ';return send_request(url,headers,request_mode=RequestMode.DIRECT,**A)
def send_proxy_request(url,headers,proxy_list,**A):'\n    Gửi request qua proxy thông thường.\n    Args:\n        url (str): Endpoint URL\n        headers (Dict[str, str]): Header cho request\n        proxy_list (List[str]): Danh sách proxy URL\n        **kwargs: Các tham số bổ sung cho send_request\n    Returns:\n        Dict[str, Any]: Dữ liệu JSON trả về\n    ';return send_request(url,headers,proxy_list=proxy_list,request_mode=RequestMode.PROXY,**A)