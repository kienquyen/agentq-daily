'\nCấu hình logging chuẩn cho dự án.\n'
import logging
def setup_logger(name,level=logging.DEBUG):
	'\n    Thiết lập logger với tên và mức độ logging cụ thể.\n    \n    :param name: Tên của logger.\n    :param level: Mức độ logging.\n    :return: Logger đã được cấu hình.\n    ';A=logging.getLogger(name)
	if not A.handlers:B=logging.StreamHandler();C=logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s');B.setFormatter(C);A.addHandler(B);A.setLevel(level)
	return A