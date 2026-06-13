'\nUI Module - Unified Interface for vnstock-data\n'
from typing import TYPE_CHECKING,Any
if TYPE_CHECKING:from vnstock_data.ui.analytics import Analytics;from vnstock_data.ui.fundamental import Fundamental;from vnstock_data.ui.insights import Insights;from vnstock_data.ui.macro import Macro;from vnstock_data.ui.market import Market;from vnstock_data.ui.reference import Reference
__all__=[bytes([82,101,102,101,114,101,110,99,101]).decode(),bytes([77,97,114,107,101,116]).decode(),bytes([73,110,115,105,103,104,116,115]).decode(),bytes([70,117,110,100,97,109,101,110,116,97,108]).decode(),bytes([77,97,99,114,111]).decode(),bytes([65,110,97,108,121,116,105,99,115]).decode(),bytes([115,104,111,119,95,97,112,105]).decode(),bytes([115,104,111,119,95,100,111,99]).decode()]
def __getattr__(name):
	'\n    Lazy load UI modules using PEP 562. \n    Allows IDE autocomplete and type hints to work correctly.\n    ';A=name
	if A==bytes([82,101,102,101,114,101,110,99,101]).decode():from vnstock_data.ui.reference import Reference as B;return B
	elif A==bytes([77,97,114,107,101,116]).decode():from vnstock_data.ui.market import Market as C;return C
	elif A==bytes([73,110,115,105,103,104,116,115]).decode():from vnstock_data.ui.insights import Insights as D;return D
	elif A==bytes([70,117,110,100,97,109,101,110,116,97,108]).decode():from vnstock_data.ui.fundamental import Fundamental as E;return E
	elif A==bytes([77,97,99,114,111]).decode():from vnstock_data.ui.macro import Macro as F;return F
	elif A==bytes([65,110,97,108,121,116,105,99,115]).decode():from vnstock_data.ui.analytics import Analytics as G;return G
	elif A==bytes([115,104,111,119,95,97,112,105]).decode():from vnstock_data.ui.helper import show_api as H;return H
	elif A==bytes([115,104,111,119,95,100,111,99]).decode():from vnstock_data.ui.helper import show_doc as I;return I
	raise AttributeError(f"module {__name__!r} has no attribute {A!r}")