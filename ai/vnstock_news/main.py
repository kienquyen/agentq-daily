_X='pattern_type'
_W='collected_at'
_V='%Y%m%d'
_U='sitemap_update_interval_hours'
_T='clean_content'
_S='max_concurrency'
_R='cache_ttl'
_Q='cache_enabled'
_P='time_window'
_O='current_url'
_N='articles_per_site'
_M='logs_dir'
_L='archive_dir'
_K='interval_minutes'
_J='sitemap_url'
_I='total_collected'
_H=False
_G='debug'
_F='sites_to_monitor'
_E='output_dir'
_D='by_site'
_C='new_this_run'
_B=True
_A='sitemap'
import os,time,asyncio,schedule,pandas as pd
from datetime import datetime,timedelta
import logging,json
from vnstock_news.api.enhanced import EnhancedNewsCrawler
from vnstock_news.utils.cleaner import ContentCleaner
from vnstock_news.utils.cache import Cache
from vnstock_news.config.sites import SITES_CONFIG
from vnstock_news.config.dynamic_config import DynamicConfig
from vnstock_news.config.sitemap_resolver import DynamicSitemapResolver
from vnstock_news.utils.logger import setup_logger
from vnstock_news.trending.analyzer import TrendingAnalyzer
CONFIG={_K:15,_E:'output/news',_L:'output/archive',_M:'logs',_F:list(SITES_CONFIG.keys()),_N:500,_P:'12h',_Q:_B,_R:3600,_S:8,_T:_B,_G:_H,_U:24}
os.makedirs(CONFIG[_E],exist_ok=_B)
os.makedirs(CONFIG[_L],exist_ok=_B)
os.makedirs(CONFIG[_M],exist_ok=_B)
TEMP_DATA_DIR='temp_data'
os.makedirs(TEMP_DATA_DIR,exist_ok=_B)
def setup_application_logging():A=os.path.join(CONFIG[_M],f"news_monitor_{datetime.now().strftime(_V)}.log");logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',handlers=[logging.FileHandler(A),logging.StreamHandler()]);return logging.getLogger('news_monitor')
logger=setup_application_logging()
sitemap_resolver=DynamicSitemapResolver(debug=CONFIG[_G])
dynamic_config=DynamicConfig(config_file='dynamic_news_config.json',debug=CONFIG[_G])
crawler=EnhancedNewsCrawler(cache_enabled=CONFIG[_Q],cache_ttl=CONFIG[_R],max_concurrency=CONFIG[_S],debug=CONFIG[_G])
cleaner=ContentCleaner(debug=CONFIG[_G])
trends_cache=Cache(Cache.SQLITE,db_file=os.path.join(TEMP_DATA_DIR,'news_trends.db'),ttl=604800)
sitemap_update_cache=Cache(Cache.SQLITE,db_file=os.path.join(TEMP_DATA_DIR,'sitemap_updates.db'),ttl=2592000)
stop_words_path='vnstock_news/config/vietnamese-stopwords.txt'
trending_analyzer=TrendingAnalyzer(stop_words_file=stop_words_path,min_token_length=3)
class ArticleStore:
	def __init__(A,db_file=os.path.join(TEMP_DATA_DIR,'collected_articles.db')):A.cache=Cache(Cache.SQLITE,db_file=db_file,ttl=2592000)
	def add_article(C,article_dict):
		A=article_dict;B=A.get('url')
		if not B:return _H
		A[_W]=datetime.now().isoformat();C.cache.set(B,A);return _B
	def get_article(A,url):return A.cache.get(url)
	def get_recent_articles(B,hours=24):
		C=[];D=datetime.now()-timedelta(hours=hours)
		for E in B._get_all_keys():
			A=B.cache.get(E)
			if A:
				F=datetime.fromisoformat(A.get(_W,'2000-01-01T00:00:00'))
				if F>=D:C.append(A)
		return C
	def _get_all_keys(A):return A.cache._get_all_keys()if hasattr(A.cache,'_get_all_keys')else[]
