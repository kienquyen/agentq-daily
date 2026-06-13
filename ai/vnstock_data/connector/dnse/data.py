import argparse,csv,json,logging,os,random,time,requests,yaml
from paho.mqtt import client as mqtt_client
from paho.mqtt.client import MQTTv5
from paho.mqtt.subscribeoptions import SubscribeOptions
def append_tick_to_csv(tick_data,filename=bytes([116,105,99,107,95,100,97,116,97,46,99,115,118]).decode()):
	A=filename;C=[bytes([115,121,109,98,111,108]).decode(),bytes([109,97,116,99,104,80,114,105,99,101]).decode(),bytes([109,97,116,99,104,81,116,116,121]).decode(),bytes([116,105,109,101]).decode(),bytes([115,105,100,101]).decode(),bytes([115,101,115,115,105,111,110]).decode(),bytes([108,111,119]).decode(),bytes([111,112,101,110]).decode(),bytes([108,97,115,116,85,112,100,97,116,101,100]).decode(),bytes([118,111,108,117,109,101]).decode(),bytes([99,108,111,115,101]).decode(),bytes([116,121,112,101]).decode(),bytes([104,105,103,104]).decode()];D=os.path.isfile(A)
	with open(A,bytes([97]).decode(),newline='')as E:
		B=csv.DictWriter(E,fieldnames=C)
		if not D:B.writeheader()
		B.writerow(tick_data)
def yaml_creds(path):
	'\n    Đọc thông tin từ file cấu hình định dạng yaml. \n    user name phải là số điện thoại, số lưu ký hoặc email.\n    \n    Tham số:\n        - path: str: Đường dẫn đến file cấu hình.\n    \n    Trả về:\n        - username (str): giá trị username được lấy từ file cấu hình.\n        - password: (str): giá trị password được lấy từ file cấu hình.\n\n    Tài liệu API: https://hdsd.dnse.com.vn/san-pham-dich-vu/api-lightspeed/iii.-market-data/2.-dac-ta-thong-tin-cac-message/2.1.-moi-truong\n    '
	try:
		with open(path)as C:
			A=yaml.safe_load(C)
			if not isinstance(A,dict):raise ValueError(bytes([84,104,101,32,99,114,101,100,101,110,116,105,97,108,115,32,102,105,108,101,32,102,111,114,109,97,116,32,105,115,32,105,110,99,111,114,114,101,99,116,46,32,69,120,112,101,99,116,101,100,32,97,32,100,105,99,116,105,111,110,97,114,121,46]).decode())
			D=A[bytes([117,115,114]).decode()];E=A[bytes([112,119,100]).decode()]
		return D,E
	except FileNotFoundError:raise FileNotFoundError(f"The file {path} does not exist.")
	except yaml.YAMLError as B:raise ValueError(f"Error parsing the YAML file: {B}")
	except KeyError as B:raise KeyError(f"Missing required key in the credentials file: {B}")
