'\nLớp trừu tượng cho việc xuất dữ liệu và các triển khai cụ thể.\n'
_I='parquet'
_H='snappy'
_G='%Y-%m-%d'
_F='intraday'
_E='time'
_D='csv'
_C=False
_B=True
_A=None
import abc,os
from datetime import datetime
from pathlib import Path
from typing import List,Optional
import pandas as pd
class Exporter(abc.ABC):
	'\n    Lớp trừu tượng Exporter để xuất dữ liệu đã xử lý ra hệ thống lưu trữ.\n    Phương thức export phải được định nghĩa trong lớp con.\n    '
	@abc.abstractmethod
	def export(self,data,ticker,**A):'\n        Xuất dữ liệu đã xử lý.\n\n        :param data: Dữ liệu đã chuyển đổi (ví dụ: DataFrame).\n        :param ticker: Mã chứng khoán.\n        :param kwargs: Các tham số bổ sung.\n        :return: Path hoặc None tùy thuộc vào triển khai.\n        '
	def preview(A,ticker,n=5,**B):'\n        Phương thức tùy chọn để xem trước n dòng dữ liệu cuối cùng.\n\n        :param ticker: Mã chứng khoán.\n        :param n: Số dòng dữ liệu cần xem trước.\n        :return: Dữ liệu xem trước (DataFrame hoặc None).\n        '
BaseExporter=Exporter
class CSVExport(Exporter):
	'\n    Triển khai Exporter để xuất dữ liệu ra file CSV.\n    '
	def __init__(A,base_path):
		A.base_path=base_path
		if not os.path.exists(A.base_path):os.makedirs(A.base_path)
	def export(D,data,ticker,**G):
		"\n        Ghi dữ liệu ra file CSV, đảm bảo không lặp lại bản ghi dựa trên\n        ['time', 'id']. Nếu file đã tồn tại, đọc toàn bộ dữ liệu cũ,\n        nối batch mới, loại trùng, rồi ghi đè lại file.\n        Nếu chưa có file thì ghi như cũ.\n        ";C=data;A=os.path.join(D.base_path,f"{ticker}.csv")
		if os.path.exists(A):
			try:
				E=pd.read_csv(A);B=pd.concat([E,C],ignore_index=_B)
				if _E in B.columns and'id'in B.columns:B=B.drop_duplicates(subset=[_E,'id'])
				B.to_csv(A,index=_C)
			except Exception as F:print(f"[CSVExport] Lỗi khi đọc/gộp dữ liệu cũ: {F}. Ghi append như cũ.");C.to_csv(A,mode='a',header=_C,index=_C)
		else:C.to_csv(A,index=_C)
	def preview(B,ticker,n=5,**D):
		A=os.path.join(B.base_path,f"{ticker}.csv")
		if not os.path.exists(A):return
		C=pd.read_csv(A);return C.tail(n)
class ParquetExport(Exporter):
	'\n    Triển khai Exporter để xuất dữ liệu ra file Parquet với cấu trúc\n    thư mục tổ chức. Cấu trúc thư mục mặc định:\n    base_path/data_type/date/ticker.parquet\n    '
	def __init__(A,base_path,data_type='stock_data'):"\n        Khởi tạo Parquet Export.\n\n        :param base_path: Đường dẫn gốc để lưu dữ liệu\n        :param data_type: Loại dữ liệu\n                         (vd: 'intraday', 'daily', 'financials',...)\n        ";A.base_path=Path(base_path);A.data_type=data_type;A.base_path.mkdir(parents=_B,exist_ok=_B)
	def _get_file_path(A,ticker,date=_A):'\n        Tạo đường dẫn file parquet dựa trên mã cổ phiếu và ngày.\n\n        :param ticker: Mã cổ phiếu\n        :param date: Ngày dữ liệu (YYYY-MM-DD).\n                    Nếu None, sử dụng ngày hiện tại\n        :return: Đối tượng Path đến file parquet\n        ';C=date or datetime.now().strftime(_G);B=A.base_path/A.data_type/C;B.mkdir(parents=_B,exist_ok=_B);return B/f"{ticker}.parquet"
	def export(A,data,ticker,date=_A,**F):
		'\n        Xuất dữ liệu ra file Parquet.\n\n        :param data: DataFrame chứa dữ liệu cần xuất\n        :param ticker: Mã cổ phiếu\n        :param date: Ngày dữ liệu (YYYY-MM-DD).\n                    Nếu None, sử dụng ngày hiện tại\n        :param kwargs: Các tham số bổ sung\n        '
		try:import pyarrow as B,pyarrow.parquet as C
		except ImportError:raise ImportError('pyarrow is required for ParquetExport. Install it with: pip install pyarrow')
		D=A._get_file_path(ticker,date);E=B.Table.from_pandas(data);C.write_table(E,D,compression=_H,use_dictionary=_B,version='2.6',data_page_size=1048576)
	def preview(C,ticker,n=5,date=_A,**G):
		'\n        Xem trước n dòng dữ liệu từ file parquet.\n\n        :param ticker: Mã cổ phiếu\n        :param n: Số dòng dữ liệu cần xem\n        :param date: Ngày dữ liệu (YYYY-MM-DD).\n                    Nếu None, sử dụng ngày hiện tại\n        :return: DataFrame chứa n dòng dữ liệu cuối cùng hoặc None\n                nếu không tìm thấy file\n        '
		try:import pyarrow.parquet as D
		except ImportError:raise ImportError('pyarrow is required for ParquetExport')
		A=C._get_file_path(ticker,date)
		if not A.exists():return
		B=D.ParquetFile(A);H=B.metadata.num_rows;E=B.read_row_groups(row_groups=[0],columns=_A,use_threads=_B);F=E.to_pandas();return F.tail(n)
