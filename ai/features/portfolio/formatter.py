# features.portfolio/formatter.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Dict, Any, List, Tuple
import math
import discord

# ============================================================
# Basic helpers
# ============================================================

def _is_bad(x) -> bool:
    return x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))

def _pct(x, nd: int = 1) -> str:
    if _is_bad(x):
        return "N/A"
    try:
        return f"{float(x) * 100:.{nd}f}%"
    except Exception:
        return "N/A"

def _num(x, nd: int = 2) -> str:
    if _is_bad(x):
        return "N/A"
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "N/A"

def _money(x, base: str) -> str:
    if _is_bad(x):
        return "N/A"
    try:
        x = float(x)
    except Exception:
        return "N/A"

    base = (base or "VND").upper()
    if base == "VND":
        ax = abs(x)
        if ax >= 1e9:
            return f"{x/1e9:.2f}B"
        if ax >= 1e6:
            return f"{x/1e6:.2f}M"
        return f"{x:,.0f}"
    return f"{x:,.2f}"

def _arrow_pnl(pnl: float) -> str:
    if _is_bad(pnl):
        return "⚪️→"
    pnl = float(pnl)
    if pnl > 0:
        return "🟢⬆️"
    if pnl < 0:
        return "🔴⬇️"
    return "⚪️→"

def _cut(s: str, n: int = 1024) -> str:
    if s is None:
        return ""
    s = str(s)
    return s if len(s) <= n else (s[: n - 3] + "...")

# ============================================================
# Compact "table" builder for mobile
# ============================================================

def _kv_table(rows: List[Tuple[str, str]], w_key: int = 14) -> str:
    """
    Mobile-friendly pseudo-table (fixed-width).
    """
    lines = []
    for k, v in rows:
        k = (k or "").strip()
        v = (v or "").strip()
        if len(k) > w_key:
            k = k[:w_key]
        lines.append(f"{k.ljust(w_key)} | {v}")
    return "```\n" + "\n".join(lines) + "\n```"

def _mini_table_header(title: str) -> str:
    # not used inside codeblock; kept if you want later
    return title

def _tbl(headers: List[str], rows: List[List[str]], widths: List[int], align: List[str] | None = None) -> str:
    """
    Fixed-width table for Discord codeblock.
    - widths: per-column width
    - align: "l" or "r" per column (default: left)
    """
    if align is None:
        align = ["l"] * len(widths)

    def fmt_cell(s: str, w: int, a: str) -> str:
        s = ("" if s is None else str(s))
        if len(s) > w:
            s = s[: w - 1] + "…"
        return s.rjust(w) if a == "r" else s.ljust(w)

    # header
    h = "  ".join(fmt_cell(headers[i], widths[i], "l") for i in range(len(widths)))
    sep = "  ".join("-" * widths[i] for i in range(len(widths)))

    lines = [h, sep]
    for r in rows:
        r = (r + [""] * len(widths))[: len(widths)]
        lines.append("  ".join(fmt_cell(r[i], widths[i], align[i]) for i in range(len(widths))))

    return "```\n" + "\n".join(lines) + "\n```"

# ============================================================
# Correlation matrix (fixed-width, NO legend)
# ============================================================

def _short_key(k: str, maxlen: int = 8) -> str:
    s = (k or "").strip()
    s = s.replace("CRYPTO:", "CR_").replace("VN:", "VN_").replace("CASH:", "CA_").replace("GOLD:", "AU_")
    s = s.replace("USDT", "")
    s = s.replace("-", "_").replace(" ", "_")
    if len(s) > maxlen:
        s = s[:maxlen]
    return s

def _select_corr_assets(corr, weights_risk: Dict[str, float], max_assets: int = 8):
    if corr is None or getattr(corr, "empty", True):
        return corr

    cols = list(corr.columns)
    if len(cols) <= max_assets:
        return corr

    def _w(c: str) -> float:
        try:
            return float(weights_risk.get(c, 0.0))
        except Exception:
            return 0.0

    ranked = sorted(cols, key=_w, reverse=True)
    keep = ranked[:max_assets]
    try:
        return corr.loc[keep, keep]
    except Exception:
        return corr.iloc[:max_assets, :max_assets]

