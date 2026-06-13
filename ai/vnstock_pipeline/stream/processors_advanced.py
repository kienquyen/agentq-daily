'\nAdvanced Data Processors\n=======================\n\nReal-time streaming processors for various integration patterns.\n'
_I='Redis connection closed'
_H='redis module not installed. Install with: pip install redis'
_G='redis://localhost:6379'
_F='close'
_E=True
_D='{data_type}'
_C='unknown'
_B='data_type'
_A=None
import asyncio,json,traceback
from typing import Dict,Any,Optional,Callable,List
from collections import deque
import time
from vnstock_pipeline.stream.processors import DataProcessor
class RedisStreamProcessor(DataProcessor):
	'\n    Stream data to Redis Streams for message queue pattern.\n    \n    Use Cases:\n    - Multiple consumers processing same data stream\n    - Buffer for slow consumers\n    - Persistent message history\n    - Consumer groups for load balancing\n    \n    Example:\n        processor = RedisStreamProcessor(\n            redis_url="redis://localhost:6379",\n            stream_key="market:stream",\n            maxlen=10000  # Keep last 10k messages\n        )\n    '
	def __init__(A,redis_url=_G,stream_key='market:stream',maxlen=10000,data_types=_A):
		'\n        Initialize Redis Stream processor.\n        \n        Args:\n            redis_url: Redis connection URL\n            stream_key: Redis stream key (can use {data_type} placeholder)\n            maxlen: Maximum stream length (FIFO when exceeded)\n            data_types: Filter by data types, None for all\n        ';B=data_types;super().__init__();A.redis_url=redis_url;A.stream_key=stream_key;A.maxlen=maxlen;A.data_types=set(B)if B else _A;A.redis=_A
		try:import redis.asyncio as C;A.aioredis=C
		except ImportError:A.logger.error(_H);raise
	async def _ensure_connected(A):
		'Ensure Redis connection is established.'
		if A.redis is _A:A.redis=await A.aioredis.from_url(A.redis_url,encoding='utf-8',decode_responses=_E);A.logger.info(f"Connected to Redis: {A.redis_url}")
	def _get_stream_key(B,data):
		'Generate stream key from data.';A=B.stream_key
		if _D in A:C=data.get(_B,_C);A=A.replace(_D,C)
		return A
	async def process(A,data):
		'\n        Stream data to Redis.\n        \n        Args:\n            data: Market data to stream\n        ';B=data
		try:
			if A.data_types:
				D=B.get(_B,_C)
				if D not in A.data_types:return
			await A._ensure_connected();C=A._get_stream_key(B);await A.redis.xadd(C,{'data':json.dumps(B)},maxlen=A.maxlen);A.logger.debug(f"Streamed to Redis: {C}")
		except Exception as E:A.logger.error(f"Redis streaming error: {E}");A.logger.error(traceback.format_exc())
	async def close(A):
		'Close Redis connection.'
		if A.redis:await A.redis.close();A.logger.info(_I)
