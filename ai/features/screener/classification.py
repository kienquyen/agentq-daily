"""
features/screener/classification.py
Screener 2.0 — lọc VN200, dựa 100% quant analysis
Tiêu chí:
  - BUY   → pass nếu GT TB ≥ 10 tỷ/ngày
  - WAIT  → pass nếu close > MA50 VÀ không có red flag VÀ GT TB ≥ 10 tỷ/ngày
  - AVOID → loại bỏ

Rate-limit guard (Golden Member = 500 req/min):
  - Semaphore(2)  → tối đa 2 mã xử lý đồng thời
  - sleep(2.0s)   → delay trước mỗi lần gọi API
  - Batch pause   → nghỉ 10s sau mỗi 25 mã để tránh burst
  - No retry on timeout → tránh nhân đôi lượng request
"""

import discord
import asyncio
import concurrent.futures
import datetime
import math
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

# ── Rate limit constants ────────────────────────────────────────────────────
_CONCURRENCY      = 3       # mã xử lý song song (3 = an toàn với 500 req/min Golden)
_STOCK_DELAY      = 1.5     # giây nghỉ trước mỗi mã
_BATCH_SIZE       = 50      # số mã mỗi batch
_BATCH_PAUSE      = 5.0     # giây nghỉ giữa các batch
_STOCK_TIMEOUT    = 20.0    # giây timeout per mã
_MAX_THREADS      = 20      # bounded thread pool (3 concurrent × 7 API calls/mã)
_SCAN_TIMEOUT     = 25 * 60 # 25 phút tổng (dự phòng 65s × vài lần rate limit)

from features.quant.analysis import compute_task1_v2, Task1V2RuleConfig, RF_ANNUAL
from app.vnstock_core.core import fetch_ohlcv as _fetch_ohlcv

# ── VN200 FALLBACK (dùng khi API fetch_symbols_by_group thất bại) ──────────
VN200_FALLBACK: List[str] = [
    # VN30
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "NVL", "PDR", "PLX", "POW", "SAB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
    # VN70
    "AGR", "ANV", "BWE", "C4G", "CII", "CMG", "DGC", "DGW", "DIG", "DPM",
    "DXG", "EIB", "FRT", "GEX", "GMD", "HAH", "HDG", "HHV", "HSG", "HUT",
    "IDC", "IMP", "KBC", "KDH", "LPB", "MSB", "NAB", "NKG", "NLG", "NT2",
    "OCB", "PAN", "PC1", "PHR", "PNJ", "PVD", "PVS", "PVT", "QNS", "REE",
    "SBT", "SCS", "SHB", "SKG", "SSB", "TCH", "THG", "TLG", "TV2", "VCS",
    "VGC", "VGI", "VHC", "VIX", "VND", "VTP", "VGS", "DHC", "PVB",
    "DCM", "DBC", "HCM", "MBS", "SHS", "VCI", "KDC", "GTN", "LHG",
    # VN100 → VN200 (mid-cap mở rộng)
    "ACV", "AGG", "AMD", "APH", "ASM", "BSR", "BTP", "CHP", "CLC", "CSM",
    "DHA", "DHG", "DLG", "DRC", "DSN", "DXS", "ELC", "EVE", "FCN", "FIT",
    "FLC", "GEG", "GIL", "HAG", "HBC", "HDC", "HGM", "HII", "HMC", "HNG",
    "HPX", "HQC", "HTN", "HVN", "IJC", "ITA", "ITC", "KHG", "KOS", "L14",
    "LAF", "LCG", "LDG", "LSS", "MHC", "MIG", "MSH", "MVB", "NAF", "NBB",
    "NHH", "NHT", "NSC", "NTH", "NVT", "OPC", "PDN", "PET", "PGI", "PNG",
    "PPC", "PTB", "PTC", "PVE", "PVG", "RAL", "SAF", "SAP", "SBA", "SBG",
    "SCI", "SFG", "SGN", "SGT", "SHA", "SHI", "SHN", "SHP", "SIP", "SJD",
    "SKD", "SMA", "SMC", "SPM", "SRC", "SRF", "SSC", "SSF", "STG", "STP",
    "SVT", "TBC", "TCD", "TCL", "TDM", "TDN", "TDW", "TIX", "TLH", "TLX",
    "TMP", "TNT", "TPC", "TRA", "TRC", "TSC", "TTC", "TV3", "UIC", "VCF",
    "VDS", "VFG", "VGP", "VHL", "VID", "VLC", "VNA", "VNE", "VNR", "VNS",
    "VOS", "VRC", "VRG", "VSC", "VSH", "VSN", "VTA", "VTC", "VTO", "WCS",
]