def _format_corr_matrix(corr, weights_risk: Dict[str, float], max_assets: int = 8, alias_len: int = 8, nd: int = 2) -> str:
    if corr is None or getattr(corr, "empty", True):
        return "N/A"

    corr = _select_corr_assets(corr, weights_risk, max_assets=max_assets)
    if corr is None or getattr(corr, "empty", True):
        return "N/A"

    cols = list(corr.columns)
    aliases = [_short_key(c, alias_len) for c in cols]
    w = max(alias_len, 6)

    header = " " * (w + 1) + " ".join(a.rjust(w) for a in aliases)
    rows = []
    for i, a in enumerate(aliases):
        vals = []
        for j in range(len(aliases)):
            try:
                v = float(corr.iloc[i, j])
            except Exception:
                v = float("nan")
            if math.isnan(v) or math.isinf(v):
                vals.append("".rjust(w))
            else:
                vals.append(f"{v:.{nd}f}".rjust(w))
        rows.append(a.ljust(w) + " " + " ".join(vals))

    txt = "```\n" + header + "\n" + "\n".join(rows) + "\n```"
    return _cut(txt, 1024)

# ============================================================
# Risk / Contrib helpers
# ============================================================

def _top_rc_lines(rc, weights_risk: Dict[str, float], topn: int = 5) -> str:
    if rc is None or getattr(rc, "empty", True):
        return "N/A"

    try:
        items = list(rc.head(topn).items())
    except Exception:
        try:
            items = list(rc.items())[:topn]
        except Exception:
            items = []

    # Make compact list (avoid long lines)
    lines = []
    for k, v in items:
        w = float(weights_risk.get(k, 0.0) or 0.0)
        try:
            v = float(v)
        except Exception:
            v = float("nan")
        lines.append(f"- {k} | W {_pct(w,1)} | RC {_pct(v,0)}")
    return "\n".join(lines) if lines else "N/A"

def _top_contrib_lines(contrib_list: List[Dict[str, Any]], base: str, topn: int = 6) -> str:
    if not contrib_list:
        return "N/A"
    out = []
    for row in contrib_list[:topn]:
        k = row.get("asset", "")
        c = float(row.get("contrib", 0.0) or 0.0)
        pnl = float(row.get("pnl", 0.0) or 0.0)
        out.append(f"- {k} | contrib {_pct(c,2)} | pnl {_money(pnl, base)} {base}")
    return "\n".join(out) if out else "N/A"

# ============================================================
# Tactical helpers
# ============================================================

def _fmt_cash_band(tactical: Dict[str, Any]) -> Tuple[str, str, str]:
    c = (tactical or {}).get("cash") or {}
    w = c.get("cash_weight", None)
    band = c.get("band", None)
    st = str(c.get("state", "N/A"))
    if _is_bad(w) or not isinstance(band, (list, tuple)) or len(band) != 2:
        return ("N/A", "N/A", st)
    return (_pct(float(w), 1), f"{_pct(float(band[0]),0)}–{_pct(float(band[1]),0)}", st)

def _fmt_momentum(tactical: Dict[str, Any]) -> str:
    m = (tactical or {}).get("momentum") or {}
    return f"5D {_pct(m.get('mom_5d'),2)} | 10D {_pct(m.get('mom_10d'),2)} | 30D {_pct(m.get('mom_30d'),2)} | 90D {_pct(m.get('mom_90d'),2)}"

def _fmt_breadth(tactical: Dict[str, Any]) -> Tuple[str, str, str]:
    b = (tactical or {}).get("breadth") or {}
    n = int(b.get("n_positions", 0) or 0)
    p = b.get("pct_above_ma50", None)
    wp = b.get("w_pct_above_ma50", None)
    return (str(n), _pct(p,0), _pct(wp,0))

