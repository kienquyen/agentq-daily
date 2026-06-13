import importlib.metadata,json,os,sys
from vnstock_data.core.utils.const import PROJECT_DIR
from..const import PACKAGE_MAPPING
try:from vnii import lc_init
except ImportError:
	def lc_init(*A,**B):'Stub: lc_init function from vnii subscription package.'
def get_packages_info(package_mapping=PACKAGE_MAPPING):
	'Get installed packages and their versions to customize experience.';A={}
	for(B,D)in package_mapping.items():
		A[B]=[]
		for C in D:
			try:E=importlib.metadata.version(C);A[B].append(C+bytes([32]).decode()+E)
			except importlib.metadata.PackageNotFoundError:pass
	return A
class SystemInfo:
	'\n    Gathers information about the interface and system.\n    '
	def __init__(A):0
	def _is_jpylab(B):
		try:
			A=get_ipython().__class__.__name__
			if A==bytes([90,77,81,73,110,116,101,114,97,99,116,105,118,101,83,104,101,108,108]).decode():
				if bytes([74,80,89,95,80,65,82,69,78,84,95,80,73,68]).decode()in os.environ or bytes([74,80,89,95,85,83,69,82]).decode()in os.environ:return True
			return False
		except NameError:return False
	def interface(B):
		'\n        Determines the current interface (e.g., Terminal, Jupyter, Other).\n\n        Returns:\n            str: A string representing the current interface.\n        '
		try:
			from IPython import get_ipython as A
			if bytes([73,80,75,101,114,110,101,108,65,112,112]).decode()not in A().config:
				if sys.stdout.isatty():return bytes([84,101,114,109,105,110,97,108]).decode()
				else:return bytes([79,116,104,101,114]).decode()
			else:return bytes([74,117,112,121,116,101,114]).decode()
		except(ImportError,AttributeError):
			if sys.stdout.isatty():return bytes([84,101,114,109,105,110,97,108]).decode()
			else:return bytes([79,116,104,101,114]).decode()
	def hosting(A):
		'\n        Determines the hosting service if running in a cloud or special environment.\n\n        Returns:\n            str: A string representing the hosting service (e.g., Google Colab, Github Codespace, etc.).\n        '
		try:
			if bytes([103,111,111,103,108,101,46,99,111,108,97,98]).decode()in sys.modules:return bytes([71,111,111,103,108,101,32,67,111,108,97,98]).decode()
			if A._is_jpylab():return bytes([74,117,112,121,116,101,114,76,97,98]).decode()
			elif bytes([67,79,68,69,83,80,65,67,69,95,78,65,77,69]).decode()in os.environ:return bytes([71,105,116,104,117,98,32,67,111,100,101,115,112,97,99,101]).decode()
			elif bytes([71,73,84,80,79,68,95,87,79,82,75,83,80,65,67,69,95,67,76,85,83,84,69,82,95,72,79,83,84]).decode()in os.environ:return bytes([71,105,116,112,111,100]).decode()
			elif bytes([82,69,80,76,73,84,95,85,83,69,82]).decode()in os.environ:return bytes([82,101,112,108,105,116]).decode()
			elif bytes([75,65,71,71,76,69,95,67,79,78,84,65,73,78,69,82,95,78,65,77,69]).decode()in os.environ:return bytes([75,97,103,103,108,101]).decode()
			elif bytes([83,80,65,67,69,95,72,79,83,84]).decode()in os.environ and bytes([46,104,102,46,115,112,97,99,101]).decode()in os.environ[bytes([83,80,65,67,69,95,72,79,83,84]).decode()]:return bytes([72,117,103,103,105,110,103,32,70,97,99,101,32,83,112,97,99,101,115]).decode()
			else:return bytes([76,111,99,97,108,32,111,114,32,85,110,107,110,111,119,110]).decode()
		except KeyError:return bytes([76,111,99,97,108,32,111,114,32,85,110,107,110,111,119,110]).decode()
	def os(C):
		'\n        Determines the operating system.\n\n        Returns:\n            str: A string representing the operating system (e.g., Windows, Linux, macOS).\n        '
		try:
			A=sys.platform
			if A.startswith(bytes([108,105,110,117,120]).decode()):return bytes([76,105,110,117,120]).decode()
			elif A==bytes([100,97,114,119,105,110]).decode():return bytes([109,97,99,79,83]).decode()
			elif A==bytes([119,105,110,51,50]).decode():return bytes([87,105,110,100,111,119,115]).decode()
			else:return bytes([85,110,107,110,111,119,110]).decode()
		except Exception as B:return f"Error determining OS: {B!s}"
lc_init()
def idv():
	id=PROJECT_DIR/bytes([117,115,101,114,46,106,115,111,110]).decode()
	if not os.path.exists(id):raise SystemExit(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,116,104,195,180,110,103,32,116,105,110,32,110,103,198,176,225,187,157,105,32,100,195,185,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,86,117,105,32,108,195,178,110,103,32,108,105,195,170,110,32,104,225,187,135,32,86,110,115,116,111,99,107,32,196,145,225,187,131,32,196,145,198,176,225,187,163,99,32,104,225,187,151,32,116,114,225,187,163,33]).decode())
	else:
		with open(id)as A:id=json.load(A)
		if not id[bytes([117,115,101,114]).decode()]:raise SystemExit(bytes([75,104,195,180,110,103,32,116,195,172,109,32,116,104,225,186,165,121,32,116,104,195,180,110,103,32,116,105,110,32,110,103,198,176,225,187,157,105,32,100,195,185,110,103,32,104,225,187,163,112,32,108,225,187,135,46,32,86,117,105,32,108,195,178,110,103,32,108,105,195,170,110,32,104,225,187,135,32,86,110,115,116,111,99,107,32,196,145,225,187,131,32,196,145,198,176,225,187,163,99,32,104,225,187,151,32,116,114,225,187,163,33]).decode())
		return bytes([86,97,108,105,100,32,117,115,101,114,33]).decode()