class RedisPubSubProcessor(DataProcessor):
	'\n    Publish data to Redis Pub/Sub channels.\n    \n    Use Cases:\n    - Broadcast to multiple subscribers\n    - Low-latency real-time updates\n    - No message persistence (fire-and-forget)\n    \n    Example:\n        processor = RedisPubSubProcessor(\n            redis_url="redis://localhost:6379",\n            channel="market:{data_type}"  # Dynamic channel per data type\n        )\n    '
	def __init__(A,redis_url=_G,channel='market:data',data_types=_A):
		'\n        Initialize Redis Pub/Sub processor.\n        \n        Args:\n            redis_url: Redis connection URL\n            channel: Channel name (can use {data_type} placeholder)\n            data_types: Filter by data types, None for all\n        ';B=data_types;super().__init__();A.redis_url=redis_url;A.channel=channel;A.data_types=set(B)if B else _A;A.redis=_A
		try:import redis.asyncio as C;A.aioredis=C
		except ImportError:A.logger.error(_H);raise
	async def _ensure_connected(A):
		'Ensure Redis connection is established.'
		if A.redis is _A:A.redis=await A.aioredis.from_url(A.redis_url,encoding='utf-8',decode_responses=_E);A.logger.info(f"Connected to Redis: {A.redis_url}")
	def _get_channel(B,data):
		'Generate channel name from data.';A=B.channel
		if _D in A:C=data.get(_B,_C);A=A.replace(_D,C)
		return A
	async def process(A,data):
		'\n        Publish data to Redis channel.\n        \n        Args:\n            data: Market data to publish\n        ';B=data
		try:
			if A.data_types:
				D=B.get(_B,_C)
				if D not in A.data_types:return
			await A._ensure_connected();C=A._get_channel(B);await A.redis.publish(C,json.dumps(B));A.logger.debug(f"Published to channel: {C}")
		except Exception as E:A.logger.error(f"Redis pub/sub error: {E}");A.logger.error(traceback.format_exc())
	async def close(A):
		'Close Redis connection.'
		if A.redis:await A.redis.close();A.logger.info(_I)
class KafkaProcessor(DataProcessor):
	'\n    Stream data to Apache Kafka for enterprise message queue.\n    \n    Use Cases:\n    - High-throughput data pipeline\n    - Multiple consumers with different offsets\n    - Long-term message retention\n    - Integration with big data ecosystem\n    \n    Example:\n        processor = KafkaProcessor(\n            bootstrap_servers="localhost:9092",\n            topic="market.{data_type}",\n            key_field="ticker"  # Partition by ticker\n        )\n    '
	def __init__(A,bootstrap_servers='localhost:9092',topic='market.data',key_field=_A,data_types=_A,compression_type='gzip'):
		'\n        Initialize Kafka processor.\n        \n        Args:\n            bootstrap_servers: Kafka broker addresses\n            topic: Topic name (can use {data_type} placeholder)\n            key_field: Field to use as message key for partitioning\n            data_types: Filter by data types, None for all\n            compression_type: Compression (gzip, snappy, lz4, zstd)\n        ';B=data_types;super().__init__();A.bootstrap_servers=bootstrap_servers;A.topic=topic;A.key_field=key_field;A.data_types=set(B)if B else _A;A.compression_type=compression_type;A.producer=_A
		try:from aiokafka import AIOKafkaProducer as C;A.AIOKafkaProducer=C
		except ImportError:A.logger.error('aiokafka module not installed. Install with: pip install aiokafka');raise
	async def _ensure_connected(A):
		'Ensure Kafka producer is initialized.'
		if A.producer is _A:A.producer=A.AIOKafkaProducer(bootstrap_servers=A.bootstrap_servers,value_serializer=lambda v:json.dumps(v).encode(),key_serializer=lambda k:k.encode()if k else _A,compression_type=A.compression_type);await A.producer.start();A.logger.info(f"Kafka producer started: {A.bootstrap_servers}")
	def _get_topic(B,data):
		'Generate topic name from data.';A=B.topic
		if _D in A:C=data.get(_B,_C);A=A.replace(_D,C)
		return A
	def _get_key(A,data):
		'Get message key for partitioning.'
		if A.key_field:return str(data.get(A.key_field,''))
	async def process(A,data):
		'\n        Send data to Kafka.\n        \n        Args:\n            data: Market data to send\n        ';B=data
		try:
			if A.data_types:
				E=B.get(_B,_C)
				if E not in A.data_types:return
			await A._ensure_connected();C=A._get_topic(B);D=A._get_key(B);await A.producer.send(C,value=B,key=D);A.logger.debug(f"Sent to Kafka: {C} (key={D})")
		except Exception as F:A.logger.error(f"Kafka sending error: {F}");A.logger.error(traceback.format_exc())
	async def close(A):
		'Close Kafka producer.'
		if A.producer:await A.producer.stop();A.logger.info('Kafka producer stopped')