def _fmt_action(tactical: Dict[str, Any]) -> Tuple[str, str]:
    d = (tactical or {}).get("decision") or {}
    action = str(d.get("action", "N/A"))
    bias = str(d.get("bias", "N/A"))
    return (action, bias)

# ============================================================
# Health highlight rules (short)
# ============================================================

def _health_flags(report: Dict[str, Any]) -> List[str]:
    """
    Keep <= 3 lines for mobile.
    """
    flags = []

    alloc = report.get("allocation") or {}
    cash = float(alloc.get("CASH", 0.0) or 0.0)

    perf60 = report.get("perf60")
    sharpe60 = getattr(perf60, "sharpe", float("nan")) if perf60 else float("nan")
    dd60 = getattr(perf60, "mdd", float("nan")) if perf60 else float("nan")  # if you add mdd into WindowStats later

    # Cash band
    if cash > 0.40:
        flags.append(f"🟡 Cash {_pct(cash,1)} > 40% (deploy chậm)")
    elif cash < 0.10:
        flags.append(f"🔴 Cash {_pct(cash,1)} < 10% (risk cao)")
    else:
        flags.append(f"✅ Cash {_pct(cash,1)} trong band")

    # Sharpe quick
    if _is_bad(sharpe60):
        flags.append("⚪️ Sharpe60 N/A")
    elif sharpe60 >= 0.5:
        flags.append(f"✅ Sharpe60 {_num(sharpe60,2)} tốt")
    elif sharpe60 >= 0.0:
        flags.append(f"🟡 Sharpe60 {_num(sharpe60,2)} trung tính")
    else:
        flags.append(f"🔴 Sharpe60 {_num(sharpe60,2)} xấu")

    # DD quick (fallback if mdd not present)
    if _is_bad(dd60):
        # if your WindowStats currently doesn't include mdd, show ES as proxy
        es = getattr(perf60, "es95", float("nan")) if perf60 else float("nan")
        if not _is_bad(es):
            flags.append(f"🟡 ES95(60D) {_pct(es,2)}")
    else:
        if dd60 >= -0.06:
            flags.append(f"✅ DD60 {_pct(dd60,1)} ok")
        else:
            flags.append(f"🟡 DD60 {_pct(dd60,1)} cao")

    return flags[:3]

# ============================================================
# EMBEDS
# ============================================================

