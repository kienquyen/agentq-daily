'\nReference Layer Entry Point.\n'
from vnstock_data.ui.domains.reference.bond import BondReference
from vnstock_data.ui.domains.reference.company import CompanyReference
from vnstock_data.ui.domains.reference.derivatives import DerivativesReference,FuturesReference,WarrantReference
from vnstock_data.ui.domains.reference.equity import EquityReference
from vnstock_data.ui.domains.reference.etf import ETFReference
from vnstock_data.ui.domains.reference.events import EventsReference
from vnstock_data.ui.domains.reference.fund import FundReference
from vnstock_data.ui.domains.reference.index import IndexReference
from vnstock_data.ui.domains.reference.industry import IndustryReference
from vnstock_data.ui.domains.reference.market import MarketReference
from vnstock_data.ui.domains.reference.search import SearchReference
class Reference:
	"\n    Reference Data Layer (Layer 1).\n    Provides access to static/master data for various domains.\n    \n    ✅ METHODS AVAILABLE:\n    \n    - company(symbol) → CompanyReference: General info, shareholders, officers, subsidiaries, events.\n    - futures(symbol) → FuturesReference: Index futures specifications and info.\n    - warrant(symbol) → WarrantReference: Covered warrant specifications and info.\n    \n    ✅ PROPERTIES AVAILABLE:\n    \n    - equity        → EquityReference: List equity symbols (by exchange, group, industry).\n    - index         → IndexReference: List index symbols and their compositions.\n    - etf           → ETFReference: List all ETF symbols.\n    - fund          → FundReference: List all mutual fund symbols.\n    - bond          → BondReference: List government and corporate bonds.\n    - industry      → IndustryReference: List ICB industry classifications.\n    - events        → EventsReference: Market events calendar.\n    - market        → MarketReference: Live market status (ATO, ATC, OPEN, CLOSED).\n    - search        → SearchReference: Global asset search (Dukascopy/MSN).\n    \n    Example:\n        ref = Reference()\n        fpt_info = ref.company('FPT').info()\n        all_stocks = ref.equity.list()\n    "
	def company(A,symbol):"\n        Access company-specific reference data.\n        \n        Args:\n            symbol (str): Ticker symbol (e.g., 'VNM', 'TCB').\n        ";return CompanyReference(symbol)
	def futures(A,symbol=None):"\n        Access index futures reference data (listing or symbol-specific info).\n        \n        Args:\n            symbol (str, optional): Futures symbol (e.g., 'VN30F2503', 'VN30F1M').\n                                    If None, returns listing interface.\n            \n        Example:\n            r = Reference()\n            # List all futures indices\n            futures_list = r.futures().list()\n            \n            # Get specific futures info\n            futures_info = r.futures('VN30F2503').info()\n        ";return FuturesReference(symbol)
	def warrant(A,symbol=None):"\n        Access covered warrant reference data (info, specifications, pricing).\n        \n        Args:\n            symbol (str): Warrant symbol (e.g., 'CACB2511', 'CACB25C100').\n            \n        Example:\n            r = Reference()\n            warrant_info = r.warrant('CACB2511').info()\n        ";return WarrantReference(symbol)
	@property
	def industry(self):'Access industry reference data.';return IndustryReference()
	@property
	def fund(self):'\n        Master data for Mutual Funds (Chứng Chỉ Quỹ).\n        ';return FundReference()
	@property
	def etf(self):'Access ETF reference data.';return ETFReference()
	@property
	def equity(self):'Access equity reference data.';return EquityReference()
	@property
	def index(self):'Access index reference data.';return IndexReference()
	@property
	def bond(self):'Access bond reference data.';return BondReference()
	@property
	def events(self):'Access events reference data (calendar, etc.).';return EventsReference()
	@property
	def search(self):'Access global symbol search.';return SearchReference()
	@property
	def market(self):'Access live market status.';return MarketReference()
	def derivatives(B):"\n        [DEPRECATED] Access derivatives reference data.\n        \n        To fix: Replace `Reference().derivatives().futures(symbol).info()` with `Reference().futures(symbol).info()`\n        \n        Examples:\n            # Old way (will raise warning):\n            r.derivatives().futures('VN30F2503').info()\n            \n            # New direct way:\n            r.futures('VN30F2503').info()\n        \n        Returns:\n            DerivativesReference: Provides access to .warrant() and .futures() sub-domains.\n        ";import warnings as A;A.warn(bytes([82,101,102,101,114,101,110,99,101,46,100,101,114,105,118,97,116,105,118,101,115,40,41,32,105,115,32,100,101,112,114,101,99,97,116,101,100,46,32,85,115,101,32,82,101,102,101,114,101,110,99,101,46,102,117,116,117,114,101,115,40,115,121,109,98,111,108,41,32,111,114,32,82,101,102,101,114,101,110,99,101,46,119,97,114,114,97,110,116,40,115,121,109,98,111,108,41,32,100,105,114,101,99,116,108,121,46,32,69,120,97,109,112,108,101,58,32,114,46,102,117,116,117,114,101,115,40,39,86,78,51,48,70,50,53,48,51,39,41,46,105,110,102,111,40,41,32,105,110,115,116,101,97,100,32,111,102,32,114,46,100,101,114,105,118,97,116,105,118,101,115,40,41,46,102,117,116,117,114,101,115,40,39,86,78,51,48,70,50,53,48,51,39,41,46,105,110,102,111,40,41,46,32,68,101,112,114,101,99,97,116,101,100,32,109,101,116,104,111,100,32,119,105,108,108,32,98,101,32,114,101,109,111,118,101,100,32,97,102,116,101,114,32,51,49,47,56,47,50,48,50,54,46]).decode(),DeprecationWarning,stacklevel=2);return DerivativesReference()