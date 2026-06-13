'\nCác lớp cơ sở VN-specific để xử lý dữ liệu từ vnstock.\n'
import abc,logging,pandas as pd
from vnstock_pipeline.core.fetcher import Fetcher
from vnstock_pipeline.core.validator import Validator
from vnstock_pipeline.core.transformer import Transformer
logger=logging.getLogger(__name__)
class VNFetcher(Fetcher,abc.ABC):
	'\n    Lớp cơ sở VNFetcher sử dụng thư viện vnstock chính thức.\n    Các lớp con cần override phương thức _vn_call để thực hiện lời gọi vnstock cụ thể.\n    '
	def __init__(A):0
	@abc.abstractmethod
	def _vn_call(self,ticker,**A):'\n        Phương thức cần được override để gọi hàm của vnstock (ví dụ: stock.quote.history).\n        \n        :param ticker: Mã chứng khoán.\n        :param kwargs: Các tham số bổ sung.\n        :return: DataFrame chứa dữ liệu lấy từ vnstock.\n        ';raise NotImplementedError
	def fetch(C,ticker,**D):
		'\n        Thực hiện gọi hàm _vn_call và xử lý lỗi cơ bản.\n        \n        :param ticker: Mã chứng khoán.\n        :param kwargs: Các tham số bổ sung.\n        :return: DataFrame chứa dữ liệu thô.\n        ';A=ticker
		try:B=C._vn_call(A,**D);logger.debug(f"Lấy được {len(B)} bản ghi cho {A}.");return B
		except Exception as E:logger.error(f"Lỗi khi lấy dữ liệu cho {A}: {E}");raise
class VNValidator(Validator):
	'\n    Lớp cơ sở VNValidator để kiểm tra dữ liệu lấy từ vnstock.\n    ';required_columns=[]
	def validate(C,data):
		'\n        Kiểm tra dữ liệu có phải là DataFrame và chứa các cột cần thiết không.\n        \n        :param data: DataFrame chứa dữ liệu.\n        :return: True nếu hợp lệ, ngược lại False.\n        ';B=False
		if not isinstance(data,pd.DataFrame):logger.error('Dữ liệu không phải là DataFrame.');return B
		A=[A for A in C.required_columns if A not in data.columns]
		if A:logger.warning(f"Thiếu các cột: {A}");return B
		return True
class VNTransformer(Transformer):
	'\n    Lớp cơ sở VNTransformer để chuyển đổi dữ liệu lấy từ vnstock.\n    '
	def transform(E,data):
		"\n        Chuyển đổi dữ liệu: chuyển cột 'time' hoặc 'date' sang kiểu datetime, sắp xếp và reset index.\n        \n        :param data: DataFrame chứa dữ liệu thô.\n        :return: DataFrame đã chuyển đổi.\n        ";D='coerce';C='date';B='time';A=data.copy()
		if B in A.columns:A[B]=pd.to_datetime(A[B],errors=D);A=A.sort_values(B);A=A.reset_index(drop=True)
		elif C in A.columns:A[C]=pd.to_datetime(A[C],errors=D);A=A.sort_values(C);A=A.reset_index(drop=True)
		logger.debug('Đã chuyển đổi dữ liệu theo mặc định.');return A