def build_compact_embeds(report: Dict[str, Any]) -> List[discord.Embed]:
    if not report.get("ok"):
        return [discord.Embed(title="❌ Task 3 — PM Report v3", description=str(report.get("error", "Unknown error")))]

    base = report.get("base", "VND")
    nav = float(report.get("nav") or 0.0)
    alloc = report.get("allocation") or {}
    pnl = float(report.get("pnl_unreal") or 0.0)
    pnl_pct = float(report.get("pnl_unreal_pct") or 0.0)
    pnl_badge = _arrow_pnl(pnl)

    perf60 = report.get("perf60")
    perf180 = report.get("perf180")
    regime = report.get("regime")

    weights_risk = report.get("weights_risk") or {}
    warn = report.get("warnings") or []

    e = discord.Embed(title="📊 Institutional PM Report v3")

    # ① Overview (table)
    overview_rows = [
        ("Base", str(base)),
        ("NAV", f"{_money(nav, base)} {base}"),
        ("Alloc", f"VN {_pct(float(alloc.get('VN',0.0)),1)} | CR {_pct(float(alloc.get('CRYPTO',0.0)),1)} | Cash {_pct(float(alloc.get('CASH',0.0)),1)}"),
        ("PnL", f"{pnl_badge} {_money(pnl, base)} {base} ({_pct(pnl_pct,2)})"),
    ]
    e.add_field(name="① PORTFOLIO OVERVIEW", value=_kv_table(overview_rows, w_key=7), inline=False)

    # ② Regime
    if regime:
        reg_rows = [
            ("State", str(regime.label)),
            ("Score", f"{int(regime.score)}/100"),
        ]
    else:
        reg_rows = [("State", "N/A"), ("Score", "N/A")]
    e.add_field(name="② REGIME (60D vs 180D)", value=_kv_table(reg_rows, w_key=7), inline=False)

    # ③ PERFORMANCE (Calendar NAV) — compact table
    if perf60 and perf180:
        headers = ["Win", "Ret", "Vol", "Sharpe", "ES95", "Skew", "n"]
        widths  = [4,     7,     7,     7,       7,     6,     4]
        align   = ["l",  "r",   "r",   "r",     "r",   "r",   "r"]
        rows = [
            ["60D",  _pct(perf60.ann_ret,1),  _pct(perf60.ann_vol,1), _num(perf60.sharpe,2), _pct(perf60.es95,2), _num(perf60.skew,2), str(perf60.n_obs)],
            ["180D", _pct(perf180.ann_ret,1), _pct(perf180.ann_vol,1), _num(perf180.sharpe,2), _pct(perf180.es95,2), _num(perf180.skew,2), str(perf180.n_obs)],
        ]
        e.add_field(name="③ PERFORMANCE (Calendar NAV)", value=_tbl(headers, rows, widths, align), inline=False)
    else:
        e.add_field(name="③ PERFORMANCE (Calendar NAV)", value="N/A", inline=False)

    # ④ Health (<=3 lines)
    health_lines = _health_flags(report)
    e.add_field(name="④ HEALTH HIGHLIGHTS", value="\n".join(health_lines)[:1024], inline=False)

    # ⑤ RISK (VNIndex) — Portfolio & RiskOnly (fixed columns)
    beta60  = report.get("beta60") or {}
    beta180 = report.get("beta180") or {}
    b60     = report.get("beta_riskonly_60") or {}
    b180    = report.get("beta_riskonly_180") or {}

    def _beta_cells(d: Dict[str, Any]) -> List[str]:
        n = d.get("n", None)
        n_txt = "NA"
        try:
            if isinstance(n, (int, float)) and not math.isnan(float(n)):
                n_txt = str(int(n))
        except Exception:
            pass
        return [
            _num(d.get("beta"), 2),
            _num(d.get("beta_down"), 2),
            _num(d.get("corr"), 2),
            n_txt
        ]

    vol_60  = _pct(getattr(perf60, "ann_vol", float("nan")), 1) if perf60 else "N/A"
    vol_180 = _pct(getattr(perf180, "ann_vol", float("nan")), 1) if perf180 else "N/A"

    headers = ["Type", "β", "βd", "ρ", "n"]
    widths  = [7,      5,   5,   5,   4]
    align   = ["l",   "r", "r", "r", "r"]
    rows = [
        ["Vol",  vol_60, vol_180, "", ""],  # special row (2 vols)
        ["Port60",  *_beta_cells(beta60)],
        ["Port180", *_beta_cells(beta180)],
        ["Risk60",  *_beta_cells(b60)],
        ["Risk180", *_beta_cells(b180)],
    ]

    # Render: Vol row as separate line to avoid weird columns
    risk_txt = (
        "```\n"
        f"Vol60 {vol_60}   Vol180 {vol_180}\n"
        + _tbl(headers, rows[1:], widths, align).strip("`")  # embed table without nested code fences
        + "\n```"
    )
    e.add_field(name="⑤ RISK (VNIndex) — Portfolio & RiskOnly", value=_cut(risk_txt, 1024), inline=False)
    # ⑥ Risk Drivers (RC)
    rc60 = report.get("rc60")
    rc_txt = _top_rc_lines(rc60, weights_risk, topn=5)
    e.add_field(name="⑥ RISK DRIVERS (RC, overlap 60D)", value=_cut(rc_txt, 1024), inline=False)

    # ⑦ TACTICAL (Daily) — fixed table + highlighted action
    tactical = report.get("tactical") or {}
    if tactical:
        cash_w, cash_band, cash_state = _fmt_cash_band(tactical)
        npos, p_above, wp_above = _fmt_breadth(tactical)
        action, bias = _fmt_action(tactical)

        mom = (tactical.get("momentum") or {})
        m5  = _pct(mom.get("mom_5d"), 2)
        m10 = _pct(mom.get("mom_10d"), 2)
        m30 = _pct(mom.get("mom_30d"), 2)
        m90 = _pct(mom.get("mom_90d"), 2)

        headers = ["Item", "V1", "V2", "V3", "V4"]
        widths  = [6,      10,   10,   10,   10]
        align   = ["l",    "r",  "r",  "r",  "r"]
        rows = [
            ["Cash", cash_w, cash_band, cash_state, ""],
            ["MA50", f"npos {npos}", f">{p_above}", f"W {wp_above}", ""],
            ["Mom",  m5, m10, m30, m90],
        ]

        e.add_field(
            name="⑦ TACTICAL (Daily)",
            value=_tbl(headers, rows, widths, align),
            inline=False
        )

        # ---------- Highlighted Action (separate line) ----------
        action_block = (
            "```\n"
            f"▶ ACTION: {action}\n"
            f"   Bias : {bias}\n"
            "```"
        )

        e.add_field(
            name="🎯 FINAL DECISION",
            value=action_block,
            inline=False
        )
        
        # keep rules short (<=2 lines)
        rules = ((tactical.get("decision") or {}).get("rules") or [])[:2]
        if rules:
            e.add_field(name="Rules (short)", value=_cut("\n".join([f"- {r}" for r in rules]), 1024), inline=False)

    if warn:
        e.add_field(name="Notes", value=_cut("\n".join([f"⚠️ {w}" for w in warn]), 1024), inline=False)

    e.set_footer(text="Tip: View Details for Corr Matrix + Contribution.")
    return [e]


