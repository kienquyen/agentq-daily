'\nModule quản lý cấu trúc dữ liệu và cung cấp tiện ích làm việc với dữ liệu.\n'
_D='*.parquet'
_C='%Y-%m-%d'
_B=True
_A=None
from pathlib import Path
from datetime import datetime,timedelta
from typing import Dict,List,Optional,Union
import pandas as pd,pyarrow as pa,pyarrow.parquet as pq,pyarrow.dataset as ds
class DataManager:
	'\n    Quản lý cấu trúc thư mục và cung cấp các phương thức tiện ích\n    để làm việc với dữ liệu được lưu trữ dưới dạng parquet.\n    \n    Cấu trúc thư mục mặc định:\n    base_path/\n    ├── data_type_1/\n    │   ├── YYYY-MM-DD/\n    │   │   ├── ticker1.parquet\n    │   │   └── ticker2.parquet\n    │   └── YYYY-MM-DD/\n    │       └── ticker1.parquet\n    └── data_type_2/\n        └── ...\n    '
	def __init__(A,base_path):'\n        Khởi tạo DataManager.\n        \n        :param base_path: Đường dẫn gốc để lưu trữ dữ liệu\n        ';A.base_path=Path(base_path);A.base_path.mkdir(parents=_B,exist_ok=_B)
	def get_data_path(A,data_type,date=_A):"\n        Lấy đường dẫn đến thư mục chứa dữ liệu của một loại và ngày cụ thể.\n        \n        :param data_type: Loại dữ liệu (vd: 'intraday', 'daily', 'financials')\n        :param date: Ngày dữ liệu (YYYY-MM-DD). Nếu None, sử dụng ngày hiện tại\n        :return: Đường dẫn đến thư mục chứa dữ liệu\n        ";B=date or datetime.now().strftime(_C);return A.base_path/data_type/B
	def save_data(C,data,ticker,data_type,date=_A,partition_cols=_A,**D):"\n        Lưu dữ liệu ra file parquet với cấu trúc thư mục tổ chức.\n        \n        :param data: DataFrame chứa dữ liệu cần lưu\n        :param ticker: Mã chứng khoán\n        :param data_type: Loại dữ liệu (vd: 'intraday', 'daily', 'financials')\n        :param date: Ngày dữ liệu (YYYY-MM-DD). Nếu None, sử dụng ngày hiện tại\n        :param partition_cols: Danh sách các cột dùng để phân vùng dữ liệu\n        :param kwargs: Các tham số bổ sung cho pq.write_table\n        :return: Đường dẫn đến file đã lưu\n        ";A=C.get_data_path(data_type,date);A.mkdir(parents=_B,exist_ok=_B);B=A/f"{ticker}.parquet";E=pa.Table.from_pandas(data);pq.write_table(table=E,where=B,compression='snappy',version='2.6',**D);return str(B)
	def load_data(L,ticker,data_type,start_date=_A,end_date=_A,columns=_A,filters=_A):
		"\n        Đọc dữ liệu từ các file parquet.\n        \n        :param ticker: Mã chứng khoán\n        :param data_type: Loại dữ liệu (vd: 'intraday', 'daily', 'financials')\n        :param start_date: Ngày bắt đầu (YYYY-MM-DD). Nếu None, lấy tất cả dữ liệu\n        :param end_date: Ngày kết thúc (YYYY-MM-DD). Nếu None, lấy đến ngày hiện tại\n        :param columns: Danh sách các cột cần đọc. Nếu None, đọc tất cả các cột\n        :param filters: Danh sách các bộ lọc (theo định dạng của PyArrow)\n        :return: DataFrame chứa dữ liệu đã đọc\n        ";Q=filters;P=end_date;O=start_date;N=data_type;M=ticker;I=columns;T=L.base_path/N;G=[]
		if O and P:
			J=datetime.strptime(O,_C);U=datetime.strptime(P,_C)
			while J<=U:
				V=J.strftime(_C);F=L.get_data_path(N,V)/f"{M}.parquet"
				if F.exists():G.append(F)
				J+=timedelta(days=1)
		else:
			for R in T.glob('*'):
				if R.is_dir():
					F=R/f"{M}.parquet"
					if F.exists():G.append(F)
		if not G:return pd.DataFrame()
		H=ds.dataset(G,format='parquet');W=H.schema
		if Q:
			import pyarrow.compute as X;C=_A
			for(S,A,D)in Q:
				if S not in W.names:continue
				E=X.field(S)
				if A=='==':B=E==D
				elif A=='!=':B=E!=D
				elif A=='>':B=E>D
				elif A=='>=':B=E>=D
				elif A=='<':B=E<D
				elif A=='<=':B=E<=D
				else:raise ValueError(f"Unsupported operator: {A}")
				if C is _A:C=B
				else:C=C&B
			if C is not _A:K=H.to_table(columns=I,filter=C)
			else:K=H.to_table(columns=I)
		else:K=H.to_table(columns=I)
		return K.to_pandas()
	def list_available_data(D,data_type=_A,date=_A):
		'\n        Liệt kê các dữ liệu có sẵn trong thư mục.\n        \n        :param data_type: Loại dữ liệu cần liệt kê. Nếu None, liệt kê tất cả các loại\n        :param date: Ngày cần liệt kê (YYYY-MM-DD). Nếu None, liệt kê tất cả các ngày\n        :return: Từ điển chứa danh sách các mã chứng khoán có sẵn, nhóm theo loại dữ liệu\n        ';E=data_type;A={}
		if E:F=[E]
		else:F=[A.name for A in D.base_path.glob('*')if A.is_dir()]
		for B in F:
			C=D.base_path/B
			if not C.exists():continue
			A[B]={}
			if date:G=[C/date]
			else:G=[A for A in C.glob('*')if A.is_dir()]
			for H in G:
				I=[A.stem for A in H.glob(_D)]
				if I:A[B][H.name]=I
		return A
	def delete_data(G,data_type,ticker=_A,date=_A):
		'\n        Xóa dữ liệu theo các tiêu chí.\n        \n        :param data_type: Loại dữ liệu cần xóa\n        :param ticker: Mã chứng khoán cần xóa. Nếu None, xóa tất cả các mã\n        :param date: Ngày cần xóa (YYYY-MM-DD). Nếu None, xóa tất cả các ngày\n        :return: Số lượng file đã xóa\n        ';C=ticker;D=G.base_path/data_type
		if not D.exists():return 0
		B=0
		if date:
			E=D/date
			if E.exists():
				if C:
					A=E/f"{C}.parquet"
					if A.exists():A.unlink();B+=1
				else:
					for A in E.glob(_D):A.unlink();B+=1
					try:E.rmdir()
					except OSError:pass
		elif C:
			for F in D.glob('*'):
				if F.is_dir():
					A=F/f"{C}.parquet"
					if A.exists():A.unlink();B+=1
					try:F.rmdir()
					except OSError:pass
		else:import shutil as H;H.rmtree(D);B=-1
		return B
def get_data_manager(base_path='data'):'\n    Hàm tiện ích để tạo một instance DataManager.\n    \n    :param base_path: Đường dẫn gốc để lưu trữ dữ liệu\n    :return: Instance của DataManager\n    ';return DataManager(base_path)