"\nUtility module for managing and displaying startup messages via logging.\nTracks message display counts using a local JSON state file.\n\nTo suppress startup messages, configure logging in your code:\n    import logging\n    logging.getLogger('vnstock_data.core.utils.startup').setLevel(logging.WARNING)\n\nOr set environment variable:\n    export VNSTOCK_STARTUP_LOG_LEVEL=WARNING\n"
import datetime,json,logging
from pathlib import Path
from vnstock_data.core.config.messages import STARTUP_MESSAGES
logger=logging.getLogger(__name__)
def _get_state_file_path():
	'Get the path to the local state file for tracking startup messages.';B=Path.home();A=B/bytes([46,118,110,115,116,111,99,107]).decode()
	if not A.exists():
		try:A.mkdir(parents=True,exist_ok=True)
		except Exception:pass
	return A/bytes([115,116,97,114,116,117,112,95,115,116,97,116,101,46,106,115,111,110]).decode()
def _load_state():
	'Load the message display state from the local JSON file.';A=_get_state_file_path()
	try:
		if A.exists():
			with open(A,encoding=bytes([117,116,102,45,56]).decode())as B:return json.load(B)
	except Exception:pass
	return{}
def _save_state(state):
	'Save the message display state to the local JSON file.';A=_get_state_file_path()
	try:
		if not A.parent.exists():A.parent.mkdir(parents=True,exist_ok=True)
		with open(A,bytes([119]).decode(),encoding=bytes([117,116,102,45,56]).decode())as B:json.dump(state,B)
	except Exception:pass
def display_startup_messages():
	'\n    Check and display active startup messages based on configured constraints.\n    Updates the display count in the local state file.\n    ';D=False;B=_load_state();I=datetime.datetime.now()
	for A in STARTUP_MESSAGES:
		C=A.get(bytes([105,100]).decode());E=A.get(bytes([116,101,120,116]).decode(),'');F=A.get(bytes([109,97,120,95,100,105,115,112,108,97,121,115]).decode());G=A.get(bytes([101,120,112,105,114,101,115,95,97,116]).decode())
		if not C or not E:continue
		if G:
			try:
				J=datetime.datetime.fromisoformat(G)
				if I>J:continue
			except ValueError:pass
		H=B.get(C,0)
		if F is not None and H>=F:continue
		logger.info(E);B[C]=H+1;D=True
	if D:_save_state(B)