def _uniq(seq: List[str]) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for x in seq:
        t = str(x).strip().upper()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _fmt_vol(vol: float) -> str:
    if not math.isfinite(vol) or vol <= 0:
        return "N/A"
    if vol >= 1_000_000:
        return f"{vol / 1_000_000:.1f}Tr"
    if vol >= 1_000:
        return f"{vol / 1_000:.0f}K"
    return str(int(vol))


def _fmt_pct(v: float) -> str:
    if not math.isfinite(v):
        return " N/A"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v*100:.1f}%"


def _fmt_f(v: float, nd: int = 2) -> str:
    if not math.isfinite(v):
        return "N/A"
    return f"{v:.{nd}f}"


# ── SINGLE STOCK COMPUTE ────────────────────────────────────────────────────

async def _compute_one(
    ticker: str,
    rf_annual: float,
    cfg: Task1V2RuleConfig,
    sem: asyncio.Semaphore,
    vnindex_cache: Optional[dict] = None,
) -> Optional[dict]:
    """
    Returns dict if stock passes screener, else None.
    Filter:
      BUY  → pass (kể cả có red flag — engine đã xét)
      WAIT → pass nếu close > MA50 VÀ không có red flag nào
      AVOID → skip

    Rate-limit safe: no retry on timeout, longer sleep, low concurrency.
    """
    async with sem:
        try:
            # Delay để tránh burst — giãn request ra theo thời gian
            await asyncio.sleep(_STOCK_DELAY)

            m, d = await asyncio.wait_for(
                compute_task1_v2(
                    ticker=ticker,
                    rf_annual=rf_annual,
                    cfg=cfg,
                    vnindex_cache=vnindex_cache,
                ),
                timeout=_STOCK_TIMEOUT,
            )

            role   = str(d.role).upper()
            action = str(d.action).upper()

            is_buy  = action == "BUY"
            is_wait = action == "WAIT" and m.above_ma50

            # Loại ngay nếu không vào diện xét
            if not (is_buy or is_wait):
                return None

            # WAIT: loại nếu có bất kỳ red flag nào trong risk_triggers
            if is_wait and d.risk_triggers:
                return None

            # ── Fetch RSI14 (hiển thị tham khảo) ────────────────────
            rsi14: Optional[float] = None
            try:
                await asyncio.sleep(0.5)   # micro-pause trước RSI call
                from app.vnstock_core.core import fetch_technical_signals
                signals = await asyncio.to_thread(
                    fetch_technical_signals, ticker
                )
                rsi14 = signals.get("rsi14") if signals else None
            except Exception:
                pass

            # ── Fetch volume/value (21 ngày gần nhất) ───────────────
            avg_vol    = float("nan")
            avg_val_ty = float("nan")
            try:
                await asyncio.sleep(0.5)   # micro-pause trước OHLCV call
                now        = datetime.datetime.now()
                start_date = (now - datetime.timedelta(days=45)).strftime("%Y-%m-%d")
                end_date   = now.strftime("%Y-%m-%d")

                df = await asyncio.to_thread(_fetch_ohlcv, ticker, start_date, end_date)

                if df is None or df.empty:
                    # Thử lùi ngày kết thúc (max 5 lần) — không tạo vòng lặp API
                    for days_back in range(1, 6):
                        await asyncio.sleep(0.3)
                        prev = (now - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
                        df   = await asyncio.to_thread(_fetch_ohlcv, ticker, start_date, prev)
                        if df is not None and not df.empty:
                            break

                if df is not None and not df.empty and "volume" in df.columns and "close" in df.columns:
                    df21     = df.tail(21)
                    vols     = pd.to_numeric(df21["volume"], errors="coerce").fillna(0)
                    closes   = pd.to_numeric(df21["close"],  errors="coerce").fillna(0)
                    r_closes = closes.apply(lambda x: x * 1000 if x < 1500 else x)
                    avg_vol    = float(vols.mean())
                    avg_val_ty = float((vols * r_closes).mean()) / 1_000_000_000
            except Exception:
                pass

            # Loại mã có thanh khoản thấp (GT TB < 10 tỷ/ngày)
            if not math.isfinite(avg_val_ty) or avg_val_ty < 10:
                return None

            return {
                "ticker":        ticker,
                "role":          role,
                "action":        action,
                "above_ma50":    m.above_ma50,
                "rsi14":         rsi14,
                "momentum":      m.momentum_score,
                "sharpe_24m":    m.sharpe_24m,
                "excess_ret_3m": m.excess_ret_3m,
                "ret_1m":        m.ret_1m,
                "avg_vol":       avg_vol,
                "avg_val_ty":    avg_val_ty,
            }

        except asyncio.TimeoutError:
            return None
        except SystemExit:
            # vnstock gọi sys.exit() khi rate limit — sleep 65s rồi bỏ qua mã này
            print(f"[screener] {ticker}: rate limit hit — sleeping 65s")
            await asyncio.sleep(65)
            return None
        except Exception:
            await asyncio.sleep(1.0)
            return None


# ── MAIN HANDLER ────────────────────────────────────────────────────────────

async def handle_screener(interaction: discord.Interaction) -> None:
    try:
        try:
            if not getattr(interaction.response, "is_done", lambda: False)():
                await interaction.response.defer(ephemeral=False)
        except Exception:
            pass

        # ── Fetch VN200 universe ─────────────────────────────────────
        universe: List[str] = []
        try:
            from app.vnstock_core.core import fetch_symbols_by_group
            raw = await asyncio.to_thread(fetch_symbols_by_group, "VN200")
            if raw:
                universe = _uniq(raw)
        except Exception:
            pass

        if not universe:
            universe = _uniq(VN200_FALLBACK)
            src_note = "fallback"
        else:
            src_note = "API"

        msg = await interaction.followup.send(
            f"🔍 Bắt đầu quét **VN200** ({len(universe)} mã, nguồn: {src_note})…",
            wait=True,
        )

        cfg = Task1V2RuleConfig()
        sem = asyncio.Semaphore(_CONCURRENCY)

        results:   List[dict] = []
        processed: int        = 0
        timed_out: bool       = False

        # ── Pre-warm VNINDEX cache (1 lần cho toàn bộ scan) ─────────────
        vnindex_cache: Dict[str, Any] = {}
        try:
            from app.vnstock_core.core import fetch_vnindex as _fvni
            _now = pd.Timestamp.now(tz="UTC")
            _end = _now.date().isoformat()
            _s24 = (_now - pd.DateOffset(months=24)).date().isoformat()
            _s36 = (_now - pd.DateOffset(months=36)).date().isoformat()
            for _start in (_s24, _s36):
                _key = f"{_start}|{_end}"
                try:
                    _vni = await asyncio.to_thread(_fvni, _start, _end)
                    if not _vni.empty:
                        vnindex_cache[_key] = _vni
                except Exception:
                    pass
            print(f"[screener] VNINDEX cache: {len(vnindex_cache)}/2 entries pre-warmed")
        except Exception as _e:
            print(f"[screener] VNINDEX cache warmup failed: {_e}")

        # ── Bounded thread pool: ngăn zombie threads lấp đầy default pool ──
        loop = asyncio.get_running_loop()
        _bounded_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=_MAX_THREADS, thread_name_prefix="screener"
        )
        _old_executor = getattr(loop, "_default_executor", None)
        loop.set_default_executor(_bounded_executor)

        async def _run_scan() -> None:
            nonlocal processed, timed_out
            # ── Xử lý theo batch để tránh rate limit ────────────────────
            for batch_start in range(0, len(universe), _BATCH_SIZE):
                batch = universe[batch_start : batch_start + _BATCH_SIZE]

                tasks = [
                    asyncio.create_task(_compute_one(tkr, RF_ANNUAL, cfg, sem, vnindex_cache))
                    for tkr in batch
                ]

                for task in asyncio.as_completed(tasks):
                    r = await task
                    processed += 1
                    if isinstance(r, dict):
                        results.append(r)

                    if processed % 10 == 0 or processed == len(universe):
                        buy_cnt  = sum(1 for x in results if x["action"] == "BUY")
                        wait_cnt = sum(1 for x in results if x["action"] == "WAIT")
                        try:
                            await msg.edit(
                                content=(
                                    f"🔍 Đang quét VN200… ({processed}/{len(universe)}) "
                                    f"→ 🛒 {buy_cnt} MUA · ⏳ {wait_cnt} CHỜ"
                                )
                            )
                        except Exception:
                            pass

                # Nghỉ giữa các batch (trừ batch cuối)
                if batch_start + _BATCH_SIZE < len(universe):
                    await asyncio.sleep(_BATCH_PAUSE)

        try:
            await asyncio.wait_for(_run_scan(), timeout=_SCAN_TIMEOUT)
        except asyncio.TimeoutError:
            timed_out = True
            buy_cnt  = sum(1 for x in results if x["action"] == "BUY")
            wait_cnt = sum(1 for x in results if x["action"] == "WAIT")
            try:
                await msg.edit(
                    content=(
                        f"⏰ Quét VN200 hết giờ sau {_SCAN_TIMEOUT // 60} phút "
                        f"({processed}/{len(universe)} mã). "
                        f"Kết quả tạm: 🛒 {buy_cnt} MUA · ⏳ {wait_cnt} CHỜ — xem bên dưới."
                    )
                )
            except Exception:
                pass
        finally:
            # Khôi phục executor cũ; không chờ zombie threads (wait=False)
            # _old_executor có thể là None (chưa được set) → tạo mới thay vì pass None
            try:
                if _old_executor is not None:
                    loop.set_default_executor(_old_executor)
                else:
                    # Reset về None để loop tự tạo ThreadPoolExecutor mặc định lần sau
                    loop._default_executor = None  # type: ignore[attr-defined]
            except Exception:
                pass
            _bounded_executor.shutdown(wait=False)

        # ── Không có kết quả ─────────────────────────────────────────
        if not results:
            await msg.edit(
                content=(
                    "❌ Quét xong VN200 nhưng không có mã nào thỏa tiêu chí.\n"
                    "Tiêu chí: MUA hoặc (CHỜ + Close > MA50 + không có red flag) · GT TB ≥ 10 tỷ/ngày."
                )
            )
            return

        # ── Sort: BUY trước WAIT, trong mỗi nhóm sort theo avg_val_ty ──
        buy_stocks  = sorted(
            [x for x in results if x["action"] == "BUY"],
            key=lambda x: x["avg_val_ty"] if math.isfinite(x["avg_val_ty"]) else 0,
            reverse=True,
        )
        wait_stocks = sorted(
            [x for x in results if x["action"] == "WAIT"],
            key=lambda x: x["avg_val_ty"] if math.isfinite(x["avg_val_ty"]) else 0,
            reverse=True,
        )

        # Top 5 BUY + top 5 WAIT (tối đa 10)
        top_buy  = buy_stocks[:5]
        top_wait = wait_stocks[:5]
        display  = top_buy + top_wait

        # ── Build table ───────────────────────────────────────────────
        # Columns: MÃ | HÀNH ĐỘNG | VAI TRÒ | RSI | MOM | SHP24M | EXC3M | GIÁ TRỊ TB
        HDR = f"{'MÃ':<5}  {'HÀNH ĐỘNG':<8}  {'VAI TRÒ':<12}  {'RSI':>4}  {'MOM':>5}  {'SHP24':>5}  {'EXC3M':>6}  {'GT TB (Tỷ)':>10}"
        SEP = "─" * len(HDR)

        rows = []
        for st in display:
            act_tag  = "🛒 MUA" if st["action"] == "BUY" else "⏳ CHỜ"
            rsi_str  = f"{st['rsi14']:.0f}" if st["rsi14"] is not None and math.isfinite(st["rsi14"]) else " N/A"
            mom_str  = f"{st['momentum']:.0f}" if math.isfinite(st["momentum"]) else " N/A"
            shp_str  = _fmt_f(st["sharpe_24m"])
            exc_str  = _fmt_pct(st["excess_ret_3m"])
            val_str  = f"{st['avg_val_ty']:.1f}" if math.isfinite(st["avg_val_ty"]) else "N/A"

            rows.append(
                f"{st['ticker']:<5}  {act_tag:<8}  {st['role']:<12}  "
                f"{rsi_str:>4}  {mom_str:>5}  {shp_str:>5}  {exc_str:>6}  {val_str:>10}"
            )

        table = "```\n" + HDR + "\n" + SEP + "\n" + "\n".join(rows) + "\n```"

        # ── Summary header ────────────────────────────────────────────
        total_buy  = len(buy_stocks)
        total_wait = len(wait_stocks)
        partial_note = f" _(kết quả tạm — quét được {processed}/{len(universe)} mã)_" if timed_out else ""
        summary = (
            f"**📊 Kết quả lọc VN200**{partial_note}\n"
            f"🛒 **{total_buy} mã MUA** · ⏳ **{total_wait} mã CHỜ** "
            f"(hiển thị top 5 mỗi nhóm theo giá trị GD)\n"
            f"_Tiêu chí: MUA hoặc (CHỜ + Close > MA50 + không có red flag) · GT TB ≥ 10 tỷ/ngày_"
        )

        await msg.edit(content=summary + "\n" + table)

    except Exception as e:
        try:
            await interaction.followup.send(f"❌ Lỗi Screener: {e}", ephemeral=False)
        except Exception:
            pass
