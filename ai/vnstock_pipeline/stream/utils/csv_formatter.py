'\nCSV Formatting Utilities\n========================\n\nUtilities for formatting and reordering CSV files with timestamp as first column and index.\n'
import os,pandas as pd,logging
from typing import Optional
logger=logging.getLogger(__name__)
def format_csv_with_timestamp_index(csv_path,output_path=None):
	'\n    Reformat a CSV file to have timestamp as first column and set as index.\n    \n    Args:\n        csv_path (str): Path to the input CSV file\n        output_path (str, optional): Path to save formatted CSV. \n                                    If None, overwrites original.\n    \n    Returns:\n        bool: True if successful, False otherwise\n    ';F=False;D='timestamp';C=True;B=csv_path
	try:
		if not os.path.exists(B):logger.error(f"CSV file not found: {B}");return F
		A=pd.read_csv(B)
		if A.empty:logger.warning(f"CSV is empty: {B}");return C
		if D not in A.columns:logger.warning(f"No timestamp column in {B}");return C
		G=A.pop(D);A.insert(0,D,G);A=A.set_index(D);E=output_path or B;os.makedirs(os.path.dirname(E)or'.',exist_ok=C);A.to_csv(E);logger.info(f"Formatted CSV: {B} ({len(A.columns)} columns, {len(A)} rows)");return C
	except Exception as H:logger.error(f"Error formatting CSV {B}: {H}");return F
def format_all_csvs_in_directory(directory,pattern='market_data_*.csv'):
	'\n    Format all CSV files in a directory.\n    \n    Args:\n        directory (str): Directory containing CSV files\n        pattern (str): Glob pattern for CSV files to format\n    \n    Returns:\n        int: Number of files successfully formatted\n    ';A=directory
	try:
		import glob;C=glob.glob(os.path.join(A,pattern));B=0
		for D in C:
			if format_csv_with_timestamp_index(D):B+=1
		logger.info(f"Formatted {B}/{len(C)} CSV files in {A}");return B
	except Exception as E:logger.error(f"Error formatting CSVs in {A}: {E}");return 0