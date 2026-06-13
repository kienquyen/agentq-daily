'\nModule xử lý dữ liệu intraday sử dụng các lớp VN cơ sở.\nCho phép tải dữ liệu theo 2 chế độ:\n- EOD: Lấy dữ liệu tĩnh một lần.\n- live: Cập nhật dữ liệu liên tục trong phiên giao dịch, với kiểm tra giờ giao dịch.\n         Trong live mode, trước mỗi lần cập nhật, sẽ kiểm tra market_hours để đảm bảo\n         rằng thị trường đang mở. Nếu thị trường đóng (hoặc trong giờ nghỉ), vòng lặp sẽ dừng.\n'
_H='page_size'
_G='live'
_F='append'
_E=False
_D='backup'
_C='id'
_B=True
_A='time'
import time,os,shutil
from pathlib import Path
from datetime import datetime
import pandas as pd
from vnstock import Vnstock
from vnstock_data.explorer.vci import Quote
from vnstock_pipeline.template.vnstock import VNFetcher,VNValidator,VNTransformer
from vnstock_pipeline.utils.deduplication import drop_duplicates
from vnstock_pipeline.utils.market_hours import trading_hours
from vnstock_pipeline.core.exporter import Exporter
class IntradayFetcher(VNFetcher):
	'\n    Lớp thực hiện việc lấy dữ liệu intraday từ vnstock.\n    '
	def _vn_call(E,ticker,**A):B=A.get(_H,50000);C=Quote(symbol=ticker);D=C.intraday(page_size=B);return D
class IntradayValidator(VNValidator):'\n    Lớp kiểm tra dữ liệu intraday từ vnstock.\n    ';required_columns=[_A,'price','volume','match_type',_C]
class IntradayTransformer(VNTransformer):
	'\n    Lớp chuyển đổi dữ liệu intraday từ vnstock.\n    '
	def transform(B,data):
		A=super().transform(data);A=drop_duplicates(A,subset=[_A,_C])
		if _A in A.columns:A[_A]=pd.to_datetime(A[_A])
		A=A.sort_values(_A);return A
