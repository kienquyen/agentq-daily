import logging,requests
from tenacity import retry,stop_after_attempt,wait_exponential
logger=logging.getLogger(__name__)
class BinanceSpotBase:
	'\n    Base client for interacting with the Binance Spot API.\n    Handles basic request execution, error handling, and robust retries via tenacity.\n    ';BASE_URLS=[bytes([104,116,116,112,115,58,47,47,97,112,105,46,98,105,110,97,110,99,101,46,99,111,109]).decode(),bytes([104,116,116,112,115,58,47,47,97,112,105,45,103,99,112,46,98,105,110,97,110,99,101,46,99,111,109]).decode(),bytes([104,116,116,112,115,58,47,47,97,112,105,49,46,98,105,110,97,110,99,101,46,99,111,109]).decode(),bytes([104,116,116,112,115,58,47,47,97,112,105,50,46,98,105,110,97,110,99,101,46,99,111,109]).decode(),bytes([104,116,116,112,115,58,47,47,97,112,105,51,46,98,105,110,97,110,99,101,46,99,111,109]).decode(),bytes([104,116,116,112,115,58,47,47,97,112,105,52,46,98,105,110,97,110,99,101,46,99,111,109]).decode()];_current_url_index=0
	@classmethod
	def _get_base_url(A):return A.BASE_URLS[A._current_url_index]
	@classmethod
	def _rotate_url(A):A._current_url_index=(A._current_url_index+1)%len(A.BASE_URLS);logger.warning(f"Rotated Binance base URL to {A._get_base_url()}")
	@classmethod
	@retry(stop=stop_after_attempt(5),wait=wait_exponential(multiplier=1,min=2,max=10),reraise=True)
	def _request(cls,endpoint,params=None):
		'\n        Execute a GET request to the given endpoint with rotational domain fallbacks.\n        Only retries on 429, 5xx or Network connection failures.\n        ';C=cls;B=f"{C._get_base_url()}{endpoint}"
		try:D=requests.get(B,params=params,timeout=10);D.raise_for_status();return D.json()
		except requests.exceptions.HTTPError as A:
			if A.response.status_code in[429,500,502,503,504]:C._rotate_url();logger.warning(f"Rotated Binance URL. Retryable HTTP {A.response.status_code} on {B}");raise
			else:logger.error(f"Client Error {A.response.status_code} on {B}: {A.response.text}");return{}
		except requests.exceptions.RequestException as A:C._rotate_url();logger.warning(f"Rotated Binance URL. Network Error on {B}: {A!s}");E=A.response.text if hasattr(A.response,bytes([116,101,120,116]).decode())else str(A);logger.error(f"RequestException on {B}: {E}");raise
		except Exception as A:logger.error(f"Error requesting {B}: {A}");raise