seen_articles=set()
article_stats={_I:0,_C:0,_D:{}}
article_store=ArticleStore()
def update_dynamic_sitemaps():
	'Update dynamic sitemaps for sites with time-dependent URLs';L='last_sitemap_update';D='site_overrides';logger.info('Checking for sitemap updates...');H=sitemap_update_cache.get(L);I=datetime.now()
	if H:
		J=(I-datetime.fromisoformat(H)).total_seconds()/3600
		if J<CONFIG[_U]:logger.info(f"Skipping sitemap update - last update was {J:.1f} hours ago");return
	M=dynamic_config.get_sites_config();E=0
	for A in CONFIG[_F]:
		C=M.get(A,{})
		if _A in C:
			try:
				K=C[_A];N=K.get(_X);O=K.get(_O,'')
				if N in['monthly','incremental']:
					B=sitemap_resolver.resolve_sitemap_url(A,C)
					if B and B!=O:
						logger.info(f"Updating sitemap URL for {A}: {B}")
						if _A not in dynamic_config.dynamic_data.get(D,{}).get(A,{}):
							if A not in dynamic_config.dynamic_data.get(D,{}):dynamic_config.dynamic_data[D][A]={}
							dynamic_config.dynamic_data[D][A][_A]=dict(C[_A])
						dynamic_config.dynamic_data[D][A][_A][_O]=B;E+=1
					else:logger.debug(f"No sitemap update needed for {A}")
			except Exception as F:logger.error(f"Error updating sitemap for {A}: {F}")
		elif _J in C:
			try:
				G=C.get(_J,'')
				if not G:continue
				if any(A in G for A in['-20','news-20']):
					B=sitemap_resolver.resolve_sitemap_url(A,C)
					if B and B!=G:logger.info(f"Updating sitemap URL for {A}: {B}");dynamic_config.update_sitemap_url(A,B);E+=1
			except Exception as F:logger.error(f"Error checking sitemap for {A}: {F}")
	if E>0:dynamic_config._save_dynamic_config()
	sitemap_update_cache.set(L,I.isoformat());logger.info(f"Sitemap update check completed - {E} updates made")
async def fetch_news_from_site(site_name,max_articles,time_window):
	'Fetch news from a single site using dynamic sitemap resolution';F='urls';D='rss';B=site_name;logger.info(f"Fetching news from {B}...");A=dynamic_config.get_sites_config().get(B)
	if not A:logger.error(f"Site configuration not found for {B}");return pd.DataFrame()
	C=[]
	if A.get(D)and A[D].get(F):C=A[D][F]
	elif _A in A:
		E=sitemap_resolver.get_sitemap_url(B,A)
		if E:C=[E]
	elif A.get(_J):C=[A[_J]]
	if not C:logger.warning(f"No sources found for {B}");return pd.DataFrame()
	try:G=await crawler.fetch_articles_async(sources=C,site_name=B,max_articles=max_articles,time_frame=time_window,clean_content=CONFIG[_T],sort_order='desc');return G
	except Exception as H:logger.error(f"Error fetching articles from {B}: {H}");return pd.DataFrame()
async def process_new_articles(articles_df,site_name):
	'Process newly fetched articles and update trending topics';E=articles_df;A=site_name
	if E.empty:logger.info(f"No articles found for {A}");return 0
	F=E.to_dict('records');C=0
	for B in F:
		B['site_name']=A;D=B.get('url')
		if D and D not in seen_articles:seen_articles.add(D);C+=1;article_store.add_article(B);G=f"{B.get("title","")} {B.get("short_description","")}";trending_analyzer.update_trends(G)
	article_stats[_C]+=C;article_stats[_I]+=len(F)
	if A not in article_stats[_D]:article_stats[_D][A]=0
	article_stats[_D][A]+=C;return C
def save_current_data(site_name,articles_df):
	'Save current articles to CSV';E='utf-8-sig';B=site_name;A=articles_df
	if A.empty:return
	C=os.path.join(CONFIG[_E],f"{B}_news.csv");A.to_csv(C,index=_H,encoding=E);logger.debug(f"Saved {len(A)} articles to {C}");F=datetime.now().strftime(_V);D=os.path.join(CONFIG[_L],F);os.makedirs(D,exist_ok=_B);G=os.path.join(D,f"{B}_{datetime.now().strftime("%H%M")}.csv");A.to_csv(G,index=_H,encoding=E)
