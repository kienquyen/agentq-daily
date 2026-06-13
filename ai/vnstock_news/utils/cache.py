_H='SELECT COUNT(*) FROM cache'
_G='DELETE FROM cache WHERE key = ?'
_F='access_count'
_E='timestamp'
_D='memory'
_C=None
_B=True
_A=False
import os,json,hashlib,time,sqlite3
from typing import Any,Dict,Optional,Union,Tuple
from functools import wraps
import pickle,threading
from vnstock_news.utils.logger import setup_logger
def cached(ttl=_C,key_fn=_C):
	'\n    Decorator for caching function results.\n    \n    Parameters:\n        ttl (int, optional): Custom TTL in seconds\n        key_fn (callable, optional): Custom function to generate cache key\n        \n    Usage:\n        @cached(ttl=3600)\n        def fetch_data(url, params):\n            # Expensive operation\n            return results\n    ';E=key_fn
	def A(func):
		A=func;F=Cache(cache_type=Cache.MEMORY,ttl=ttl or 3600)
		@wraps(A)
		def B(*B,**C):
			if E:D=E(*B,**C)
			else:D={'func':A.__name__,'args':B,'kwargs':sorted(C.items())}
			G=F.get(D)
			if G is not _C:return G
			H=A(*B,**C);F.set(D,H);return H
		return B
	return A
