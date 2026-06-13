'\nLớp trừu tượng cho việc lấy dữ liệu.\n'
import abc
class Fetcher(abc.ABC):
	'\n    Lớp trừu tượng Fetcher để lấy dữ liệu thô từ các nguồn khác nhau.\n    Phương thức fetch phải được định nghĩa trong lớp con.\n    '
	@abc.abstractmethod
	def fetch(self,ticker,**A):'\n        Lấy dữ liệu thô cho một mã chứng khoán.\n        \n        :param ticker: Mã chứng khoán.\n        :param kwargs: Các tham số bổ sung.\n        :return: Dữ liệu thô.\n        '