def generate_report():
	'Generate a summary report of collected articles and trending topics';L='utf-8';I='N/A';D='\n';C='-';J=trending_analyzer.get_top_trends(20);E=article_store.get_recent_articles(hours=24);K={'generated_at':datetime.now().isoformat(),'statistics':{_I:article_stats[_I],'collected_last_24h':len(E),_D:article_stats[_D]},'trending_topics':[{'phrase':A,'count':B}for(A,B)in J.items()],'latest_run':{'timestamp':datetime.now().isoformat(),'new_articles':article_stats[_C]}};M=os.path.join(CONFIG[_E],'news_report.json')
	with open(M,'w',encoding=L)as A:json.dump(K,A,indent=2,ensure_ascii=_H)
	N=os.path.join(CONFIG[_E],'news_summary.txt')
	with open(N,'w',encoding=L)as A:
		O=datetime.now().strftime('%Y-%m-%d %H:%M');A.write(f"News Monitor Report - {O}\n");A.write('='*50+'\n\n');A.write('STATISTICS\n');A.write(C*50+D);P=article_stats[_I];A.write(f"Total articles collected: {P}\n");Q=len(E);A.write(f"Articles in the last 24 hours: {Q}\n");R=article_stats[_C];A.write(f"New articles in last run: {R}\n\n");A.write('BY SITE\n');A.write(C*50+D)
		for(S,F)in article_stats[_D].items():A.write(f"{S}: {F} articles\n")
		A.write('\nTRENDING TOPICS\n');A.write(C*50+D)
		for(T,(U,F))in enumerate(J.items(),1):A.write(f"{T}. {U}: {F} mentions\n")
		A.write('\nSITEMAP STATUS\n');A.write(C*50+D);V=dynamic_config.get_sites_config()
		for G in CONFIG[_F]:
			B=V.get(G,{})
			if _A in B:H=B[_A].get(_O,I);W=B[_A].get(_X,I);A.write(f"{G}: {H} (Type: {W})\n")
			else:H=B.get(_J,I);A.write(f"{G}: {H}\n")
	logger.info(f"Generated news report with {len(E)} recent articles");return K
async def fetch_all_news():
	'Fetch news from all monitored sites and process articles.';E='%H:%M:%S';article_stats[_C]=0;logger.info(f"Starting news collection at {datetime.now().strftime(E)}");logger.info(f"Monitoring {len(CONFIG[_F])} sites with {CONFIG[_N]} articles per site");D=[]
	for A in CONFIG[_F]:B=fetch_news_from_site(site_name=A,max_articles=CONFIG[_N],time_window=CONFIG[_P]);D.append((A,B))
	for(A,B)in D:
		try:C=await B;F=await process_new_articles(C,A);logger.info(f"Processed {A}: {len(C)} articles ({F} new)");save_current_data(A,C)
		except Exception as G:logger.error(f"Error processing results for {A}: {G}")
	H=generate_report();logger.info(f"Completed news collection at {datetime.now().strftime(E)}");logger.info(f"Collected {article_stats[_C]} new articles this run");article_stats[_C]=0
def run_news_collection():'Run the news collection process.';asyncio.run(fetch_all_news())
def daily_maintenance():'Perform daily maintenance tasks.';logger.info('Running daily maintenance...');update_dynamic_sitemaps();logger.info('Daily maintenance completed')
def main():
	logger.info('Starting news monitoring service');logger.info(f"Interval: {CONFIG[_K]} minutes");logger.info(f"Output directory: {CONFIG[_E]}");logger.info(f"Monitoring sites: {", ".join(CONFIG[_F])}");update_dynamic_sitemaps();schedule.every(CONFIG[_K]).minutes.do(run_news_collection);schedule.every().day.at('00:05').do(daily_maintenance);run_news_collection();logger.info('Monitoring service running. Press Ctrl+C to stop.')
	try:
		while _B:schedule.run_pending();time.sleep(1)
	except KeyboardInterrupt:logger.info('News monitoring service stopped by user')
if __name__=='__main__':main()