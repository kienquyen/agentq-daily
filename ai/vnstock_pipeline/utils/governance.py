'\nCác tiện ích về quản trị dữ liệu, kiểm tra tính toàn vẹn và tuân thủ các quy tắc dữ liệu.\n'
def check_required_columns(data,required_columns):
	'\n    Kiểm tra dữ liệu có chứa tất cả các cột bắt buộc hay không.\n    \n    :param data: Dữ liệu có thể là DataFrame hoặc dict.\n    :param required_columns: Danh sách các cột bắt buộc.\n    :return: True nếu dữ liệu có đủ các cột, ngược lại False.\n    ';A=data
	if not isinstance(A,dict):A=A.__dict__
	B=[B for B in required_columns if B not in A];return len(B)==0