class SmartCSVExport(Exporter):
	'\n    Lớp xuất dữ liệu ra file CSV với cơ chế append thông minh.\n    Hỗ trợ chế độ append thông minh để tránh trùng lặp dữ liệu.\n    Chỉ giữ lại số lượng file backup giới hạn để tiết kiệm dung lượng.\n    '
	def __init__(A,base_path,backup_dir=None,max_backups=2):
		'\n        Khởi tạo exporter với đường dẫn cơ sở và thư mục backup.\n        \n        :param base_path: Đường dẫn cơ sở để lưu file CSV\n        :param backup_dir: Thư mục để lưu các bản backup (nếu None, sẽ tạo thư mục backup trong base_path)\n        :param max_backups: Số lượng file backup tối đa cho mỗi mã chứng khoán (mặc định: 2)\n        ';B=backup_dir;A.base_path=Path(base_path);A.base_path.mkdir(parents=_B,exist_ok=_B)
		if B is None:A.backup_dir=A.base_path/_D
		else:A.backup_dir=Path(B)
		A.backup_dir.mkdir(parents=_B,exist_ok=_B);A.max_backups=max_backups
	def _get_file_path(A,ticker):'Trả về đường dẫn file cho mã chứng khoán';return A.base_path/f"{ticker}.csv"
	def _cleanup_old_backups(A,ticker):
		'\n        Xóa các file backup cũ để chỉ giữ lại số lượng tối đa đã định.\n        \n        :param ticker: Mã chứng khoán cần dọn dẹp backup\n        ';B=list(A.backup_dir.glob(f"{ticker}_*.csv"));B.sort(key=lambda x:x.stat().st_mtime,reverse=_B)
		if len(B)>A.max_backups:
			for C in B[A.max_backups:]:
				try:C.unlink();print(f"Xóa file backup cũ: {C.name}")
				except Exception as D:print(f"Không thể xóa file backup cũ {C.name}: {D}")
	def _backup_file(A,ticker):
		'\n        Tạo bản sao lưu của file hiện tại trước khi cập nhật.\n        \n        :param ticker: Mã chứng khoán\n        :return: True nếu sao lưu thành công, False nếu không có file để sao lưu\n        ';B=ticker;C=A._get_file_path(B)
		if not C.exists():return _E
		D=datetime.now().strftime('%Y%m%d_%H%M%S');E=A.backup_dir/f"{B}_{D}.csv";shutil.copy2(C,E);A._cleanup_old_backups(B);return _B
	def _save_atomic(B,df,path):'\n        Lưu DataFrame ra file một cách atomic để tránh file hỏng khi bị ngắt đột ngột.\n        \n        :param df: DataFrame cần lưu\n        :param path: Đường dẫn file đích\n        ';A=path.with_suffix('.csv.tmp');df.to_csv(A,index=_E);os.replace(A,path)
	def _read_existing_data(C,ticker):
		'\n        Đọc dữ liệu hiện có từ file CSV.\n        \n        :param ticker: Mã chứng khoán\n        :return: DataFrame chứa dữ liệu hiện có, hoặc DataFrame rỗng nếu file không tồn tại\n        ';B=C._get_file_path(ticker)
		if B.exists():
			try:
				A=pd.read_csv(B)
				if _A in A.columns:A[_A]=pd.to_datetime(A[_A])
				return A
			except Exception as D:print(f"Lỗi khi đọc file {B}: {D}");return pd.DataFrame()
		return pd.DataFrame()
	def export(B,data,ticker,**F):
		'\n        Xuất dữ liệu ra file CSV với cơ chế append thông minh.\n        \n        :param data: DataFrame chứa dữ liệu mới\n        :param ticker: Mã chứng khoán\n        :param kwargs: Các tham số bổ sung\n            - mode: "append" để thêm dữ liệu mới vào file hiện có, "overwrite" để ghi đè\n            - backup: True để tạo bản sao lưu trước khi cập nhật\n        ';C=ticker;A=data;H=F.get('mode',_F);I=F.get(_D,_B);D=B._get_file_path(C)
		if A is None or A.empty:print(f"Không có dữ liệu mới cho {C}");return
		if _A in A.columns:A[_A]=pd.to_datetime(A[_A])
		if H==_F and D.exists():
			if I:B._backup_file(C)
			E=B._read_existing_data(C)
			if E.empty:B._save_atomic(A,D);print(f"[{C}] Đã lưu dữ liệu intraday mới");return
			G=B._smart_append(E,A);B._save_atomic(G,D);print(f"[{C}] Đã cập nhật dữ liệu intraday (từ {len(E)} đến {len(G)} dòng)")
		else:B._save_atomic(A,D);print(f"[{C}] Đã lưu dữ liệu intraday ({len(A)} dòng)")
	def _smart_append(H,old_data,new_data):
		'\n        Thực hiện append thông minh để tránh trùng lặp dữ liệu.\n        \n        Phương pháp:\n        1. Xác định mốc thời gian cũ nhất trong dữ liệu mới\n        2. Xóa dữ liệu cũ từ mốc đó trở về sau\n        3. Ghép nối dữ liệu\n        \n        :param old_data: DataFrame chứa dữ liệu cũ\n        :param new_data: DataFrame chứa dữ liệu mới\n        :return: DataFrame đã được merge\n        ';B=new_data;A=old_data
		if A.empty:return B
		if B.empty:return A
		for D in[A,B]:
			if _A not in D.columns:raise ValueError("DataFrame phải có cột 'time'")
			D[_A]=pd.to_datetime(D[_A])
		A=A.sort_values(_A);B=B.sort_values(_A)
		if not B.empty:
			E=B[_A].min();F=E.replace(second=0,microsecond=0);G=A[A[_A]<F];C=pd.concat([G,B])
			if _C in C.columns:C=drop_duplicates(C,subset=[_A,_C])
			else:C=drop_duplicates(C,subset=[_A])
			C=C.sort_values(_A).reset_index(drop=_B);return C
		else:return A
	def preview(C,ticker,n=5,**E):
		'\n        Xem trước n dòng dữ liệu gần nhất cho mã chứng khoán.\n        \n        :param ticker: Mã chứng khoán\n        :param n: Số dòng cần xem\n        :return: DataFrame chứa n dòng dữ liệu gần nhất, hoặc None nếu không có dữ liệu\n        ';B=C._get_file_path(ticker)
		if not B.exists():return
		try:
			A=pd.read_csv(B)
			if _A in A.columns:A[_A]=pd.to_datetime(A[_A]);A=A.sort_values(_A,ascending=_E)
			return A.head(n)
		except Exception as D:print(f"Lỗi khi đọc file {B}: {D}");return