class Auth:
	def __init__(A,username,password):'\n        Xác thực kết nối tới DNSE API.\n\n        Tham số:\n            - username (str): giá trị username được lấy từ file cấu hình.\n            - password (str): giá trị password được lấy từ file cấu hình.\n\n        Trả về:\n            - jwt_token (str): giá trị token được lấy từ DNSE API, có hiệu lực trong 8 tiếng.\n            - investor_id (str): giá trị investor_id được lấy từ DNSE API.\n\n        Tài liệu API: https://hdsd.dnse.com.vn/san-pham-dich-vu/api-lightspeed/iii.-market-data/2.-dac-ta-thong-tin-cac-message/2.1.-moi-truong\n        ';A.username=username;A.password=password;A.token=A._get_token();A.investor_id=A._get_investorid()
	def _get_token(B):
		'\n        Extract token key from DNSE API\n        ';C=bytes([104,116,116,112,115,58,47,47,115,101,114,118,105,99,101,115,46,101,110,116,114,97,100,101,46,99,111,109,46,118,110,47,100,110,115,101,45,117,115,101,114,45,115,101,114,118,105,99,101,47,97,112,105,47,97,117,116,104]).decode();D=json.dumps({bytes([117,115,101,114,110,97,109,101]).decode():B.username,bytes([112,97,115,115,119,111,114,100]).decode():B.password});E={bytes([67,111,110,116,101,110,116,45,84,121,112,101]).decode():bytes([97,112,112,108,105,99,97,116,105,111,110,47,106,115,111,110]).decode()};A=requests.request(bytes([80,79,83,84]).decode(),C,headers=E,data=D)
		if A.status_code==200:return A.json()[bytes([116,111,107,101,110]).decode()]
		else:A.raise_for_status()
	def _get_investorid(B):
		'\n        Extract investor id from DNSE API\n        ';C=bytes([104,116,116,112,115,58,47,47,115,101,114,118,105,99,101,115,46,101,110,116,114,97,100,101,46,99,111,109,46,118,110,47,100,110,115,101,45,117,115,101,114,45,115,101,114,118,105,99,101,47,97,112,105,47,109,101]).decode();D={bytes([67,111,110,116,101,110,116,45,84,121,112,101]).decode():bytes([97,112,112,108,105,99,97,116,105,111,110,47,106,115,111,110]).decode(),bytes([97,117,116,104,111,114,105,122,97,116,105,111,110]).decode():f"Bearer {B.token}"};A=requests.request(bytes([71,69,84]).decode(),C,headers=D)
		if A.status_code==200:E=A.json();return E[bytes([105,110,118,101,115,116,111,114,73,100]).decode()]
		else:A.raise_for_status()
class Config:
	'\n    Application Configuration Class\n    '
	def __init__(A,creds_path,topics):A.user_name,A.password=yaml_creds(creds_path);A.auth=Auth(A.user_name,A.password);A.BROKER=bytes([100,97,116,97,102,101,101,100,45,108,116,115,46,100,110,115,101,46,99,111,109,46,118,110]).decode();A.PORT=443;A.TOPICS=topics;A.CLIENT_ID=f"python-json-mqtt-ws-sub-{random.randint(0,1000)}";A.USERNAME=A.auth.investor_id;A.PASSWORD=A.auth.token;A.FIRST_RECONNECT_DELAY=1;A.RECONNECT_RATE=2;A.MAX_RECONNECT_COUNT=12;A.MAX_RECONNECT_DELAY=60
