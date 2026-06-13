'\nLớp trừu tượng cho việc kiểm tra dữ liệu.\n'
import abc
class Validator(abc.ABC):
	'\n    Lớp trừu tượng Validator để kiểm tra tính hợp lệ của dữ liệu.\n    Phương thức validate phải được định nghĩa trong lớp con.\n    '
	@abc.abstractmethod
	def validate(self,data):'\n        Kiểm tra tính hợp lệ của dữ liệu.\n        \n        :param data: Dữ liệu cần kiểm tra.\n        :return: True nếu dữ liệu hợp lệ, ngược lại False hoặc raise Exception.\n        '