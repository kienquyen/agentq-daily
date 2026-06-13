"""Domain Models - Core Data Structures"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Task1Result:
    ann_ret_24m: float
    ann_vol_24m: float
    sharpe_24m: float
    beta_12m: float
    beta_6m: float
    beta_up_12m: float
    beta_dn_12m: float
    convexity_12m: float
    alpha_36m: float
    bench_ret_24m: float
    bench_vol_24m: float
    bench_sharpe_24m: float
    agentq_rating: int
    agentq_bucket: str
    agentq_risks: List[str]
    bullets: List[str]
    vni_ret_6m: float
    vni_ret_1m: float
    bench_sharpe_12m: float
    vni_vol_1m: float
    vni_vol_6m: float
    vni_vol_spike_ratio: float
    meta: Dict[str, Any]


@dataclass
class Task2Result:
    ticker: str
    company_type: str
    periods: List[str]
    income_snapshot: str
    balance_snapshot: str
    cash_snapshot: str
    valuation_snapshot: str
