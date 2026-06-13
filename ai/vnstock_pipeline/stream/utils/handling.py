'\nUtilities\n========\n\nUtility functions for the vnstock_pipeline.stream package.\n'
_A=None
import logging,os,sys
from typing import Optional
def setup_logging(level=logging.INFO,log_file='vnstock_pipeline.stream.log',console=True,file_level=_A,console_level=_A):
	'\n    Set up logging for the vnstock_pipeline.stream package.\n    \n    Args:\n        level (int): Default logging level\n        log_file (Optional[str]): Path to log file or None to disable file logging\n        console (bool): Whether to log to console\n        file_level (Optional[int]): Specific level for file logging (defaults to level)\n        console_level (Optional[int]): Specific level for console logging (defaults to level)\n    ';C=log_file;B=level;A=logging.getLogger();A.setLevel(B)
	for G in A.handlers[:]:A.removeHandler(G)
	H=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s');I=logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	if C:
		D=os.path.dirname(C)
		if D and not os.path.exists(D):os.makedirs(D,exist_ok=True)
		E=logging.FileHandler(C);E.setLevel(file_level or B);E.setFormatter(H);A.addHandler(E)
	if console:F=logging.StreamHandler(sys.stdout);F.setLevel(console_level or B);F.setFormatter(I);A.addHandler(F)
	logging.info('Logging initialized')
def chunk_list(lst,chunk_size):'\n    Split a list into smaller chunks.\n    \n    Args:\n        lst (list): The list to split\n        chunk_size (int): The maximum size of each chunk\n        \n    Returns:\n        list: List of chunks\n    ';A=chunk_size;return[lst[B:B+A]for B in range(0,len(lst),A)]
def safe_float(value,default=_A):
	'\n    Safely convert a value to float.\n    \n    Args:\n        value: The value to convert\n        default: Default value if conversion fails\n        \n    Returns:\n        float or default: The converted value or default\n    '
	try:return float(value)
	except(ValueError,TypeError):return default
def safe_int(value,default=_A):
	'\n    Safely convert a value to int.\n    \n    Args:\n        value: The value to convert\n        default: Default value if conversion fails\n        \n    Returns:\n        int or default: The converted value or default\n    '
	try:return int(value)
	except(ValueError,TypeError):return default