_B='last_updated'
_A='site_overrides'
import os,json
from datetime import datetime
from typing import Dict
from vnstock_news.config.sites import SITES_CONFIG as BASE_SITES
from vnstock_news.utils.logger import setup_logger
class DynamicConfig:
	'Manages dynamic configuration that extends the base configuration.'
	def __init__(A,config_file='dynamic_config.json',debug=False):A.logger=setup_logger(A.__class__.__name__,debug);A.config_file=config_file;A.base_sites=BASE_SITES;A.dynamic_data=A._load_dynamic_config()
	def _load_dynamic_config(A):
		'Load dynamic configuration from file if it exists.'
		if os.path.exists(A.config_file):
			try:
				with open(A.config_file,'r',encoding='utf-8')as B:return json.load(B)
			except Exception as C:A.logger.error(f"Error loading dynamic config: {C}")
		return{_B:None,_A:{}}
	def _save_dynamic_config(A):
		'Save dynamic configuration to file.'
		try:
			with open(A.config_file,'w',encoding='utf-8')as B:json.dump(A.dynamic_data,B,indent=2)
		except Exception as C:A.logger.error(f"Error saving dynamic config: {C}")
	def update_sitemap_url(A,site_name,new_url):
		'Update the sitemap URL for a site.';C=new_url;B=site_name
		if B not in A.base_sites:A.logger.error(f"Site '{B}' is not in the base configuration");return False
		if _A not in A.dynamic_data:A.dynamic_data[_A]={}
		if B not in A.dynamic_data[_A]:A.dynamic_data[_A][B]={}
		A.dynamic_data[_A][B]['sitemap_url']=C;A.dynamic_data[_B]=datetime.now().isoformat();A._save_dynamic_config();A.logger.info(f"Updated sitemap URL for {B}: {C}");return True
	def get_sites_config(B):
		'Get the combined configuration with overrides applied.';A=dict(B.base_sites)
		for(C,D)in B.dynamic_data.get(_A,{}).items():
			if C in A:A[C].update(D)
		return A