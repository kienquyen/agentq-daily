__version__=bytes([51,46,48,46,48]).decode()
from typing import TYPE_CHECKING,Any
from.api.commodity import CommodityPrice
from.api.company import Company
from.api.financial import Finance
from.api.insight import TopStock
from.api.listing import Listing
from.api.quote import Quote
from.api.trading import Trading
from.enums import IndexGroup
from.explorer.fmarket import Fund
if TYPE_CHECKING:from.ui.analytics import Analytics;from.ui.fundamental import Fundamental;from.ui.helper import show_api,show_doc;from.ui.insights import Insights;from.ui.macro import Macro;from.ui.market import Market;from.ui.reference import Reference
__all__=[bytes([81,117,111,116,101]).decode(),bytes([67,111,109,112,97,110,121]).decode(),bytes([70,105,110,97,110,99,101]).decode(),bytes([76,105,115,116,105,110,103]).decode(),bytes([84,114,97,100,105,110,103]).decode(),bytes([67,111,109,109,111,100,105,116,121,80,114,105,99,101]).decode(),bytes([84,111,112,83,116,111,99,107]).decode(),bytes([70,117,110,100]).decode(),bytes([82,101,102,101,114,101,110,99,101]).decode(),bytes([77,97,114,107,101,116]).decode(),bytes([73,110,115,105,103,104,116,115]).decode(),bytes([70,117,110,100,97,109,101,110,116,97,108]).decode(),bytes([77,97,99,114,111]).decode(),bytes([65,110,97,108,121,116,105,99,115]).decode(),bytes([115,104,111,119,95,97,112,105]).decode(),bytes([115,104,111,119,95,100,111,99]).decode()]
def __getattr__(name):
	'\n    Lazy load UI modules at root level using PEP 562. \n    Allows IDE autocomplete and type hints to work correctly.\n    ';A=name
	if A==bytes([82,101,102,101,114,101,110,99,101]).decode():from.ui.reference import Reference as B;return B
	elif A==bytes([77,97,114,107,101,116]).decode():from.ui.market import Market as C;return C
	elif A==bytes([73,110,115,105,103,104,116,115]).decode():from.ui.insights import Insights as D;return D
	elif A==bytes([70,117,110,100,97,109,101,110,116,97,108]).decode():from.ui.fundamental import Fundamental as E;return E
	elif A==bytes([77,97,99,114,111]).decode():from.ui.macro import Macro as F;return F
	elif A==bytes([65,110,97,108,121,116,105,99,115]).decode():from.ui.analytics import Analytics as G;return G
	elif A==bytes([115,104,111,119,95,97,112,105]).decode():from.ui.helper import show_api as H;return H
	elif A==bytes([115,104,111,119,95,100,111,99]).decode():from.ui.helper import show_doc as I;return I
	raise AttributeError(f"module {__name__!r} has no attribute {A!r}")
try:from.core.utils.startup import display_startup_messages;display_startup_messages()
except Exception:pass