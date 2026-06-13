'\nModule xử lý dữ liệu báo cáo tài chính sử dụng các lớp VN cơ sở.\nLớp này lấy các báo cáo tài chính (cân đối kế toán, báo cáo kết quả kinh doanh năm và quý,\nlưu chuyển tiền tệ và tỉ số) từ vnstock và lưu chúng ra các file CSV riêng biệt.\n'
_E='quarter'
_D=False
_C=True
_B=None
_A='year'
import os
from pathlib import Path
import pandas as pd
from vnstock_data.explorer.vci import Finance
from vnstock_pipeline.template.vnstock import VNFetcher,VNValidator,VNTransformer
class FinancialFetcher(VNFetcher):
	'\n    Lớp thực hiện việc lấy dữ liệu báo cáo tài chính từ vnstock.\n    Phương thức _vn_call trả về một dictionary chứa các DataFrame cho từng loại báo cáo.\n    Các tham số bổ sung (kwargs) có thể được dùng để thay đổi period, lang, dropna, etc.\n    '
	def _vn_call(R,ticker,**C):
		L='ratio';K='cash_flow';J='income_statement_quarter';I='income_statement_year';H='balance_sheet';D=ticker;E=Finance(symbol=D);M=C.get('balance_sheet_period',_A);N=C.get('income_statement_year_period',_A);O=C.get('income_statement_quarter_period',_E);P=C.get('cash_flow_period',_A);Q=C.get('ratio_period',_A);F=C.get('lang','vi');G=C.get('dropna',_C);A={}
		try:A[H]=E.balance_sheet(period=M,lang=F,dropna=G)
		except Exception as B:A[H]=_B;print(f"Lỗi khi lấy balance_sheet cho {D}: {B}")
		try:A[I]=E.income_statement(period=N,lang=F,dropna=G)
		except Exception as B:A[I]=_B;print(f"Lỗi khi lấy income_statement_year cho {D}: {B}")
		try:A[J]=E.income_statement(period=O,lang=F,dropna=G)
		except Exception as B:A[J]=_B;print(f"Lỗi khi lấy income_statement_quarter cho {D}: {B}")
		try:A[K]=E.cash_flow(period=P,lang=F,dropna=G)
		except Exception as B:A[K]=_B;print(f"Lỗi khi lấy cash_flow cho {D}: {B}")
		try:A[L]=E.ratio(period=Q,lang=F,dropna=G)
		except Exception as B:A[L]=_B;print(f"Lỗi khi lấy ratio cho {D}: {B}")
		return A
class FinancialValidator(VNValidator):
	'\n    Lớp kiểm tra dữ liệu báo cáo tài chính từ vnstock.\n    Kiểm tra dictionary trả về có chứa ít nhất một DataFrame hợp lệ.\n    '
	def validate(B,data):
		if not isinstance(data,dict):print('Dữ liệu không phải là dictionary.');return _D
		for(C,A)in data.items():
			if A is not _B and isinstance(A,pd.DataFrame)and not A.empty:return _C
		print('Không có báo cáo tài chính hợp lệ nào được lấy.');return _D
class FinancialTransformer(VNTransformer):
	'\n    Lớp chuyển đổi dữ liệu báo cáo tài chính từ vnstock.\n    Ở đây dữ liệu được giữ nguyên (pass-through) vì mục tiêu là lưu dữ liệu thô.\n    '
	def transform(A,data):return data
class FinancialExporter:
	'\n    Exporter chuyên dụng cho dữ liệu tài chính.\n    Lưu từng báo cáo tài chính ra file CSV riêng biệt trong thư mục chỉ định.\n    '
	def __init__(A,base_path):A.base_path=base_path;Path(A.base_path).mkdir(parents=_C,exist_ok=_C)
	def export(E,data,ticker,**F):
		B=ticker
		for(C,A)in data.items():
			if A is not _B and not A.empty:D=os.path.join(E.base_path,f"{B}_{C}.csv");A.to_csv(D,index=_D);print(f"Đã lưu {C} cho {B} vào {D}")
	def preview(A,ticker,n=5,**B):0
def run_financial_task(tickers,max_workers=3,request_delay=.5,rate_limit_wait=35.,**B):
	'\n    Chạy quy trình xử lý dữ liệu báo cáo tài chính cho danh sách mã chứng khoán.\n    \n    Mỗi báo cáo sẽ được lưu ra file CSV riêng biệt trong thư mục ./data/financial.\n    \n    :param tickers: Danh sách mã chứng khoán.\n    :param max_workers: Số workers song song (mặc định: 3).\n    :param request_delay: Delay giữa requests (giây) (mặc định: 0.5).\n    :param rate_limit_wait: Thời gian chờ khi rate limit (giây) (mặc định: 35.0).\n    :param kwargs: Các tham số bổ sung cho việc lấy báo cáo, ví dụ: \n                   balance_sheet_period, income_statement_year_period, income_statement_quarter_period,\n                   cash_flow_period, ratio_period, lang, dropna.\n                   \n    Ví dụ sử dụng:\n        # Lấy dữ liệu nhanh hơn (5 workers, delay 0.2s, rate_limit_wait 30s)\n        run_financial_task(tickers, max_workers=5, request_delay=0.2, rate_limit_wait=30.0,\n                          balance_sheet_period="year", lang="vi")\n    ';from vnstock_pipeline.core.scheduler import Scheduler as C;A=FinancialFetcher();D=FinancialValidator();E=FinancialTransformer();F=FinancialExporter(base_path='./data/financial');A.params=B;G=A.fetch
	def H(ticker):return G(ticker,**A.params or{})
	A.fetch=H;I=C(A,D,E,F,retry_attempts=1,max_workers=max_workers,request_delay=request_delay,rate_limit_wait=rate_limit_wait);I.run(tickers)
if __name__=='__main__':sample_tickers=['ACB','VCB','HPG'];run_financial_task(sample_tickers,balance_sheet_period=_A,income_statement_year_period=_A,income_statement_quarter_period=_E,cash_flow_period=_A,ratio_period=_A,lang='vi',dropna=_C)