'Flexible data exporter with support for trading platforms.'
_H='sample_data'
_G='csv'
_F='close'
_E='low'
_D='high'
_C='open'
_B='volume'
_A='time'
from pathlib import Path
from enum import Enum
import pandas as pd,pyarrow as pa,pyarrow.parquet as pq
from..schemas import get_dynamic_schema
class ExportFormat(Enum):PARQUET='parquet';FEATHER='feather';PANDAS='pkl';AMIBROKER=_G;MT4=_G;MT5=_G
class FlexibleExporter:
	def __init__(A,base_path):A.base_path=Path(base_path);A.base_path.mkdir(parents=True,exist_ok=True)
	def _prepare_amibroker_data(C,df):
		'Prepare DataFrame for AmiBroker format.';B='Date';A=df;A=A.copy()
		if _A in A.columns:A[B]=pd.to_datetime(A[_A]).dt.strftime('%Y%m%d')
		return A[[B,_C,_D,_E,_F,_B]].rename(columns={_C:'Open',_D:'High',_E:'Low',_F:'Close',_B:'Volume'})
	def _prepare_mt4_data(D,df):
		'Prepare DataFrame for MT4 format.';C='TIME';B='DATE';A=df;A=A.copy()
		if _A in A.columns:A[B]=pd.to_datetime(A[_A]).dt.strftime('%Y.%m.%d');A[C]=pd.to_datetime(A[_A]).dt.strftime('%H:%M')
		return A[[B,C,_C,_D,_E,_F,_B]].rename(columns={_C:'OPEN',_D:'HIGH',_E:'LOW',_F:'CLOSE',_B:'VOLUME'})
	def _prepare_mt5_data(A,df):'Prepare DataFrame for MT5 format.';return A._prepare_mt4_data(df)
	def export(D,df,name,format=ExportFormat.PARQUET,**C):
		'\n        Export data to specified format.\n        \n        Args:\n            df: Input DataFrame with OHLCV data\n            name: Output filename (without extension)\n            format: Export format (PARQUET, FEATHER, PANDAS, AMIBROKER, MT4, MT5)\n            **kwargs: Additional arguments passed to the underlying writer\n            \n        Returns:\n            str: Path to the exported file\n        ';F=False;A=df;B=D.base_path/f"{name}.{format.value}"
		if format==ExportFormat.PARQUET:G=pa.Table.from_pandas(A,schema=get_dynamic_schema(A));pq.write_table(G,B,**C)
		elif format==ExportFormat.FEATHER:A.to_feather(B,**C)
		elif format==ExportFormat.PANDAS:A.to_pickle(B,**C)
		elif format==ExportFormat.AMIBROKER:E=D._prepare_amibroker_data(A);E.to_csv(B,index=F,**C)
		elif format in(ExportFormat.MT4,ExportFormat.MT5):E=D._prepare_mt4_data(A)if format==ExportFormat.MT4 else D._prepare_mt5_data(A);E.to_csv(B,index=F,**C)
		return str(B)
	def load(C,name,format,**A):
		'\n        Load data from file.\n        \n        Args:\n            name: Input filename (without extension)\n            format: Input format (PARQUET, FEATHER, PANDAS, AMIBROKER, MT4, MT5)\n            **kwargs: Additional arguments passed to the underlying reader\n            \n        Returns:\n            pd.DataFrame: Loaded data\n        ';B=C.base_path/f"{name}.{format.value}"
		if format==ExportFormat.PARQUET:return pq.read_table(B,**A).to_pandas()
		elif format==ExportFormat.FEATHER:return pd.read_feather(B,**A)
		elif format==ExportFormat.PANDAS:return pd.read_pickle(B,**A)
		elif format in(ExportFormat.AMIBROKER,ExportFormat.MT4,ExportFormat.MT5):return pd.read_csv(B,**A)
if __name__=='__main__':exporter=FlexibleExporter('./data');df=pd.DataFrame({_A:pd.date_range('2025-01-01',periods=5,freq='1min'),'price':[100.5,101.,101.5,100.8,101.2],_B:[1000,1500,2000,1200,1800]});exporter.export(df,_H,ExportFormat.PARQUET);exporter.export(df,_H,ExportFormat.FEATHER);loaded_df=exporter.load(_H,ExportFormat.PARQUET);print(loaded_df.head())