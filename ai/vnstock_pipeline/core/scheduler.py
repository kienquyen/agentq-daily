'\nĐiều phối quá trình xử lý dữ liệu cho danh sách mã chứng khoán.\n\nQuy trình:\n  1. Với mỗi mã chứng khoán, thực hiện:\n     - (Tùy chọn) Xem trước dữ liệu đã xuất.\n     - Fetch dữ liệu, Validate, Transform, Export.\n     - Nếu có lỗi, retry theo số lần quy định.\n  2. Nếu số mã > 10, sử dụng xử lý song song (asynchronous) kết hợp với ThreadPoolExecutor,\n     hiển thị tiến trình qua tqdm.\n  3. Sau khi hoàn thành, in báo cáo tổng kết (thời gian, tốc độ trung bình, số mã thành công/và thất bại)\n     và lưu log lỗi vào file CSV.\n'
_G='Processing tickers'
_F='avg_speed'
_E='total_time'
_D='fail'
_C='success'
_B='errors'
_A=None
import time,csv,logging
from typing import List,Optional,Dict,Any
from concurrent.futures import ThreadPoolExecutor
import asyncio
from tqdm import tqdm
logger=logging.getLogger(__name__)
def in_jupyter():
	'\n    Kiểm tra xem chương trình có đang chạy trong Jupyter Notebook không.\n    '
	try:A=get_ipython().__class__.__name__;return A=='ZMQInteractiveShell'
	except NameError:return False
