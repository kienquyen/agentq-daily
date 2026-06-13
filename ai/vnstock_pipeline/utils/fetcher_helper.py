'\nCác hàm tiện ích hỗ trợ việc lấy dữ liệu, bao gồm caching, retry, và quản lý phiên (session).\n'
import time,logging
logger=logging.getLogger(__name__)
def retry(func,max_attempts=3,backoff=2.,*C,**D):
	'\n    Hàm bọc để thực hiện retry cho một hàm có thể thất bại.\n    \n    :param func: Hàm cần thực hiện.\n    :param max_attempts: Số lần thử tối đa.\n    :param backoff: Hệ số chờ giữa các lần thử.\n    :return: Kết quả của hàm nếu thành công.\n    :raises: Exception nếu tất cả các lần thử đều thất bại.\n    ';B=max_attempts;A=0
	while A<B:
		try:return func(*C,**D)
		except Exception as E:A+=1;logger.warning(f"Thử lại {A}/{B} sau lỗi: {E}");time.sleep(backoff**A)
	raise Exception('Hết số lần thử, không thể hoàn thành thao tác.')