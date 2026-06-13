_C=', '
_B=True
_A=None
import re
from typing import List,Dict,Union,Optional,Any,Callable
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
from vnstock_news.utils.logger import setup_logger
class ValidationError(Exception):'Exception raised for validation errors.'
class InputValidator:
	'\n    Validates input parameters for vnnews functions.\n    '
	def __init__(A,debug=False):'\n        Initialize the validator.\n        \n        Parameters:\n            debug (bool): Enable debug logging.\n        ';A.logger=setup_logger(A.__class__.__name__,debug)
	def validate_url(D,url,required=_B):
		'\n        Validate a URL.\n        \n        Parameters:\n            url (str): URL to validate.\n            required (bool): Whether the URL is required.\n            \n        Returns:\n            str: The validated URL.\n            \n        Raises:\n            ValidationError: If URL is invalid.\n        ';A=url
		if not A and not required:return A
		if not A:raise ValidationError('URL is required.')
		A=A.strip()
		try:
			B=urlparse(A)
			if not all([B.scheme,B.netloc]):raise ValidationError(f"Invalid URL format: {A}")
			if B.scheme not in['http','https']:raise ValidationError(f"URL must use HTTP or HTTPS: {A}")
		except Exception as C:raise ValidationError(f"URL parsing error: {C}")
		return A
	def validate_urls(C,urls):
		'\n        Validate a list of URLs.\n        \n        Parameters:\n            urls (str or list): Single URL or list of URLs to validate.\n            \n        Returns:\n            list: List of validated URLs.\n            \n        Raises:\n            ValidationError: If any URL is invalid.\n        ';A=urls
		if isinstance(A,str):A=[A]
		if not A:raise ValidationError('At least one URL is required.')
		B=[]
		for(D,E)in enumerate(A):
			try:B.append(C.validate_url(E))
			except ValidationError as F:raise ValidationError(f"URL at index {D} is invalid: {F}")
		return B
	def validate_site_name(D,site_name,SITES_CONFIG,required=_B):
		'\n        Validate a site name against the list of supported sites.\n        \n        Parameters:\n            site_name (str): Site name to validate.\n            SITES_CONFIG (list): List of supported site names.\n            required (bool): Whether the site name is required.\n            \n        Returns:\n            str or None: The validated site name or None if not required and not provided.\n            \n        Raises:\n            ValidationError: If site name is invalid.\n        ';C=required;B=SITES_CONFIG;A=site_name
		if not A and not C:return
		if not A and C:raise ValidationError('Site name is required.')
		A=A.strip().lower()
		if A not in B:raise ValidationError(f"Invalid site name: '{A}'. Supported sites: {_C.join(B)}")
		return A
	def validate_config(C,config,required_keys):
		'\n        Validate configuration dictionary against required keys.\n        \n        Parameters:\n            config (dict): Configuration to validate.\n            required_keys (list): List of required configuration keys.\n            \n        Returns:\n            dict: The validated configuration.\n            \n        Raises:\n            ValidationError: If configuration is invalid.\n        ';A=config
		if not A:raise ValidationError('Configuration dictionary is required.')
		if not isinstance(A,dict):raise ValidationError(f"Configuration must be a dictionary, not {type(A).__name__}.")
		B=[B for B in required_keys if B not in A]
		if B:raise ValidationError(f"Missing required configuration keys: {_C.join(B)}")
		return A
	def validate_time_frame(E,time_frame):
		"\n        Validate a time frame string (e.g. '1h', '2d', '30m').\n        \n        Parameters:\n            time_frame (str): Time frame to validate.\n            \n        Returns:\n            str: The validated time frame.\n            \n        Raises:\n            ValidationError: If time frame is invalid.\n        ";A=time_frame
		if not A:raise ValidationError('Time frame is required.')
		A=A.strip().lower();D='^(\\d+)([hdm])$';C=re.match(D,A)
		if not C:raise ValidationError(f"Invalid time frame format: '{A}'. Use format like '1h' for 1 hour, '2d' for 2 days, or '30m' for 30 minutes.")
		B,F=C.groups()
		try:
			B=int(B)
			if B<=0:raise ValidationError(f"Time frame value must be positive, got {B}.")
		except ValueError:raise ValidationError(f"Time frame value must be an integer, got '{B}'.")
		return A
	def validate_date(D,date_str,format_str='%Y-%m-%d'):
		'\n        Validate a date string.\n        \n        Parameters:\n            date_str (str): Date string to validate.\n            format_str (str): Expected date format string.\n            \n        Returns:\n            datetime: The validated date as a datetime object.\n            \n        Raises:\n            ValidationError: If date is invalid.\n        ';B=format_str;A=date_str
		if not A:raise ValidationError('Date string is required.')
		A=A.strip()
		try:return datetime.strptime(A,B)
		except ValueError as C:raise ValidationError(f"Invalid date format: {C}. Expected format: {B}")
	def validate_positive_int(D,value,param_name,required=_B,default=_A):
		'\n        Validate a positive integer parameter.\n        \n        Parameters:\n            value (any): Value to validate.\n            param_name (str): Parameter name for error messages.\n            required (bool): Whether the parameter is required.\n            default (int, optional): Default value if not provided and not required.\n            \n        Returns:\n            int or None: The validated integer or default.\n            \n        Raises:\n            ValidationError: If value is invalid.\n        ';B=param_name;A=value
		if A is _A:
			if required:raise ValidationError(f"{B} is required.")
			return default
		try:
			C=int(A)
			if C<=0:raise ValidationError(f"{B} must be positive, got {C}.")
			return C
		except ValueError:raise ValidationError(f"{B} must be an integer, got '{A}'.")
	def validate_dataframe(B,df,required_columns):
		'\n        Validate a pandas DataFrame for required columns.\n        \n        Parameters:\n            df (DataFrame): DataFrame to validate.\n            required_columns (list): List of required column names.\n            \n        Returns:\n            DataFrame: The validated DataFrame.\n            \n        Raises:\n            ValidationError: If DataFrame is invalid.\n        '
		if df is _A or df.empty:raise ValidationError('DataFrame cannot be None or empty.')
		A=[A for A in required_columns if A not in df.columns]
		if A:raise ValidationError(f"Missing required columns: {_C.join(A)}")
		return df
	def validate_sort_order(B,sort_order):
		"\n        Validate sort order parameter.\n        \n        Parameters:\n            sort_order (str): Sort order ('asc' or 'desc').\n            \n        Returns:\n            str: The validated sort order.\n            \n        Raises:\n            ValidationError: If sort order is invalid.\n        ";A=sort_order
		if not A:raise ValidationError('Sort order is required.')
		A=A.lower().strip()
		if A not in['asc','desc']:raise ValidationError(f"Invalid sort order: '{A}'. Must be 'asc' or 'desc'.")
		return A
	def validate_choice(E,value,choices,param_name,required=_B,default=_A):
		'\n        Validate that a value is one of the allowed choices.\n        \n        Parameters:\n            value (any): Value to validate.\n            choices (list): List of allowed choices.\n            param_name (str): Parameter name for error messages.\n            required (bool): Whether the parameter is required.\n            default (any): Default value if not provided and not required.\n            \n        Returns:\n            any: The validated value or default.\n            \n        Raises:\n            ValidationError: If value is invalid.\n        ';C=param_name;B=choices;A=value
		if A is _A:
			if required:raise ValidationError(f"{C} is required.")
			return default
		if A not in B:D=_C.join([str(A)for A in B]);raise ValidationError(f"{C} must be one of: {D}, got '{A}'.")
		return A
	def validate(D,validation_dict):
		"\n        Run multiple validations at once.\n        \n        Parameters:\n            validation_dict (dict): Dictionary mapping parameter names to validation specs.\n                Each validation spec is a dict with keys:\n                - 'value': The value to validate\n                - 'validator': The validation method to use\n                - Other keys are passed as kwargs to the validator\n        \n        Returns:\n            dict: Dictionary of validated values.\n            \n        Raises:\n            ValidationError: If any validation fails.\n            \n        Example:\n            validator.validate({\n                'url': {\n                    'value': 'https://example.com',\n                    'validator': 'validate_url'\n                },\n                'count': {\n                    'value': 10,\n                    'validator': 'validate_positive_int',\n                    'param_name': 'Item count'\n                }\n            })\n        ";E={};A=[]
		for(F,B)in validation_dict.items():
			G=B.pop('value');C=B.pop('validator')
			if not hasattr(D,C):A.append(f"Unknown validator: {C}");continue
			H=getattr(D,C)
			try:E[F]=H(G,**B)
			except ValidationError as I:A.append(f"{F}: {str(I)}")
		if A:raise ValidationError('\n'.join(A))
		return E