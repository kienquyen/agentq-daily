from abc import ABC,abstractmethod
from typing import Any
from vnstock_news.utils.logger import setup_logger
class BaseParser(ABC):
	'\n    Abstract base class defining a standard fetch → parse workflow.\n    '
	def __init__(A,show_log=False):A.logger=setup_logger(A.__class__.__name__,show_log)
	@abstractmethod
	def fetch(self):'\n        Fetch raw data from the source (e.g. XML, HTML).\n        '
	@abstractmethod
	def parse(self,raw):'\n        Parse raw data into structured form (e.g. DataFrame or dict).\n        '
	def run(A):'\n        Execute fetch() followed by parse() and return the result.\n        ';B=A.fetch();return A.parse(B)