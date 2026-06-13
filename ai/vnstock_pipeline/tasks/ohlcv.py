'\nModule xử lý dữ liệu OHLCV hàng ngày sử dụng các lớp VN cơ sở.\n'
_B='2025-03-19'
_A='2024-01-01'
import pandas as pd
from vnstock_pipeline.template.vnstock import VNFetcher,VNValidator,VNTransformer
from vnstock_pipeline.utils.deduplication import drop_duplicates
from vnstock_data.explorer.vci import Quote
class OHLCVDailyFetcher(VNFetcher):
	'\n    Lớp thực hiện việc lấy dữ liệu OHLCV hàng ngày từ vnstock.\n    '
	def _vn_call(G,ticker,**A):B=A.get('start',_A);C=A.get('end',_B);D=A.get('interval','1D');E=Quote(symbol=ticker);F=E.history(start=B,end=C,interval=D);return F
class OHLCVDailyValidator(VNValidator):'\n    Lớp kiểm tra dữ liệu OHLCV hàng ngày từ vnstock.\n    ';required_columns=['time','open','high','low','close','volume']
class OHLCVDailyTransformer(VNTransformer):
	'\n    Lớp chuyển đổi dữ liệu OHLCV hàng ngày từ vnstock.\n    '
	def transform(B,data):A=super().transform(data);A=drop_duplicates(A,subset=['time']);return A
def run_task(tickers,**B):
	'\n    Chạy quy trình xử lý dữ liệu OHLCV hàng ngày cho danh sách mã chứng khoán.\n    \n    :param tickers: Danh sách mã chứng khoán.\n    :param kwargs: Các tham số bổ sung cho việc lấy dữ liệu, ví dụ: start, end, interval.\n    ';from vnstock_pipeline.core.scheduler import Scheduler as C;from vnstock_pipeline.core.exporter import CSVExport as D;A=OHLCVDailyFetcher();E=OHLCVDailyValidator();F=OHLCVDailyTransformer();G=D(base_path='./data/ohlcv');A.params=B;H=A.fetch
	def I(ticker):return H(ticker,**A.params or{})
	A.fetch=I;J=C(A,E,F,G);J.run(tickers)
if __name__=='__main__':sample_tickers=['ACB','VCB','HPG'];run_task(sample_tickers,start=_A,end=_B,interval='1D')