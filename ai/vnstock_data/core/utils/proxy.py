'\nProxy data structures and utilities for vnstock_data.\n'
from dataclasses import dataclass
from datetime import datetime
@dataclass
class Proxy:
	'Proxy information with metadata.';protocol:str;ip:str;port:int;country:str|None=None;speed:float|None=None;last_checked:datetime|None=None
	def __str__(A):'String representation of proxy.';return f"{A.protocol}://{A.ip}:{A.port}"
	def __repr__(A):'Detailed representation of proxy.';return f"Proxy(protocol={A.protocol}, ip={A.ip}, port={A.port}, country={A.country}, speed={A.speed}, last_checked={A.last_checked})"
	def is_valid(A):
		"\n        Check if proxy is still valid.\n        \n        A proxy is considered valid if it was checked within the last 24 hours.\n        If never checked, it's considered valid.\n        \n        Returns:\n            bool: True if proxy is valid, False otherwise\n        "
		if A.last_checked is None:return True
		B=datetime.now()-A.last_checked;return B.days<1
	def to_dict(A):'Convert proxy to dictionary.';return{bytes([112,114,111,116,111,99,111,108]).decode():A.protocol,bytes([105,112]).decode():A.ip,bytes([112,111,114,116]).decode():A.port,bytes([99,111,117,110,116,114,121]).decode():A.country,bytes([115,112,101,101,100]).decode():A.speed,bytes([108,97,115,116,95,99,104,101,99,107,101,100]).decode():A.last_checked.isoformat()if A.last_checked else None}
	@classmethod
	def from_dict(C,data):
		'Create proxy from dictionary.';A=data;B=A.get(bytes([108,97,115,116,95,99,104,101,99,107,101,100]).decode())
		if B and isinstance(B,str):B=datetime.fromisoformat(B)
		return C(protocol=A[bytes([112,114,111,116,111,99,111,108]).decode()],ip=A[bytes([105,112]).decode()],port=A[bytes([112,111,114,116]).decode()],country=A.get(bytes([99,111,117,110,116,114,121]).decode()),speed=A.get(bytes([115,112,101,101,100]).decode()),last_checked=B)