class DuckDBExport(Exporter):
	'\n    Triển khai Exporter để xuất dữ liệu ra cơ sở dữ liệu DuckDB.\n    '
	def __init__(A,db_path):A.db_path=db_path
	def export(D,data,ticker,**F):
		C='data';B=ticker
		try:import duckdb as E
		except ImportError:raise ImportError('duckdb is required for DuckDBExport. Install it with: pip install duckdb')
		A=E.connect(D.db_path);A.execute(f"CREATE TABLE IF NOT EXISTS {B} AS SELECT * FROM data LIMIT 0",{C:data});A.execute(f"INSERT INTO {B} SELECT * FROM data",{C:data});A.close()
class TimeSeriesExporter(Exporter):
	"\n    Generic Time-Series Data Exporter.\n\n    Hỗ trợ lưu dữ liệu time-series với các chế độ append/overwrite.\n\n    Cấu trúc thư mục mặc định:\n    base_path/data_type/[subfolder]/YYYY-MM-DD/ticker.{csv|parquet}\n\n    Ví dụ:\n    data/price_depth/2025-10-23/VNM.csv\n    data/ohlcv/1m/2025-10-23/ACB.csv\n    data/intraday/2025-10-23/HPG.csv\n    data/financial/2025-Q4/GAS.csv\n\n    Cách dùng - Intraday (append data):\n        exporter = TimeSeriesExporter('./data', file_format='csv')\n        exporter.export(df, ticker='VNM', data_type='price_depth',\n                       append_mode=True)\n\n    Cách dùng - EOD (overwrite data):\n        exporter.export(df, ticker='VNM', data_type='price_board',\n                       append_mode=False)\n\n    Cách dùng - OHLCV với subfolder:\n        exporter.export(df, ticker='VNM', data_type='ohlcv',\n                       subfolder='1m', append_mode=True)\n    "
	def __init__(A,base_path,file_format=_D,dedup_columns=_A):
		"\n        Khởi tạo TimeSeriesExporter.\n\n        Args:\n            base_path: Đường dẫn gốc để lưu dữ liệu\n            file_format: 'csv' hoặc 'parquet' (mặc định: 'csv')\n            dedup_columns: Danh sách cột để loại trùng\n                          (mặc định: ['time', 'ticker'])\n        ";A.base_path=Path(base_path);A.file_format=file_format.lower();A.dedup_columns=dedup_columns or[_E,'ticker']
		if A.file_format not in[_D,_I]:B="file_format must be 'csv' or 'parquet'";raise ValueError(B)
		A.base_path.mkdir(parents=_B,exist_ok=_B)
	def _build_path(B,ticker,data_type,date=_A,subfolder=_A):
		"\n        Xây dựng đường dẫn file.\n\n        Args:\n            ticker: Mã cổ phiếu\n            data_type: Loại dữ liệu (price_depth, ohlcv, etc.)\n            date: Ngày dữ liệu (YYYY-MM-DD, mặc định: hôm nay)\n            subfolder: Subfolder tùy chọn (ví dụ: '1m' cho OHLCV)\n\n        Returns:\n            Path đến file\n        ";C=subfolder;E=date or datetime.now().strftime(_G);F=_D if B.file_format==_D else _I;A=[B.base_path,data_type]
		if C:A.append(C)
		A.append(E);D=Path(*A);D.mkdir(parents=_B,exist_ok=_B);return D/f"{ticker}.{F}"
	def _read_file(B,file_path):
		'Đọc file CSV hoặc Parquet.';A=file_path
		if B.file_format==_D:return pd.read_csv(A)
		else:return pd.read_parquet(A)
	def _write_file(B,file_path,data):
		'Ghi file CSV hoặc Parquet.';A=file_path
		if B.file_format==_D:data.to_csv(A,index=_C)
		else:data.to_parquet(A,engine='pyarrow',compression=_H,index=_C)
	def _deduplicate(C,data):
		"\n        Loại bỏ dữ liệu trùng lặp.\n\n        Dựa trên dedup_columns (mặc định: ['time', 'ticker']).\n        Giữ lại bản ghi cuối cùng nếu có trùng.\n        ";A=data;B=[B for B in C.dedup_columns if B in A.columns]
		if not B:return A
		return A.drop_duplicates(subset=B,keep='last')
	def export(A,data,ticker,data_type=_F,date=_A,append_mode=_B,deduplicate=_C,subfolder=_A,**G):
		"\n        Xuất dữ liệu time-series.\n\n        Args:\n            data: DataFrame\n            ticker: Mã cổ phiếu\n            data_type: Loại dữ liệu\n                      (price_depth, ohlcv, financial, etc.)\n            date: Ngày (YYYY-MM-DD, mặc định: hôm nay)\n            append_mode: True = append, False = overwrite\n            deduplicate: True = loại trùng, False = giữ hết\n            subfolder: Subfolder tùy chọn (ví dụ: '1m', 'quarterly')\n        ";E=deduplicate;B=data
		if B is _A or B.empty:return
		C=A._build_path(ticker,data_type,date,subfolder)
		if C.exists()and append_mode:
			F=A._read_file(C);D=pd.concat([F,B],ignore_index=_B)
			if E:D=A._deduplicate(D)
			A._write_file(C,D)
		else:
			if E:B=A._deduplicate(B)
			A._write_file(C,B)
		return C
	def preview(A,ticker,n=5,data_type=_F,date=_A,subfolder=_A,**D):
		"\n        Xem trước n dòng cuối của file.\n\n        Args:\n            ticker: Mã cổ phiếu\n            n: Số dòng (mặc định: 5)\n            data_type: Loại dữ liệu (mặc định: 'intraday')\n            date: Ngày (mặc định: hôm nay)\n            subfolder: Subfolder tùy chọn\n        ";B=A._build_path(ticker,data_type,date,subfolder)
		if not B.exists():return
		C=A._read_file(B);return C.tail(n)
	def read_all(A,ticker,data_type=_F,date=_A,subfolder=_A):
		"\n        Đọc toàn bộ dữ liệu của file.\n\n        Args:\n            ticker: Mã cổ phiếu\n            data_type: Loại dữ liệu (mặc định: 'intraday')\n            date: Ngày (mặc định: hôm nay)\n            subfolder: Subfolder tùy chọn\n\n        Returns:\n            DataFrame hoặc None nếu file không tồn tại\n        ";B=A._build_path(ticker,data_type,date,subfolder)
		if not B.exists():return
		return A._read_file(B)
	def list_dates(C,ticker,data_type,subfolder=_A):
		'\n        Liệt kê các ngày có dữ liệu cho ticker và data_type.\n\n        Args:\n            ticker: Mã cổ phiếu\n            data_type: Loại dữ liệu\n            subfolder: Subfolder tùy chọn\n\n        Returns:\n            Danh sách các ngày (định dạng YYYY-MM-DD, sắp xếp)\n        ';E=subfolder;D=ticker;A=C.base_path/data_type
		if E:A=A/E
		if not A.exists():return[]
		F=[];G=f"{D}.csv"if C.file_format==_D else f"{D}.parquet"
		for B in A.iterdir():
			if B.is_dir()and(B/G).exists():F.append(B.name)
		return sorted(F)
	def read_date_range(B,ticker,data_type,start_date,end_date,subfolder=_A):
		'\n        Đọc dữ liệu trong khoảng ngày.\n\n        Args:\n            ticker: Mã cổ phiếu\n            data_type: Loại dữ liệu\n            start_date: Ngày bắt đầu (YYYY-MM-DD)\n            end_date: Ngày kết thúc (YYYY-MM-DD)\n            subfolder: Subfolder tùy chọn\n\n        Returns:\n            DataFrame kết hợp tất cả các ngày trong khoảng\n        ';E=subfolder;D=data_type;C=ticker;H=B.list_dates(C,D,E);F=[A for A in H if start_date<=A<=end_date]
		if not F:return pd.DataFrame()
		A=[]
		for I in F:
			G=B.read_all(C,D,I,E)
			if G is not _A:A.append(G)
		if not A:return pd.DataFrame()
		return pd.concat(A,ignore_index=_B)