class MQTTClient:
	'\n    Class encapsulating MQTT Client related functionalities\n    '
	def __init__(A,config):A.config=config;A.client=mqtt_client.Client(client_id=A.config.CLIENT_ID,protocol=MQTTv5,transport=bytes([119,101,98,115,111,99,107,101,116,115]).decode());A.client.username_pw_set(A.config.USERNAME,A.config.PASSWORD);A.client.tls_set_context();A.client.ws_set_options(path=bytes([47,119,115,115]).decode());A.client.on_connect=A.on_connect;A.client.on_message=A.on_message;A.client.on_disconnect=A.on_disconnect;A.FLAG_EXIT=False
	def connect_mqtt(A):A.client.connect(A.config.BROKER,A.config.PORT,keepalive=120);return A.client
	def on_connect(A,client,userdata,flags,rc,properties=None):
		if rc==0 and client.is_connected():logging.info(bytes([67,111,110,110,101,99,116,101,100,32,116,111,32,77,81,84,84,32,66,114,111,107,101,114,33]).decode());B=[(A,SubscribeOptions(qos=2))for A in A.config.TOPICS];A.client.subscribe(B)
		else:logging.error(f"Failed to connect, return code {rc}")
	def on_disconnect(A,client,userdata,rc,properties=None):
		logging.info(bytes([68,105,115,99,111,110,110,101,99,116,101,100,32,119,105,116,104,32,114,101,115,117,108,116,32,99,111,100,101,58,32,37,115]).decode(),rc);C,B=0,A.config.FIRST_RECONNECT_DELAY
		while C<A.config.MAX_RECONNECT_COUNT:
			logging.info(bytes([82,101,99,111,110,110,101,99,116,105,110,103,32,105,110,32,37,100,32,115,101,99,111,110,100,115,46,46,46]).decode(),B);time.sleep(B)
			try:client.reconnect();logging.info(bytes([82,101,99,111,110,110,101,99,116,101,100,32,115,117,99,99,101,115,115,102,117,108,108,121,33]).decode());return
			except Exception as D:logging.error(bytes([37,115,46,32,82,101,99,111,110,110,101,99,116,32,102,97,105,108,101,100,46,32,82,101,116,114,121,105,110,103,46,46,46]).decode(),D)
			B*=A.config.RECONNECT_RATE;B=min(B,A.config.MAX_RECONNECT_DELAY);C+=1
		logging.info(bytes([82,101,99,111,110,110,101,99,116,32,102,97,105,108,101,100,32,97,102,116,101,114,32,37,115,32,97,116,116,101,109,112,116,115,46,32,69,120,105,116,105,110,103,46,46,46]).decode(),C);A.FLAG_EXIT=True
	def on_message(B,client,userdata,msg):
		A=json.loads(msg.payload.decode())
		if bytes([109,97,116,99,104,80,114,105,99,101]).decode()in A and bytes([109,97,116,99,104,81,116,116,121]).decode()in A:
			try:A[bytes([109,97,116,99,104,80,114,105,99,101]).decode()]=float(A[bytes([109,97,116,99,104,80,114,105,99,101]).decode()]);A[bytes([109,97,116,99,104,81,116,116,121]).decode()]=float(A[bytes([109,97,116,99,104,81,116,116,121]).decode()]);append_tick_to_csv(A);logging.debug(f"Received tick data: {A}")
			except ValueError:logging.error(bytes([73,110,118,97,108,105,100,32,100,97,116,97,32,102,111,114,109,97,116,44,32,115,107,105,112,112,105,110,103,32,116,105,99,107,46]).decode())
def run(creds_path,topics):logging.basicConfig(format=bytes([37,40,97,115,99,116,105,109,101,41,115,32,45,32,37,40,108,101,118,101,108,110,97,109,101,41,115,58,32,37,40,109,101,115,115,97,103,101,41,115]).decode(),level=logging.DEBUG);A=Config(creds_path,topics);B=MQTTClient(A);C=B.connect_mqtt();C.loop_forever()
if __name__==bytes([95,95,109,97,105,110,95,95]).decode():parser=argparse.ArgumentParser(description=bytes([77,81,84,84,32,67,108,105,101,110,116,32,67,76,73,32,65,112,112]).decode());parser.add_argument(bytes([99,114,101,100,115,95,112,97,116,104]).decode(),type=str,help=bytes([80,97,116,104,32,116,111,32,116,104,101,32,99,114,101,100,115,46,121,97,109,108,32,102,105,108,101]).decode());parser.add_argument(bytes([45,45,116,111,112,105,99,115]).decode(),type=str,nargs=bytes([43]).decode(),default=[bytes([112,108,97,105,110,116,101,120,116,47,113,117,111,116,101,115,47,100,101,114,105,118,97,116,105,118,101,47,79,72,76,67,47,49,47,86,78,51,48,70,49,77]).decode(),bytes([112,108,97,105,110,116,101,120,116,47,113,117,111,116,101,115,47,115,116,111,99,107,47,116,105,99,107,47,43]).decode()],help=bytes([76,105,115,116,32,111,102,32,116,111,112,105,99,115,32,116,111,32,115,117,98,115,99,114,105,98,101,32,116,111]).decode());args=parser.parse_args();run(args.creds_path,tuple(args.topics))