def build_details_embeds(report: Dict[str, Any]) -> List[discord.Embed]:
    if not report.get("ok"):
        return [discord.Embed(title="❌ Task 3 — Details", description=str(report.get("error", "Unknown error")))]

    base = report.get("base", "VND")
    weights_risk = report.get("weights_risk") or {}

    embeds: List[discord.Embed] = []

    # A) Contribution (compact)
    e2 = discord.Embed(title="💰 Details — Contribution (Calendar NAV)")
    e2.add_field(name="Top 60D", value=_cut(_top_contrib_lines(report.get("contrib60") or [], base, topn=8), 1024), inline=False)
    e2.add_field(name="Top 180D", value=_cut(_top_contrib_lines(report.get("contrib180") or [], base, topn=8), 1024), inline=False)
    embeds.append(e2)

    # B) Correlation matrix (NO LEGEND, fixed-width)
    e3 = discord.Embed(title="📐 Details — Correlation Matrix (Overlap)")
    m60 = _format_corr_matrix(report.get("corr60"), weights_risk=weights_risk, max_assets=8, alias_len=8, nd=2)
    m180 = _format_corr_matrix(report.get("corr180"), weights_risk=weights_risk, max_assets=8, alias_len=8, nd=2)
    e3.add_field(name="Corr 60D (top weights)", value=m60, inline=False)
    e3.add_field(name="Corr 180D (top weights)", value=m180, inline=False)
    embeds.append(e3)

    # C) RC details
    e4 = discord.Embed(title="🧮 Details — Risk Contribution (Overlap RC)")
    rc60 = report.get("rc60")
    rc180 = report.get("rc180")
    e4.add_field(name="RC 60D", value=_cut(_top_rc_lines(rc60, weights_risk, topn=12), 1024), inline=False)
    e4.add_field(name="RC 180D", value=_cut(_top_rc_lines(rc180, weights_risk, topn=12), 1024), inline=False)
    embeds.append(e4)

    return embeds