class Cache:
	'\n    A flexible caching system supporting memory, file, and SQLite backends.\n    ';MEMORY=_D;FILE='file';SQLITE='sqlite'
	def __init__(A,cache_type=_D,cache_dir='.cache',ttl=3600,max_size=1000,db_file='cache.db',debug=_A):
		"\n        Initialize the cache system.\n        \n        Parameters:\n            cache_type (str): Cache backend type: 'memory', 'file', or 'sqlite'.\n            cache_dir (str): Directory for file cache storage.\n            ttl (int): Default cache TTL in seconds.\n            max_size (int): Maximum number of items to store in memory cache.\n            db_file (str): Filename for SQLite cache database.\n            debug (bool): Enable debug logging.\n        ";B=cache_type;A.logger=setup_logger(A.__class__.__name__,debug);A.cache_type=B;A.cache_dir=cache_dir;A.ttl=ttl;A.max_size=max_size;A.db_file=db_file;A._lock=threading.RLock()
		if A.cache_type==A.MEMORY:A._cache={};A._timestamps={};A._access_count={}
		elif A.cache_type==A.FILE:os.makedirs(A.cache_dir,exist_ok=_B)
		elif A.cache_type==A.SQLITE:A._init_sqlite_cache()
		else:raise ValueError(f"Unsupported cache type: {B}")
		A.logger.info(f"Initialized {B} cache system")
	def _init_sqlite_cache(A):'Initialize SQLite cache database.';A.conn=sqlite3.connect(A.db_file,check_same_thread=_A);B=A.conn.cursor();B.execute('\n            CREATE TABLE IF NOT EXISTS cache (\n                key TEXT PRIMARY KEY,\n                value BLOB,\n                timestamp REAL,\n                access_count INTEGER\n            )\n        ');B.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON cache (timestamp)');A.conn.commit()
	def _get_key(C,key):
		'\n        Convert key to a consistent string format.\n        \n        Parameters:\n            key (str or dict): Cache key.\n            \n        Returns:\n            str: Normalized cache key.\n        ';B=key
		if isinstance(B,dict):A=json.dumps(B,sort_keys=_B)
		else:A=str(B)
		if len(A)>100:return hashlib.md5(A.encode()).hexdigest()
		return A
	def get(A,key,default=_C):
		'\n        Retrieve value from cache.\n        \n        Parameters:\n            key (str or dict): Cache key.\n            default (Any): Default value if key not found or expired.\n            \n        Returns:\n            Any: Cached value or default.\n        ';C=default;B=key;B=A._get_key(B)
		if A.cache_type==A.MEMORY:return A._get_memory(B,C)
		elif A.cache_type==A.FILE:return A._get_file(B,C)
		elif A.cache_type==A.SQLITE:return A._get_sqlite(B,C)
	def _get_memory(A,key,default):
		'Get from memory cache with thread safety.';B=key
		with A._lock:
			if B in A._cache:
				if time.time()-A._timestamps[B]<=A.ttl:A._access_count[B]+=1;A.logger.debug(f"Cache hit: {B}");return A._cache[B]
				else:A._remove_memory_item(B)
			A.logger.debug(f"Cache miss: {B}");return default
	def _get_file(A,key,default):
		'Get from file cache.';C=key;D=os.path.join(A.cache_dir,C);E=f"{D}.meta"
		if os.path.exists(D)and os.path.exists(E):
			try:
				with open(E,'r')as B:F=json.load(B)
				if time.time()-F[_E]<=A.ttl:
					with open(D,'rb')as B:G=pickle.load(B)
					F[_F]+=1
					with open(E,'w')as B:json.dump(F,B)
					A.logger.debug(f"Cache hit: {C}");return G
				else:
					try:os.remove(D);os.remove(E)
					except OSError:pass
			except(OSError,json.JSONDecodeError,pickle.PickleError)as H:A.logger.warning(f"Error reading cache file {C}: {H}")
		A.logger.debug(f"Cache miss: {C}");return default
	def _get_sqlite(A,key,default):
		'Get from SQLite cache with thread safety.';D=default;B=key
		with A._lock:
			C=A.conn.cursor();C.execute('SELECT value, timestamp, access_count FROM cache WHERE key = ?',(B,));E=C.fetchone()
			if E:
				F,G,H=E
				if time.time()-G<=A.ttl:
					C.execute('UPDATE cache SET access_count = ? WHERE key = ?',(H+1,B));A.conn.commit();A.logger.debug(f"Cache hit: {B}")
					try:return pickle.loads(F)
					except pickle.PickleError as I:A.logger.warning(f"Error unpickling cache value: {I}");return D
				else:C.execute(_G,(B,));A.conn.commit()
			A.logger.debug(f"Cache miss: {B}");return D
	def delete(A,key):
		'\n        Delete an item from the cache.\n        \n        Parameters:\n            key (str or dict): Cache key to delete.\n            \n        Returns:\n            bool: Success status.\n        ';B=key;B=A._get_key(B)
		try:
			if A.cache_type==A.MEMORY:
				with A._lock:A._remove_memory_item(B)
				return _B
			elif A.cache_type==A.FILE:
				C=os.path.join(A.cache_dir,B);D=f"{C}.meta"
				if os.path.exists(C):os.remove(C)
				if os.path.exists(D):os.remove(D)
				return _B
			elif A.cache_type==A.SQLITE:
				with A._lock:E=A.conn.cursor();E.execute(_G,(B,));A.conn.commit()
				return _B
		except Exception as F:A.logger.error(f"Error deleting cache for {B}: {F}");return _A
		return _A
	def clear(A):
		'\n        Clear all cached items.\n        \n        Returns:\n            bool: Success status.\n        '
		try:
			if A.cache_type==A.MEMORY:
				with A._lock:A._cache.clear();A._timestamps.clear();A._access_count.clear()
			elif A.cache_type==A.FILE:
				for C in os.listdir(A.cache_dir):
					D=os.path.join(A.cache_dir,C)
					try:os.remove(D)
					except OSError as B:A.logger.warning(f"Error removing cache file {C}: {B}")
			elif A.cache_type==A.SQLITE:
				with A._lock:E=A.conn.cursor();E.execute('DELETE FROM cache');A.conn.commit()
			A.logger.info(f"Cache cleared for {A.cache_type} backend");return _B
		except Exception as B:A.logger.error(f"Error clearing cache: {B}");return _A
	def set(A,key,value,ttl=_C):
		'\n        Store value in cache.\n        \n        Parameters:\n            key (str or dict): Cache key.\n            value (Any): Value to cache.\n            ttl (int, optional): Custom TTL in seconds.\n            \n        Returns:\n            bool: Success status.\n        ';C=value;B=key;B=A._get_key(B);ttl=ttl or A.ttl
		try:
			if A.cache_type==A.MEMORY:return A._set_memory(B,C)
			elif A.cache_type==A.FILE:return A._set_file(B,C)
			elif A.cache_type==A.SQLITE:return A._set_sqlite(B,C)
			return _A
		except Exception as D:A.logger.error(f"Error setting cache for {B}: {D}");return _A
	def _set_memory(A,key,value):
		'Set in memory cache with cleanup and thread safety.';B=key
		with A._lock:
			if len(A._cache)>=A.max_size and B not in A._cache:A._cleanup_memory_cache()
			A._cache[B]=value;A._timestamps[B]=time.time();A._access_count[B]=0;return _B
	def _cleanup_memory_cache(A):
		'Remove least recently used or expired items from memory cache.'
		with A._lock:
			D=time.time();E=[B for(B,C)in A._timestamps.items()if D-C>A.ttl]
			for B in E:A._remove_memory_item(B)
			if len(A._cache)>=A.max_size:
				C=sorted(A._access_count.items(),key=lambda x:x[1]);F=max(1,int(.1*len(C)))
				for(B,G)in C[:F]:A._remove_memory_item(B)
	def _remove_memory_item(A,key):
		'Remove item from memory cache with thread safety.';B=key
		with A._lock:
			if B in A._cache:del A._cache[B];del A._timestamps[B];del A._access_count[B]
	def _set_file(D,key,value):
		'Set in file cache.';A=os.path.join(D.cache_dir,key);B=f"{A}.meta"
		try:
			with open(A,'wb')as C:pickle.dump(value,C)
			E={_E:time.time(),_F:0}
			with open(B,'w')as C:json.dump(E,C)
			return _B
		except(OSError,pickle.PickleError)as F:
			D.logger.error(f"Error writing to cache file: {F}")
			try:
				if os.path.exists(A):os.remove(A)
				if os.path.exists(B):os.remove(B)
			except OSError:pass
			return _A
	def _set_sqlite(A,key,value):
		'Set in SQLite cache with thread safety.';C=key
		with A._lock:
			try:
				D=pickle.dumps(value);B=A.conn.cursor();B.execute('SELECT COUNT(*) FROM cache WHERE key = ?',(C,))
				if B.fetchone()[0]>0:B.execute('UPDATE cache SET value = ?, timestamp = ?, access_count = 0 WHERE key = ?',(D,time.time(),C))
				else:
					B.execute(_H)
					if B.fetchone()[0]>=A.max_size:A._cleanup_sqlite_cache()
					B.execute('INSERT INTO cache (key, value, timestamp, access_count) VALUES (?, ?, ?, 0)',(C,D,time.time()))
				A.conn.commit();return _B
			except(sqlite3.Error,pickle.PickleError)as E:A.logger.error(f"Error writing to SQLite cache: {E}");A.conn.rollback();return _A
	def _cleanup_sqlite_cache(A):
		'Clean up SQLite cache by removing expired or least accessed items.'
		with A._lock:
			B=A.conn.cursor();B.execute('DELETE FROM cache WHERE timestamp < ?',(time.time()-A.ttl,));B.execute(_H)
			if B.fetchone()[0]>=A.max_size:B.execute('\n                    DELETE FROM cache \n                    WHERE key IN (\n                        SELECT key FROM cache \n                        ORDER BY access_count ASC \n                        LIMIT ?\n                    )\n                ',(max(1,int(.1*A.max_size)),))
			A.conn.commit()