class Scheduler:
	def __init__(A,fetcher,validator,transformer,exporter=_A,retry_attempts=3,backoff_factor=2.,max_workers=3,request_delay=.5,rate_limit_wait=35.):'\n        Khởi tạo Scheduler với các thành phần xử lý dữ liệu.\n        \n        :param fetcher: Đối tượng fetcher (lấy dữ liệu).\n        :param validator: Đối tượng validator (kiểm tra dữ liệu).\n        :param transformer: Đối tượng transformer (chuyển đổi dữ liệu).\n        :param exporter: Đối tượng exporter (xuất dữ liệu).\n        :param retry_attempts: Số lần thử lại tối đa (mặc định: 3).\n        :param backoff_factor: Hệ số chờ giữa các lần retry (mặc định: 2.0).\n        :param max_workers: Số workers song song (mặc định: 3, giảm để tránh rate limit).\n        :param request_delay: Delay giữa mỗi request (giây) (mặc định: 0.5).\n        :param rate_limit_wait: Thời gian chờ khi gặp rate limit (giây) (mặc định: 35.0).\n        ';A.fetcher=fetcher;A.validator=validator;A.transformer=transformer;A.exporter=exporter;A.retry_attempts=retry_attempts;A.backoff_factor=backoff_factor;A.max_workers=max_workers;A.request_delay=request_delay;A.rate_limit_wait=rate_limit_wait
	def process_ticker(A,ticker,fetcher_kwargs=_A,exporter_kwargs=_A):
		'\n        Xử lý dữ liệu cho một mã chứng khoán: fetch → validate → transform → export.\n        Thực hiện retry nếu có lỗi.\n        \n        :param ticker: Mã chứng khoán cần xử lý.\n        :param fetcher_kwargs: Tham số bổ sung cho fetcher.\n        :param exporter_kwargs: Tham số bổ sung cho exporter.\n        ';D=exporter_kwargs;B=ticker;C=0;F=False
		while C<A.retry_attempts and not F:
			C+=1
			try:
				time.sleep(A.request_delay);G={}
				if D:G={A:B for(A,B)in D.items()if A!='data'}
				N=A.exporter.preview(B,n=5,**G)if A.exporter and hasattr(A.exporter,'preview')else _A;J=fetcher_kwargs or{};H=A.fetcher.fetch(B,**J)
				if not A.validator.validate(H):raise ValueError(f"Validation failed for {B}.")
				K=A.transformer.transform(H)
				if A.exporter:L=D or{};A.exporter.export(K,B,**L)
				F=True;logger.info(f"[{B}] Successfully processed on attempt {C}.")
			except Exception as E:
				I=str(E).lower()
				if'rate limit'in I or'quá nhiều request'in I:logger.warning(f"[{B}] Rate limited. Waiting {A.rate_limit_wait}s before retry...");time.sleep(A.rate_limit_wait)
				else:
					logger.warning(f"[{B}] Attempt {C} failed with error: {E}")
					if C<A.retry_attempts:M=A.backoff_factor**C;time.sleep(M)
					else:raise E
	async def _run_async(D,tickers,fetcher_kwargs=_A,exporter_kwargs=_A):
		'\n        Thực thi xử lý các ticker song song sử dụng asyncio và ThreadPoolExecutor.\n        Hiển thị tiến trình qua tqdm.\n        \n        :param tickers: Danh sách mã chứng khoán.\n        :return: Bản tóm tắt kết quả.\n        ';B=tickers;E=0;F=0;G=[];N=time.time();C=[];H={};O=D.max_workers;P=asyncio.get_event_loop();Q=ThreadPoolExecutor(max_workers=O)
		for I in B:A=P.run_in_executor(Q,lambda t=I:D.process_ticker(t,fetcher_kwargs=fetcher_kwargs,exporter_kwargs=exporter_kwargs));C.append(A);H[A]=I
		J=tqdm(total=len(C),desc=_G)
		for A in asyncio.as_completed(C):
			try:await A;E+=1
			except Exception as K:F+=1;L=H.get(A,'unknown');G.append((L,str(K)));logger.error(f"Ticker {L} failed with error: {K}")
			J.update(1)
		J.close();M=time.time()-N;R=M/len(B)if B else 0;S={_C:E,_D:F,_E:M,_F:R,_B:G};return S
	def run(B,tickers,fetcher_kwargs=_A,exporter_kwargs=_A,max_workers=_A,request_delay=_A,rate_limit_wait=_A):
		'\n        Chạy quy trình xử lý cho danh sách mã chứng khoán.\n        Nếu số mã > 10, sử dụng xử lý song song (asynchronous).\n        Hiển thị tiến trình và báo cáo tổng kết khi hoàn thành.\n        \n        :param tickers: Danh sách mã chứng khoán.\n        :param fetcher_kwargs: Tham số bổ sung cho fetcher.\n        :param exporter_kwargs: Tham số bổ sung cho exporter.\n        :param max_workers: Số workers song song (override giá trị từ __init__).\n        :param request_delay: Delay giữa requests (giây) (override giá trị từ __init__).\n        :param rate_limit_wait: Thời gian chờ khi rate limit (giây) (override giá trị từ __init__).\n        ';K=rate_limit_wait;J=request_delay;I=max_workers;E=exporter_kwargs;D=fetcher_kwargs;C=tickers
		if I is not _A:B.max_workers=I
		if J is not _A:B.request_delay=J
		if K is not _A:B.rate_limit_wait=K
		S=time.time();F=len(C);T=10;A=_A
		if F>T:
			logger.info('Using parallel processing for tickers.')
			if in_jupyter():
				try:import nest_asyncio as U;U.apply();G=asyncio.get_event_loop();A=G.run_until_complete(B._run_async(C,fetcher_kwargs=D,exporter_kwargs=E))
				except ImportError:logger.warning('nest_asyncio not installed; running without patch.');A=asyncio.run(B._run_async(C,fetcher_kwargs=D,exporter_kwargs=E))
			else:
				try:G=asyncio.get_running_loop();A=G.run_until_complete(B._run_async(C,fetcher_kwargs=D,exporter_kwargs=E))
				except RuntimeError:A=asyncio.run(B._run_async(C,fetcher_kwargs=D,exporter_kwargs=E))
		else:
			logger.info('Processing tickers sequentially.');L=0;M=0;N=[]
			for H in tqdm(C,desc=_G):
				try:B.process_ticker(H,fetcher_kwargs=D,exporter_kwargs=E);L+=1
				except Exception as O:M+=1;N.append((H,str(O)));logger.error(f"Ticker {H} failed with error: {O}")
			P=time.time()-S;V=P/F if F>0 else 0;A={_C:L,_D:M,_E:P,_F:V,_B:N}
		print('Scheduler run complete.');print(f"Success: {A[_C]}, Fail: {A[_D]}");print(f"Total time: {A[_E]:.2f} seconds, Average time per ticker: {A[_F]:.2f} seconds")
		if A[_B]:
			Q='error_log.csv'
			with open(Q,'w',newline='',encoding='utf-8')as W:R=csv.writer(W);R.writerow(['Ticker','Error']);R.writerows(A[_B])
			print(f"Error log saved to {Q}.")