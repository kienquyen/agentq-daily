'\nLớp trừu tượng cho việc chuyển đổi dữ liệu.\n'
import abc
class Transformer(abc.ABC):
	'\n    Lớp trừu tượng Transformer để chuyển đổi dữ liệu thô thành dạng chuẩn.\n    Phương thức transform phải được định nghĩa trong lớp con.\n    '
	@abc.abstractmethod
	def transform(self,data):'\n        Chuyển đổi dữ liệu thô thành dữ liệu đã xử lý.\n        \n        :param data: Dữ liệu thô cần chuyển đổi.\n        :return: Dữ liệu đã chuyển đổi.\n        '