class WebSocketRelayProcessor(DataProcessor):
	'\n    Relay data to WebSocket clients (act as WebSocket server).\n    \n    Use Cases:\n    - Browser-based dashboards\n    - Mobile apps\n    - Two-way communication\n    \n    Example:\n        processor = WebSocketRelayProcessor(\n            host="0.0.0.0",\n            port=8765,\n            data_types=["stockps", "index"]\n        )\n    '
	def __init__(A,host='0.0.0.0',port=8765,data_types=_A,max_clients=100):
		'\n        Initialize WebSocket relay processor.\n        \n        Args:\n            host: Host to bind to\n            port: Port to listen on\n            data_types: Filter by data types, None for all\n            max_clients: Maximum concurrent clients\n        ';B=data_types;super().__init__();A.host=host;A.port=port;A.data_types=set(B)if B else _A;A.max_clients=max_clients;A.clients=set();A.server=_A;A.server_task=_A
		try:import websockets as C;A.websockets=C
		except ImportError:A.logger.error('websockets module not installed. Install with: pip install websockets');raise
	async def _start_server(A):
		'Start WebSocket server.'
		if A.server is _A:A.server=await A.websockets.serve(A._handle_client,A.host,A.port);A.logger.info(f"WebSocket relay started: ws://{A.host}:{A.port}")
	async def _handle_client(A,websocket,path):
		'Handle new WebSocket client connection.';B=websocket
		if len(A.clients)>=A.max_clients:await B.close(1008,'Max clients reached');A.logger.warning('Rejected client: max clients reached');return
		A.clients.add(B);A.logger.info(f"Client connected: {B.remote_address} (total: {len(A.clients)})")
		try:
			async for C in B:await B.send(C)
		except Exception as D:A.logger.debug(f"Client connection error: {D}")
		finally:A.clients.remove(B);A.logger.info(f"Client disconnected (total: {len(A.clients)})")
	async def process(A,data):
		'\n        Broadcast data to all connected clients.\n        \n        Args:\n            data: Market data to broadcast\n        '
		try:
			if A.data_types:
				E=data.get(_B,_C)
				if E not in A.data_types:return
			await A._start_server()
			if not A.clients:return
			F=json.dumps(data);C=set()
			for D in A.clients:
				try:await D.send(F)
				except Exception as B:A.logger.debug(f"Failed to send to client: {B}");C.add(D)
			A.clients-=C
			if A.clients:A.logger.debug(f"Broadcasted to {len(A.clients)} clients")
		except Exception as B:A.logger.error(f"WebSocket relay error: {B}");A.logger.error(traceback.format_exc())
	async def close(A):
		'Close WebSocket server.'
		if A.server:A.server.close();await A.server.wait_closed();A.logger.info('WebSocket relay stopped')
