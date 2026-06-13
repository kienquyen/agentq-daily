'\nBase WebSocket Client\n====================\n\nProvides the core WebSocket client functionality for market data streaming.\n'
_B=False
_A=None
import asyncio,logging,time,traceback
from abc import ABC,abstractmethod
from typing import List,Dict,Any,Optional
import websockets
class BaseWebSocketClient(ABC):
	'\n    Base abstract WebSocket client for streaming market data.\n    \n    This abstract class provides the core functionality for WebSocket-based \n    market data streaming. Concrete implementations must be provided for\n    specific data sources.\n    '
	def __init__(A,uri,ping_interval=25):'\n        Initialize the WebSocket client.\n        \n        Args:\n            uri (str): The WebSocket URI to connect to\n            ping_interval (int): Interval in seconds to send ping messages\n        ';A.uri=uri;A.ping_interval=ping_interval;A.websocket=_A;A.running=_B;A.processors=[];A.logger=logging.getLogger(A.__class__.__name__);A.ping_task=_A;A.message_handler_task=_A
	def add_processor(A,processor):'\n        Add a data processor to process incoming data.\n        \n        Args:\n            processor: A DataProcessor instance to process the data\n        ';A.processors.append(processor)
	async def _send_ping(A):
		'Send ping messages to keep the connection alive.'
		while A.running:
			if A.websocket:
				try:await A.websocket.send('2');A.logger.debug('Ping sent')
				except Exception as B:A.logger.error(f"Error sending ping: {B}");A.logger.error(traceback.format_exc())
			await asyncio.sleep(A.ping_interval)
	@abstractmethod
	async def _send_initial_messages(self):'\n        Send initial subscription messages.\n        \n        This method must be implemented by concrete subclasses to handle\n        source-specific subscription messages.\n        '
	@abstractmethod
	def _parse_message(self,message):'\n        Parse received WebSocket messages.\n        \n        This method must be implemented by concrete subclasses to handle\n        source-specific message formats.\n        \n        Args:\n            message (str): The raw message received from the WebSocket\n            \n        Returns:\n            Optional[Dict[str, Any]]: Parsed data or None if message should be ignored\n        '
	async def _handle_messages(A):
		'Handle incoming WebSocket messages.';A.logger.info('Message handler started - waiting for messages...');D=0
		while A.running and A.websocket:
			try:
				E=await A.websocket.recv();D+=1;A.logger.info(f"[MSG #{D}] {E[:80]}");C=A._parse_message(E)
				if C:
					G=C.get('event_type','unknown');A.logger.info(f"[PARSED] event_type={G}")
					for F in A.processors:
						try:await F.process(C)
						except Exception as B:A.logger.error(f"Error in processor {F.__class__.__name__}: {B}");A.logger.error(traceback.format_exc())
			except websockets.exceptions.ConnectionClosed as B:A.logger.warning(f"WebSocket connection closed: {B}");A._on_connection_closed();break
			except Exception as B:A.logger.error(f"Error handling message: {B}");A.logger.error(traceback.format_exc())
	def _on_connection_closed(A):'\n        Hook called when WebSocket connection closes.\n        Override in subclass to add custom behavior.\n        '
	def _on_message_handler_done(A,task):
		'\n        Callback when message handler task completes.\n        \n        This handles cleanup when the WebSocket connection closes.\n        '
		try:task.result()
		except asyncio.CancelledError:A.logger.info('Message handler task cancelled')
		except Exception as B:A.logger.error(f"Message handler task failed: {B}");A.logger.error(traceback.format_exc())
		finally:A.running=_B;A.logger.info('Message handler task completed')
	async def connect(A):
		'\n        Connect to the WebSocket server and start processing messages.\n        \n        This method establishes the WebSocket connection, sends initial\n        subscription messages, and starts background tasks for message\n        handling and ping. It returns immediately after connection is\n        established, allowing the connection to run in the background.\n        '
		if A.running:A.logger.warning('Already connected or connection in progress');return
		A.running=True
		try:A.logger.info(f"Connecting to {A.uri}...");A.websocket=await websockets.connect(A.uri);A.logger.info(f"Connected to {A.uri}");await A._send_initial_messages();A.ping_task=asyncio.create_task(A._send_ping());A.message_handler_task=asyncio.create_task(A._handle_messages());A.message_handler_task.add_done_callback(A._on_message_handler_done);A.logger.info('Connection established and background tasks started')
		except Exception as B:
			A.logger.error(f"Connection error: {B}");A.logger.error(traceback.format_exc());A.running=_B
			if A.websocket:await A.websocket.close()
			A.websocket=_A;raise
	async def disconnect(A):
		'Disconnect from the WebSocket server and cancel background tasks.';A.logger.info('Initiating disconnect...');A.running=_B
		if A.ping_task and not A.ping_task.done():
			A.ping_task.cancel()
			try:await A.ping_task
			except asyncio.CancelledError:pass
			A.ping_task=_A
		if A.message_handler_task and not A.message_handler_task.done():
			A.message_handler_task.cancel()
			try:await A.message_handler_task
			except asyncio.CancelledError:pass
			A.message_handler_task=_A
		if A.websocket:
			try:await A.websocket.close();A.logger.info('Connection closed')
			except Exception as B:A.logger.error(f"Error closing connection: {B}");A.logger.error(traceback.format_exc())
			finally:A.websocket=_A
		A.logger.info('Disconnected')
	def is_connected(A):'\n        Check if the client is currently connected.\n        \n        Returns:\n            bool: True if connected and running, False otherwise\n        ';return A.websocket is not _A and A.running and A.message_handler_task is not _A and not A.message_handler_task.done()
	async def wait_until_disconnected(A):
		'\n        Wait until the connection is closed.\n        \n        This is useful for keeping the program running while the\n        WebSocket connection is active.\n        '
		if A.message_handler_task:
			try:await A.message_handler_task
			except asyncio.CancelledError:pass
	async def send_message(A,message):
		'\n        Send a raw message to the server.\n        \n        Args:\n            message (str): The raw message to send\n        ';B=message
		if A.websocket:
			try:await A.websocket.send(B);A.logger.info(f"Sent message: {B[:50]}...")
			except Exception as C:A.logger.error(f"Error sending message: {C}");A.logger.error(traceback.format_exc())
		else:A.logger.error('Cannot send message: Not connected')