def run_intraday_task(tickers,interval=60,mode=_G,page_size=50000,backup=_B,max_backups=2):
	'\n    Chạy quy trình xử lý dữ liệu intraday cho danh sách mã chứng khoán.\n    \n    Nếu mode = "EOD":\n        - Lấy dữ liệu tĩnh một lần và lưu ra file CSV.\n    Nếu mode = "live":\n        - Cập nhật dữ liệu liên tục trong phiên giao dịch với cơ chế append thông minh.\n        - Trước mỗi lần cập nhật, kiểm tra giờ giao dịch bằng market_hours.\n        - Nếu thị trường không mở, dừng vòng lặp.\n    \n    :param tickers: Danh sách mã chứng khoán.\n    :param interval: Thời gian chờ giữa các lần cập nhật (giây) trong live mode.\n    :param mode: "live" để cập nhật liên tục hoặc "EOD" để tải dữ liệu một lần.\n    :param page_size: Số lượng bản ghi tối đa lấy từ API.\n    :param backup: True để tạo bản sao lưu trước khi cập nhật trong live mode.\n    ';M='trading_session';L='./data/intraday';F=interval;E=tickers;from vnstock_pipeline.core.scheduler import Scheduler as G;from vnstock_pipeline.core.exporter import CSVExport as N;H=IntradayFetcher();I=IntradayValidator();J=IntradayTransformer();K={_H:page_size}
	if mode.lower()=='eod':print('Chế độ EOD: Lấy dữ liệu intraday tĩnh một lần.');A=N(base_path=L);B={};C=G(H,I,J,A);C.run(E,fetcher_kwargs=K,exporter_kwargs=B);print('EOD download hoàn thành.')
	else:
		print('Chế độ live: Cập nhật dữ liệu intraday liên tục trong phiên giao dịch.');A=SmartCSVExport(base_path=L,max_backups=max_backups);B={'mode':_F,_D:backup};C=G(H,I,J,A)
		try:
			while _B:
				try:
					D=trading_hours(market='HOSE',enable_log=_B,language='vi')
					if not D['is_trading_hour']:print(f"Ngoài giờ giao dịch ({D[M]}). Đợi 5 phút...");time.sleep(300);continue
					print(f"Đang cập nhật dữ liệu trong phiên {D[M]}...");C.run(E,fetcher_kwargs=K,exporter_kwargs=B);print(f"Hoàn thành cập nhật. Đợi {F} giây trước khi cập nhật tiếp...")
				except Exception as O:print(f"Lỗi khi cập nhật dữ liệu intraday: {O}")
				time.sleep(F)
		except KeyboardInterrupt:print('Đã dừng cập nhật dữ liệu theo yêu cầu.')
if __name__=='__main__':sample_tickers=['ACB','VCB','HPG'];mode=_G;page_size=5000 if mode==_G else 50000;run_intraday_task(sample_tickers,interval=60,mode=mode,page_size=page_size,backup=_B,max_backups=2)