class BufferedProcessor(DataProcessor):
	'\n    Buffer data and flush in batches for efficiency.\n    \n    Use Cases:\n    - Reduce I/O overhead for slow processors\n    - Batch inserts to databases\n    - Aggregate before forwarding\n    \n    Example:\n        buffered = BufferedProcessor(\n            processor=DuckDBProcessor("market.db"),\n            batch_size=100,\n            flush_interval=5.0  # seconds\n        )\n    '
	def __init__(A,processor,batch_size=100,flush_interval=5.):'\n        Initialize buffered processor.\n        \n        Args:\n            processor: Underlying processor to buffer for\n            batch_size: Flush when buffer reaches this size\n            flush_interval: Flush every N seconds even if not full\n        ';super().__init__();A.processor=processor;A.batch_size=batch_size;A.flush_interval=flush_interval;A.buffer=deque();A.last_flush=time.time();A.flush_task=_A
	async def _auto_flush(A):
		'Auto-flush task that runs periodically.'
		while _E:
			await asyncio.sleep(A.flush_interval)
			if A.buffer and time.time()-A.last_flush>=A.flush_interval:await A._flush()
	async def _flush(A):
		'Flush buffer to underlying processor.'
		if not A.buffer:return
		B=list(A.buffer);A.buffer.clear();A.last_flush=time.time();A.logger.debug(f"Flushing {len(B)} items")
		for C in B:
			try:await A.processor.process(C)
			except Exception as D:A.logger.error(f"Error processing buffered data: {D}")
	async def process(A,data):
		'\n        Buffer data and flush when conditions met.\n        \n        Args:\n            data: Market data to buffer\n        '
		try:
			if A.flush_task is _A:A.flush_task=asyncio.create_task(A._auto_flush())
			A.buffer.append(data)
			if len(A.buffer)>=A.batch_size:await A._flush()
		except Exception as B:A.logger.error(f"Buffered processor error: {B}");A.logger.error(traceback.format_exc())
	async def close(A):
		'Flush remaining data and close.'
		if A.flush_task:A.flush_task.cancel()
		await A._flush()
		if hasattr(A.processor,_F):
			if asyncio.iscoroutinefunction(A.processor.close):await A.processor.close()
			else:A.processor.close()
class ConditionalProcessor(DataProcessor):
	'\n    Process data only when conditions are met.\n    \n    Use Cases:\n    - Alert only when price > threshold\n    - Forward only during market hours\n    - Filter by volume, change %, etc.\n    \n    Example:\n        alert = ConditionalProcessor(\n            processor=WebhookProcessor("http://alert.com"),\n            condition=lambda data: (\n                data.get("data_type") == "stockps" and\n                float(data.get("change_percent", 0)) > 5.0\n            )\n        )\n    '
	def __init__(A,processor,condition):'\n        Initialize conditional processor.\n        \n        Args:\n            processor: Processor to use when condition met\n            condition: Function that returns True to process\n        ';super().__init__();A.processor=processor;A.condition=condition
	async def process(A,data):
		'\n        Process data if condition is met.\n        \n        Args:\n            data: Market data to check\n        '
		try:
			if A.condition(data):await A.processor.process(data)
			else:A.logger.debug('Condition not met, skipping')
		except Exception as B:A.logger.error(f"Conditional processor error: {B}");A.logger.error(traceback.format_exc())
	async def close(A):
		'Close underlying processor.'
		if hasattr(A.processor,_F):
			if asyncio.iscoroutinefunction(A.processor.close):await A.processor.close()
			else:A.processor.close()
class MultiProcessor(DataProcessor):
	'\n    Route data to multiple processors simultaneously.\n    \n    Use Cases:\n    - Save to DB AND forward to webhook\n    - Multiple data sinks\n    - Parallel processing pipeline\n    \n    Example:\n        multi = MultiProcessor([\n            CSVProcessor("data.csv"),\n            WebhookProcessor("http://api.com"),\n            RedisPubSubProcessor()\n        ])\n    '
	def __init__(A,processors):'\n        Initialize multi-processor.\n        \n        Args:\n            processors: List of processors to run\n        ';B=processors;super().__init__();A.processors=B;A.logger.info(f"MultiProcessor with {len(B)} processors")
	async def process(A,data):
		'\n        Process data through all processors.\n        \n        Args:\n            data: Market data to process\n        '
		try:
			C=[A.process(data)for A in A.processors];D=await asyncio.gather(*C,return_exceptions=_E)
			for(E,B)in enumerate(D):
				if isinstance(B,Exception):A.logger.error(f"Processor {A.processors[E].__class__.__name__} error: {B}")
		except Exception as F:A.logger.error(f"Multi-processor error: {F}");A.logger.error(traceback.format_exc())
	async def close(B):
		'Close all processors.'
		for A in B.processors:
			if hasattr(A,_F):
				try:
					if asyncio.iscoroutinefunction(A.close):await A.close()
					else:A.close()
				except Exception as C:B.logger.error(f"Error closing processor: {C}")