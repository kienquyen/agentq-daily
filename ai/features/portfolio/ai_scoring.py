# features.portfolio/ai_scoring.py
# -*- coding: utf-8 -*-

from typing import Dict, Any

async def ai_score_stub(
    nav: Dict[str, Any],
    regime: Dict[str, Any],
    sharpe: Dict[str, Any],
    beta_btc: Dict[str, Any],
    beta_vni: Dict[str, Any],
    risk: int,
) -> Dict[str, Any]:
    w_vn = nav["w_vn"]
    w_crypto = nav["w_crypto"]
    w_cash = nav["w_cash"]
    top1 = nav["concentration"]["top1"]
    top3 = nav["concentration"]["top3"]
    flags = nav.get("flags", {})

    score = 82

    # penalty by constraints
    if "crypto_cap_breach" in flags:
        score -= 10
    if "cash_buffer_low" in flags:
        score -= 8
    if "top3_concentration_high" in flags:
        score -= 8
    if "max_pos_breach" in flags:
        score -= 6

    # sanity on risk
    if risk >= 8 and w_cash < 0.08:
        score -= 4  # aggressive without buffer
    if risk <= 4 and w_crypto > 0.20:
        score -= 6  # conservative but high crypto

    score = max(0, min(100, score))
    verdict = "GOOD" if score >= 70 else ("OK" if score >= 55 else "FRAGILE")

    reasons = [
        f"Allocation VN/Crypto/Cash = {w_vn:.0%}/{w_crypto:.0%}/{w_cash:.0%}",
        f"Concentration Top1/Top3 = {top1:.0%}/{top3:.0%}",
        f"Sharpe30={sharpe.get('sharpe_30d')} | BetaBTC3M={beta_btc.get('beta_btc_3m')} | BetaVNI6M={beta_vni.get('beta_vni_6m')}",
    ]
    if flags:
        reasons.append("Flags: " + ", ".join(flags.keys()))

    actions = {"reduce": [], "monitor": [], "add": [], "rebalance": []}

    if "crypto_cap_breach" in flags:
        actions["reduce"].append("Trim crypto về mức cap để giảm drawdown risk.")
    if "cash_buffer_low" in flags:
        actions["rebalance"].append("Tăng cash buffer ≥10% để có optionality.")
    if top3 > 0.60:
        actions["rebalance"].append("Giảm tập trung Top-3, tăng diversification.")
    if sharpe.get("sharpe_30d") is not None and sharpe["sharpe_30d"] < 0.3:
        actions["monitor"].append("Sharpe ngắn hạn thấp: kiểm tra chất lượng phân bổ & timing.")
    if beta_btc.get("beta_btc_3m") is not None and beta_btc["beta_btc_3m"] > 0.8:
        actions["monitor"].append("Beta vs BTC cao: portfolio nhạy với biến động crypto.")

    return {
        "quality_score": score,
        "verdict": verdict,
        "top_reasons": reasons[:3],
        "actions": actions,
        "commentary": "PM view: Ưu tiên giảm concentration + quản trị beta/vol trước khi tăng risk.",
    }