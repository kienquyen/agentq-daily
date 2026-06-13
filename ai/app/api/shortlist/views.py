"""
Shortlist API — Discord interaction handler

Handles the "AI Shortlist" menu button (item 6).

Flow:
  Click button 6
    → ShortlistPickerView: [📈 20d hôm nay] [🔄 Retrain] [📅 MTD 20d] [🔄 Cập nhật]
       ├─ 20d hôm nay  → score today with 20d model (default)
       ├─ Retrain      → train candidate model, then confirm deploy
       ├─ MTD 20d      → scan all trading days last 2 months, aggregate signals
       └─ Cập nhật     → run full pipeline (OHLCV → features → scoring)
           └─ Result view has [📅 Xem ngày khác] [📊 Kết quả T+20]
"""

from __future__ import annotations

import asyncio
import datetime
from pathlib import Path

import discord
from discord.ui import View, Button, Modal, TextInput


# ── Date picker modal ──────────────────────────────────────────────────────────

class DatePickerModal(Modal):
    def __init__(self) -> None:
        super().__init__(title="Chọn ngày xem shortlist")
        self.date_input = TextInput(
            label="Ngày (YYYY-MM-DD)",
            placeholder=f"Ví dụ: {datetime.date.today().strftime('%Y-%m-%d')}",
            max_length=10,
            min_length=10,
            required=True,
        )
        self.add_item(self.date_input)


# ── Picker view (shown on first click) ────────────────────────────────────────

class ShortlistPickerView(View):
    """
    First screen after clicking menu button 6.
    Only 20d model — 5d model removed.
    """

    def __init__(self) -> None:
        super().__init__(timeout=60)

    @discord.ui.button(
        label="📈 AI Shortlist 20 ngày (+5%)",
        style=discord.ButtonStyle.success,
        row=0,
    )
    async def btn_today_20d(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        today = _last_trading_day()
        feat_path = Path("data/features") / f"{today}.parquet"

        if not feat_path.exists():
            await interaction.response.edit_message(
                content=(
                    f"⏳ **Chưa có dữ liệu cho ngày {today}**\n\n"
                    "Features sẵn sàng sau khi thị trường đóng cửa (~15:30 ICT).\n"
                    "Bot tự động gửi shortlist vào **19:00 ICT** hàng ngày.\n\n"
                    "👇 Hoặc bạn có thể tự chạy pipeline ngay bây giờ:"
                ),
                view=PipelineRunView("20d"),
            )
            return

        if _is_feature_stale(today):
            await interaction.response.edit_message(
                content=(
                    f"⚠️ **Dữ liệu ngày {today} có thể chưa cập nhật**\n\n"
                    "Feature file được tính trước khi thị trường đóng cửa (15:30 ICT).\n"
                    "Kết quả hiện tại có thể giống ngày hôm trước.\n\n"
                    "👇 Nên cập nhật OHLCV mới nhất để có kết quả chính xác:"
                ),
                view=PipelineRunView("20d", show_stale_option=True),
            )
            return

        await interaction.response.defer(thinking=True, ephemeral=False)
        await _send_shortlist(interaction, today, horizon="20d", followup=True)

    @discord.ui.button(
        label="💎 AI Shortlist VALUE (v5, +10% vs Index)",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def btn_value_v5(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        import asyncio as _asyncio
        today = _last_trading_day()
        feat_path = Path("data/features") / f"{today}.parquet"
        if not feat_path.exists():
            await interaction.response.edit_message(
                content=(
                    f"⏳ **Chưa có dữ liệu cho ngày {today}**\n\n"
                    "Features sẵn sàng sau khi thị trường đóng cửa (~15:30 ICT).\n"
                    "👇 Hoặc tự chạy pipeline:"
                ),
                view=PipelineRunView("20d"),
            )
            return
        await interaction.response.defer(thinking=True, ephemeral=False)
        try:
            from pipeline.v5_shadow import build_v5_discord_message
            msg = await _asyncio.to_thread(build_v5_discord_message, today)
        except Exception as exc:
            await interaction.followup.send(f"⚠️ VALUE shortlist lỗi: `{exc}`")
            return
        from app.services.shortlist_job import _split_message
        for chunk in _split_message(msg, limit=1950):
            await interaction.followup.send(chunk)

    @discord.ui.button(
        label="🔄 Retrain Model",
        style=discord.ButtonStyle.danger,
        row=1,
    )
    async def btn_retrain(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        await interaction.response.send_message(
            "⚠️ **Xác nhận Retrain Model 20D?**\n\n"
            "Bot sẽ train lại LightGBM với toàn bộ dữ liệu mới nhất (~3 phút).\n"
            "• Model mới chỉ được deploy nếu AUC ≥ AUC hiện tại\n"
            "• Backup tự động trước khi deploy",
            view=RetrainConfirmView(),
            ephemeral=True,
        )

    @discord.ui.button(
        label="📅 Shortlist 2 tháng gần nhất (20d)",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def btn_mtd_20d(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        await _send_mtd_shortlist(interaction, followup=True)

    @discord.ui.button(
        label="🔧 Model Versions",
        style=discord.ButtonStyle.secondary,
        row=3,
    )
    async def btn_model_versions(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        await interaction.response.send_message(
            "⚙️ **Quản lý Model Versions**",
            view=ModelVersionView(),
            ephemeral=True,
        )

    @discord.ui.button(
        label="🔄 Cập nhật dữ liệu",
        style=discord.ButtonStyle.secondary,
        row=4,
    )
    async def btn_update_today(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        today = _last_trading_day()
        missing = _find_missing_month_dates(today)

        if missing:
            dates_str = ", ".join(d[5:] for d in missing)  # MM-DD format
            msg = (
                f"⏳ **Phát hiện {len(missing)} ngày thiếu dữ liệu trong tháng:**\n"
                f"`{dates_str}`\n\n"
                "🔄 Đang backfill OHLCV → features → scoring...\n"
                "*(Mỗi ngày ~30–60s. Kết quả gửi khi xong.)*"
            )
        else:
            msg = (
                f"⏳ **Đang cập nhật dữ liệu cho ngày {today}...**\n\n"
                "Pipeline: fetch OHLCV → tính features → scoring\n"
                "*(Khoảng 5–10 phút. Kết quả sẽ gửi khi xong.)*"
            )

        await interaction.response.edit_message(content=msg, view=None)
        await _send_backfill_and_score(interaction, today, missing)


# ── Result view (shown after shortlist rendered) ───────────────────────────────

class ShortlistResultView(View):
    """Shown below the shortlist result — lets user re-query another date or check T+20 results."""

    def __init__(self, horizon: str = "20d") -> None:
        super().__init__(timeout=120)
        self._horizon = horizon

    @discord.ui.button(
        label="📅 Xem ngày khác",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def btn_other_date(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        modal = DatePickerModal()
        horizon = self._horizon

        async def on_submit(i: discord.Interaction) -> None:
            date_str = modal.date_input.value.strip()
            await i.response.defer(thinking=True, ephemeral=False)
            await _send_shortlist(i, date_str, horizon=horizon, followup=True)

        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="📊 Kết quả thực tế (T+20)",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def btn_feedback_stats(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=False)
        try:
            stats   = await asyncio.to_thread(_get_feedback_stats)
            message = stats["discord_message"]
            from app.services.shortlist_job import _split_message
            for chunk in _split_message(message, limit=1950):
                await interaction.followup.send(chunk, ephemeral=False)
        except Exception as exc:
            await interaction.followup.send(
                f"⚠️ Lỗi khi tải kết quả thực tế:\n```{exc}```", ephemeral=True
            )


# ── Pipeline run view (shown when no feature file exists) ─────────────────────

class PipelineRunView(View):
    """
    Shown when no feature file exists, or when feature file is stale (built
    before market close). Lets user trigger the full pipeline manually.
    show_stale_option=True adds a "view current (possibly stale)" button.
    """

    def __init__(self, horizon: str = "20d", show_stale_option: bool = False) -> None:
        super().__init__(timeout=120)
        self._horizon = horizon
        # Dynamically add stale-view button only when needed
        if show_stale_option:
            btn = discord.ui.Button(
                label="📊 Xem kết quả hiện tại (có thể cũ)",
                style=discord.ButtonStyle.secondary,
                row=1,
            )
            btn.callback = self._view_stale
            self.add_item(btn)

    @discord.ui.button(
        label="🔄 Cập nhật & chạy pipeline hôm nay",
        style=discord.ButtonStyle.success,
        row=0,
    )
    async def btn_run_today(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        today = _last_trading_day()
        missing = _find_missing_month_dates(today)

        if missing:
            dates_str = ", ".join(d[5:] for d in missing)
            msg = (
                f"⏳ **Phát hiện {len(missing)} ngày thiếu trong tháng:**\n"
                f"`{dates_str}`\n\n"
                "🔄 Đang backfill + chạy pipeline hôm nay...\n"
                "*(Kết quả gửi khi xong.)*"
            )
        else:
            msg = (
                f"⏳ **Đang cập nhật dữ liệu cho ngày {today}...**\n\n"
                "Pipeline: fetch OHLCV → tính features → scoring\n"
                "*(Khoảng 5–10 phút. Kết quả sẽ gửi khi xong.)*"
            )
        await interaction.response.edit_message(content=msg, view=None)
        await _send_backfill_and_score(interaction, today, missing)

    @discord.ui.button(
        label="📅 Chạy pipeline ngày khác",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def btn_run_other_date(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        modal = DatePickerModal()
        modal.title = "Chọn ngày chạy pipeline"
        horizon = self._horizon

        async def on_submit(i: discord.Interaction) -> None:
            date_str = modal.date_input.value.strip()
            await i.response.defer(thinking=True, ephemeral=False)
            await _send_pipeline_shortlist(i, date_str, horizon=horizon, followup=True)

        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

    async def _view_stale(self, interaction: discord.Interaction) -> None:
        """View current (possibly stale) result without running pipeline."""
        today = _last_trading_day()
        await interaction.response.defer(thinking=True, ephemeral=False)
        await _send_shortlist(interaction, today, horizon=self._horizon, followup=True)


# ── Entry point ────────────────────────────────────────────────────────────────

async def open_shortlist_view(interaction: discord.Interaction) -> None:
    """
    Called from main menu button 6.
    Shows picker: 5d today / 20d today / MTD 20d / pick date.
    """
    await interaction.response.send_message(
        "🎯 **AI Shortlist** — Bạn muốn xem gì?",
        view=ShortlistPickerView(),
        ephemeral=True,
    )


# ── Core send logic ────────────────────────────────────────────────────────────

async def _send_shortlist(
    interaction: discord.Interaction,
    date_str: str,
    horizon: str = "5d",
    followup: bool = False,
) -> None:
    """Score and send shortlist for date_str. horizon = '5d' or '20d'."""
    # Validate date format
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        msg = f"❌ Ngày không hợp lệ: `{date_str}`. Vui lòng dùng định dạng YYYY-MM-DD."
        if followup:
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return

    # Check feature file exists
    feat_path = Path("data/features") / f"{date_str}.parquet"
    if not feat_path.exists():
        msg = (
            f"📭 **Chưa có dữ liệu features cho ngày {date_str}**\n\n"
            "👇 Bạn có thể tự chạy pipeline để tạo dữ liệu:"
        )
        if followup:
            await interaction.followup.send(msg, ephemeral=True, view=PipelineRunView(horizon))
        else:
            await interaction.response.send_message(msg, ephemeral=True, view=PipelineRunView(horizon))
        return

    # Run scoring in thread (CPU-bound, ~2–5s)
    try:
        result = await asyncio.to_thread(_score_no_update, date_str, horizon)
    except Exception as exc:
        msg = f"⚠️ Lỗi khi tạo shortlist cho `{date_str}` (horizon={horizon}):\n```{exc}```"
        if followup:
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return

    message = result.get("discord_message", "*(no message)*")

    from app.services.shortlist_job import _split_message
    chunks = _split_message(message, limit=1950)

    for idx, chunk in enumerate(chunks):
        view = ShortlistResultView(horizon) if idx == len(chunks) - 1 else None
        if followup:
            await interaction.followup.send(chunk, ephemeral=False, view=view)
        else:
            if idx == 0:
                await interaction.response.send_message(chunk, ephemeral=False, view=view)
            else:
                await interaction.followup.send(chunk, ephemeral=False, view=view)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _score_no_update(date_str: str, horizon: str = "5d") -> dict:
    """Synchronous: score using existing cached feature file. No OHLCV/feature update."""
    if horizon == "20d":
        from pipeline.phase6_shortlist_discord import get_shortlist_20d
        return get_shortlist_20d(date_str=date_str, update_ohlcv=False, update_features=False)
    else:
        from pipeline.phase6_shortlist_discord import get_shortlist
        return get_shortlist(date_str=date_str, update_ohlcv=False, update_features=False)


def _run_pipeline_and_score(date_str: str, horizon: str = "20d") -> dict:
    """Synchronous: run full pipeline (fetch OHLCV + features) then score. ~5–10 min."""
    if horizon == "20d":
        from pipeline.phase6_shortlist_discord import get_shortlist_20d
        return get_shortlist_20d(date_str=date_str, update_ohlcv=True, update_features=True)
    else:
        from pipeline.phase6_shortlist_discord import get_shortlist
        return get_shortlist(date_str=date_str, update_ohlcv=True, update_features=True)


async def _send_pipeline_shortlist(
    interaction: discord.Interaction,
    date_str: str,
    horizon: str = "20d",
    followup: bool = False,
) -> None:
    """Run full pipeline then send shortlist result. Always uses followup after pipeline."""
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await interaction.followup.send(
            f"❌ Ngày không hợp lệ: `{date_str}`. Dùng định dạng YYYY-MM-DD.",
            ephemeral=True,
        )
        return

    try:
        result = await asyncio.to_thread(_run_pipeline_and_score, date_str, horizon)
    except Exception as exc:
        await interaction.followup.send(
            f"⚠️ Pipeline thất bại cho `{date_str}`:\n```{exc}```", ephemeral=True
        )
        return

    message = result.get("discord_message", "*(no message)*")
    from app.services.shortlist_job import _split_message
    chunks = _split_message(message, limit=1950)
    for idx, chunk in enumerate(chunks):
        view = ShortlistResultView(horizon) if idx == len(chunks) - 1 else None
        await interaction.followup.send(chunk, ephemeral=False, view=view)


def _last_trading_day() -> str:
    """Return today or most-recent weekday as YYYY-MM-DD."""
    d = datetime.date.today()
    while d.weekday() >= 5:
        d -= datetime.timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _get_vnindex_trading_days() -> set[str]:
    """
    Đọc VNINDEX.parquet để lấy tập hợp ngày trading thực tế (YYYY-MM-DD).
    Dùng làm oracle: nếu sàn đóng cửa (lễ, sự kiện bất thường) thì VNINDEX
    sẽ không có row cho ngày đó → hàm này trả về set rỗng nếu file không tồn tại.
    """
    import pandas as _pd
    vnindex_path = Path("data/ohlcv/VNINDEX.parquet")
    if not vnindex_path.exists():
        return set()
    try:
        df = _pd.read_parquet(vnindex_path, columns=["time"])
        df["time"] = _pd.to_datetime(df["time"])
        return set(df["time"].dt.strftime("%Y-%m-%d").tolist())
    except Exception:
        return set()


def _find_missing_month_dates(as_of: str) -> list[str]:
    """
    Tìm tất cả ngày trading trong tháng hiện tại (từ ngày 1 đến as_of)
    mà chưa có feature file.

    - Dùng VNINDEX.parquet làm oracle ngày giao dịch thực tế (bao gồm xử lý
      cả ngày lễ Việt Nam, ngày sàn đóng cửa bất thường).
    - Fallback về weekday < 5 nếu VNINDEX.parquet chưa có.

    Trả về list YYYY-MM-DD đã sort tăng dần.
    """
    feat_dir     = Path("data/features")
    end          = datetime.date.fromisoformat(as_of)
    start        = end.replace(day=1)
    trading_days = _get_vnindex_trading_days()
    use_oracle   = len(trading_days) > 0

    d       = start
    missing = []
    while d <= end:
        ds = d.strftime("%Y-%m-%d")
        is_trading = (ds in trading_days) if use_oracle else (d.weekday() < 5)
        if is_trading and not (feat_dir / f"{ds}.parquet").exists():
            missing.append(ds)
        d += datetime.timedelta(days=1)
    return missing


def _backfill_features_for_date(date_str: str) -> str:
    """
    Synchronous: chạy phase2 feature pipeline cho một ngày cụ thể.
    OHLCV đã có sẵn (phase1 đã chạy trước hoặc data đã tồn tại).
    Trả về thông báo ngắn về kết quả.
    """
    try:
        from pipeline.phase2_feature_pipeline import run as phase2_run
        df = phase2_run(target_date=date_str, save=True)
        passed = int(df["hardcheck_pass"].sum()) if "hardcheck_pass" in df.columns else len(df)
        return f"✅ {date_str}: {passed} mã qua hardcheck"
    except Exception as exc:
        return f"⚠️ {date_str}: lỗi features — {exc}"


def _run_full_pipeline_for_date(date_str: str) -> str:
    """
    Synchronous: chạy phase1 OHLCV update (incremental) + phase2 features cho một ngày.
    Trả về thông báo ngắn.
    """
    try:
        from pipeline.phase1a_ohlcv_store import run as phase1_run
        # phase1a.run() tự lấy end = ngày hôm nay (UTC), không nhận tham số 'end'
        phase1_run(mode="incremental")
    except Exception as exc:
        return f"⚠️ {date_str}: lỗi OHLCV — {exc}"
    return _backfill_features_for_date(date_str)


async def _send_backfill_and_score(
    interaction: discord.Interaction,
    today: str,
    missing_dates: list[str],
) -> None:
    """
    1. Backfill feature files cho tất cả ngày thiếu trong tháng.
    2. Chạy full pipeline (OHLCV + features) cho ngày today.
    3. Gửi kết quả shortlist hôm nay.
    """
    results = []

    # ── Backfill missing days (features only, OHLCV assumed present) ──────────
    for ds in missing_dates:
        if ds == today:
            continue  # today handled below
        feat_path = Path("data/features") / f"{ds}.parquet"
        if feat_path.exists():
            continue  # already done (concurrent race)
        msg = await asyncio.to_thread(_backfill_features_for_date, ds)
        results.append(msg)

    # ── Run full pipeline for today (OHLCV + features) ────────────────────────
    try:
        today_msg = await asyncio.to_thread(_run_full_pipeline_for_date, today)
        results.append(today_msg)
    except Exception as exc:
        results.append(f"⚠️ {today}: pipeline lỗi — {exc}")

    # ── Gửi tóm tắt backfill ─────────────────────────────────────────────────
    if results:
        summary = "📋 **Kết quả backfill:**\n" + "\n".join(f"  {r}" for r in results)
        await interaction.followup.send(summary, ephemeral=False)

    # ── Gửi shortlist hôm nay ────────────────────────────────────────────────
    await _send_pipeline_shortlist(interaction, today, horizon="20d")


def _is_feature_stale(date_str: str) -> bool:
    """
    Returns True if the feature file for date_str was built BEFORE today's
    market close (15:30 ICT = 08:30 UTC) and date_str == today.

    A stale file means OHLCV data for today hasn't been incorporated yet,
    so the shortlist result will be identical to the previous trading day.
    Historical dates never go stale.
    """
    import os

    today = datetime.date.today().strftime("%Y-%m-%d")
    if date_str != today:
        return False  # Historical dates don't go stale

    feat_path = Path("data/features") / f"{date_str}.parquet"
    if not feat_path.exists():
        return False  # Missing ≠ stale

    # Market closes 15:30 ICT = 08:30 UTC
    market_close_utc = datetime.datetime.combine(
        datetime.date.today(), datetime.time(8, 30),
        tzinfo=datetime.timezone.utc,
    )
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # Before market close → can't have fresh data yet, not considered stale
    if now_utc < market_close_utc:
        return False

    # After market close → stale if file was last modified before close time
    feat_mtime = datetime.datetime.fromtimestamp(
        os.path.getmtime(feat_path), tz=datetime.timezone.utc
    )
    return feat_mtime < market_close_utc


# ── MTD (Month-to-Date) shortlist ─────────────────────────────────────────────

def _trading_days_last_2months() -> list[str]:
    """
    Return all actual trading days from 2 months ago (1st of that month) up to today.

    - Dùng VNINDEX.parquet làm oracle (bao gồm xử lý ngày lễ Việt Nam).
    - Fallback về weekday < 5 nếu VNINDEX.parquet chưa có.
    """
    today = datetime.date.today()
    # Go back 2 months
    month = today.month - 2
    year  = today.year
    if month <= 0:
        month += 12
        year  -= 1
    first        = today.replace(year=year, month=month, day=1)
    trading_days = _get_vnindex_trading_days()
    use_oracle   = len(trading_days) > 0

    days = []
    d = first
    while d <= today:
        ds = d.strftime("%Y-%m-%d")
        if (ds in trading_days) if use_oracle else (d.weekday() < 5):
            days.append(ds)
        d += datetime.timedelta(days=1)
    return days


def _score_mtd_20d_sync() -> dict:
    """
    Scan all trading days this month, collect 20d signals from cached feature files.
    Returns aggregated result: each symbol ranked by frequency + best_prob.
    Only processes days where data/features/<date>.parquet already exists.
    """
    from pathlib import Path
    from collections import defaultdict

    days = _trading_days_last_2months()
    feat_dir = Path("data/features")

    # symbol → {dates, probs, scores, entry_prices}
    seen: dict[str, dict] = defaultdict(lambda: {
        "dates": [], "probs": [], "scores": [], "entry_prices": [],
    })
    days_scanned = 0
    days_with_data = 0

    for date_str in days:
        days_scanned += 1
        feat_path = feat_dir / f"{date_str}.parquet"
        if not feat_path.exists():
            continue
        days_with_data += 1
        try:
            result = _score_no_update(date_str, horizon="20d")
            for sig in result.get("signals", []):
                sym = sig["symbol"]
                seen[sym]["dates"].append(date_str)
                seen[sym]["probs"].append(sig["prob"])
                seen[sym]["scores"].append(sig["score"])
                seen[sym]["entry_prices"].append(sig.get("close_price") or 0)
        except Exception:
            pass

    # Build ranked list: sort by (appearances DESC, best_prob DESC)
    rows = []
    for sym, v in seen.items():
        last_idx = v["dates"].index(max(v["dates"]))  # index of most recent signal
        rows.append({
            "symbol":       sym,
            "appearances":  len(v["dates"]),
            "best_prob":    round(max(v["probs"]), 4),
            "avg_prob":     round(sum(v["probs"]) / len(v["probs"]), 4),
            "last_date":    max(v["dates"]),
            "entry_price":  v["entry_prices"][last_idx],  # close on last signal date
            "dates":        sorted(v["dates"]),
        })
    rows.sort(key=lambda r: (r["last_date"], r["best_prob"]), reverse=True)

    return {
        "month":          datetime.date.today().strftime("%Y-%m"),
        "days_scanned":   days_scanned,
        "days_with_data": days_with_data,
        "symbols":        rows,
    }


def _format_mtd_message(data: dict) -> str:
    """Format MTD scan result for Discord — compact mobile-friendly table."""
    from pipeline.phase6_shortlist_discord import _get_latest_close, _add_n_trading_days

    month          = data["month"]
    days_scanned   = data["days_scanned"]
    days_with_data = data["days_with_data"]
    rows           = data["symbols"]

    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📅  **AI SHORTLIST 2 THÁNG GẦN NHẤT (Model 20D)**")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(
        f"📊 **{days_with_data}/{days_scanned}** ngày có data  |  "
        f"**{len(rows)}** mã tín hiệu"
    )
    lines.append("")

    if not rows:
        lines.append("🔕 **Không có mã nào đạt điều kiện trong tháng này.**")
        lines.append("> Dữ liệu features chưa được tính cho tháng hiện tại.")
        lines.append("")
        lines.append("⚠️ *Tín hiệu tham khảo từ mô hình ML. Không phải khuyến nghị đầu tư.*")
        return "\n".join(lines)

    # ── Compact table ──────────────────────────────────────────────────────────
    # Columns: Mã | Lần | Vào | Mua(k) | +/- | Thoát | Status
    # Status: Open=đang mở, Closed-Win=đóng lãi, Closed-Lost=đóng lỗ, !SL=cắt lỗ -10%
    from pipeline.phase6_shortlist_discord import _get_signal_statuses, _get_latest_close

    lines.append("```")
    lines.append(f"{'Mã':<5} {'Lần':>3} {'Vào':>5} {'Mua(k)':>6} {'+/-':>6}  {'Thoát':>5}  {'Status':<11}")
    lines.append(f"{'─'*5} {'─'*3} {'─'*5} {'─'*6} {'─'*6}  {'─'*5}  {'─'*11}")
    for r in rows[:20]:
        sym       = r["symbol"]
        n_appear  = r["appearances"]
        entry_vnd = r.get("entry_price") or 0
        entry_k   = entry_vnd / 1000 if entry_vnd else None
        price_str = f"{entry_k:,.1f}" if entry_k else "  —"
        entry_short = datetime.datetime.strptime(r["last_date"], "%Y-%m-%d").strftime("%d/%m")

        # Look up status from feedback log for the last signal date
        st_map   = _get_signal_statuses(r["last_date"], [sym])
        st       = st_map.get(sym, {"status": "new", "actual_return": None, "exit_date": None})
        st_key   = st["status"]
        act_ret  = st.get("actual_return")
        exit_dt  = st.get("exit_date") or "   —"

        if st_key in ("t20", "stop_loss"):
            perf_str = f"{act_ret:+.1f}%" if act_ret is not None else "   —  "
            if st_key == "stop_loss":
                status_str = "!SL"
            else:
                is_win = st.get("is_win")
                status_str = "Closed-Win" if is_win else "Closed-Lost"
        else:
            cur_vnd = _get_latest_close(sym)
            if entry_vnd and cur_vnd:
                perf     = (cur_vnd - entry_vnd) / entry_vnd * 100
                perf_str = f"{perf:+.1f}%"
            else:
                perf_str = "   —  "
            status_str = "Open"
            exit_dt    = "   —"

        lines.append(
            f"{sym:<5} {n_appear:>3} {entry_short:>5} {price_str:>6} {perf_str:>6}  {exit_dt:>5}  {status_str:<11}"
        )
    lines.append("```")

    if len(rows) > 20:
        lines.append(f"*… {len(rows) - 20} mã khác (top 20)*")

    # ── Summary stats: Win/Loss/Open counts + avg returns ─────────────────────
    wins, losses, sl_hits, opens = [], [], [], []
    for r in rows:
        sym      = r["symbol"]
        st_map   = _get_signal_statuses(r["last_date"], [sym])
        st       = st_map.get(sym, {"status": "new", "actual_return": None})
        st_key   = st["status"]
        act_ret  = st.get("actual_return")
        is_win   = st.get("is_win")
        if st_key == "stop_loss":
            sl_hits.append(act_ret if act_ret is not None else -10.0)
        elif st_key == "t20":
            if is_win:
                wins.append(act_ret if act_ret is not None else 0.0)
            else:
                losses.append(act_ret if act_ret is not None else 0.0)
        else:
            opens.append(r)

    n_closed = len(wins) + len(losses) + len(sl_hits)
    n_total  = n_closed + len(opens)
    wr_pct   = len(wins) / n_closed * 100 if n_closed > 0 else 0.0
    avg_win  = sum(wins)  / len(wins)  if wins  else 0.0
    avg_loss = sum(losses + sl_hits) / (len(losses) + len(sl_hits)) if (losses or sl_hits) else 0.0

    lines.append("")
    lines.append("```")
    lines.append(f"📊 TỔNG KẾT  ({n_closed} đã đóng / {len(opens)} đang mở)")
    lines.append(f"{'─'*34}")
    lines.append(f"  Win rate  : {len(wins):>2} Closed-Win  = {wr_pct:>5.1f}%")
    lines.append(f"  Closed-Win: avg {avg_win:>+6.1f}%")
    lines.append(f"  Closed-Lost + !SL: {len(losses)} + {len(sl_hits)} = avg {avg_loss:>+6.1f}%")
    lines.append(f"  Open      : {len(opens):>2} lệnh đang mở")
    lines.append("```")

    lines.append("")
    lines.append(
        "💡 *Lần=số ngày xuất hiện · Vào=ngày mua gần nhất · Mua(k)=giá vào · "
        "+/-=so entry(Open)/thực tế(Đóng) · Thoát=ngày đóng lệnh*"
    )
    lines.append(
        "📊 *Closed-Win=đóng lãi>0% · Closed-Lost=đóng lỗ≤0% · !SL=cắt lỗ -10% · Open=đang mở*"
    )
    lines.append("🎯 *Mã lặp nhiều lần = model nhất quán xác nhận.*")
    lines.append("")
    lines.append("⚠️ *Tín hiệu tham khảo từ mô hình ML. Không phải khuyến nghị đầu tư.*")
    return "\n".join(lines)


# ── Model Version Manager ──────────────────────────────────────────────────────

class ModelVersionView(View):
    """
    Quản lý model versions: xem status, switch active, bật/tắt shadow.
    Truy cập từ ShortlistPickerView button 🔧.
    """

    def __init__(self) -> None:
        super().__init__(timeout=120)

    @discord.ui.button(label="📋 Trạng thái versions", style=discord.ButtonStyle.primary, row=0)
    async def btn_status(self, interaction: discord.Interaction, button: Button) -> None:
        from pipeline.model_registry import registry
        s = registry.status()
        lines = ["```", f"🎯 Active : {s['active']}", f"👁️ Shadow : {s.get('shadow') or 'OFF'}", ""]
        for v, info in s.get("versions", {}).items():
            tag = " ← active" if info["is_active"] else (" ← shadow" if info["is_shadow"] else "")
            auc_str = f"AUC={info['auc']:.4f}" if info.get("auc") else "AUC=?"
            lines.append(f"  {v}{tag}")
            lines.append(f"    {auc_str}  created={info.get('created','?')}")
            lines.append(f"    {info.get('description','')[:60]}")
            lines.append("")
        lines.append("```")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @discord.ui.button(label="🔀 Switch Version", style=discord.ButtonStyle.secondary, row=0)
    async def btn_switch(self, interaction: discord.Interaction, button: Button) -> None:
        modal = _VersionInputModal("Switch Active Version", "Version name (e.g. v3b)")

        async def on_submit(i: discord.Interaction) -> None:
            ver = modal.value_input.value.strip()
            from pipeline.model_registry import registry, version_exists
            if not version_exists(ver):
                await i.response.send_message(
                    f"❌ Version `{ver}` không tồn tại trong `data/models/`.", ephemeral=True
                )
                return
            old = registry.active()
            registry.set_active(ver)
            await i.response.send_message(
                f"✅ Đã switch: **{old}** → **{ver}**\n"
                f"_(Áp dụng ngay, không cần restart bot)_", ephemeral=True
            )

        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="👁️ Shadow: ON/OFF", style=discord.ButtonStyle.secondary, row=1)
    async def btn_shadow(self, interaction: discord.Interaction, button: Button) -> None:
        from pipeline.model_registry import registry
        current = registry.shadow()
        if current:
            # Tắt shadow
            registry.set_shadow("")
            await interaction.response.send_message(
                f"🔕 Shadow mode **OFF** (đã tắt `{current}`)", ephemeral=True
            )
        else:
            # Bật shadow — hỏi version
            modal = _VersionInputModal("Bật Shadow Mode", "Shadow version (e.g. v3b)")

            async def on_submit(i: discord.Interaction) -> None:
                ver = modal.value_input.value.strip()
                from pipeline.model_registry import version_exists
                if not version_exists(ver):
                    await i.response.send_message(
                        f"❌ Version `{ver}` chưa có model file.", ephemeral=True
                    )
                    return
                registry.set_shadow(ver)
                await i.response.send_message(
                    f"👁️ Shadow mode **ON** → `{ver}`\n"
                    f"Kết quả lưu tại `data/shadow_signals/{ver}/`", ephemeral=True
                )

            modal.on_submit = on_submit
            await interaction.response.send_modal(modal)

    @discord.ui.button(label="📊 So sánh Versions", style=discord.ButtonStyle.secondary, row=1)
    async def btn_compare(self, interaction: discord.Interaction, button: Button) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            msg = await asyncio.to_thread(_compare_versions_stats)
            await interaction.followup.send(msg, ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(f"⚠️ Lỗi: ```{exc}```", ephemeral=True)

    @discord.ui.button(label="🚀 Promote → Production", style=discord.ButtonStyle.danger, row=2)
    async def btn_promote(self, interaction: discord.Interaction, button: Button) -> None:
        modal = _VersionInputModal("Promote Candidate", "Version cần promote (e.g. v3b)")

        async def on_submit(i: discord.Interaction) -> None:
            ver = modal.value_input.value.strip()
            from pipeline.model_registry import version_exists, promote_to_production
            if not version_exists(ver):
                await i.response.send_message(f"❌ Version `{ver}` không có model file.", ephemeral=True)
                return
            await i.response.defer(ephemeral=True)
            try:
                archive = await asyncio.to_thread(promote_to_production, ver)
                await i.followup.send(
                    f"✅ **{ver}** đã promote → production (`v3a`)\n"
                    f"📦 Backup cũ: `data/models/archive/{archive}`", ephemeral=True
                )
            except Exception as exc:
                await i.followup.send(f"❌ Promote thất bại:\n```{exc}```", ephemeral=True)

        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)


class _VersionInputModal(discord.ui.Modal):
    """Generic 1-field modal để nhập version name."""
    def __init__(self, title: str, placeholder: str) -> None:
        super().__init__(title=title)
        self.value_input = discord.ui.TextInput(
            label="Version",
            placeholder=placeholder,
            max_length=20,
            min_length=2,
            required=True,
        )
        self.add_item(self.value_input)


def _compare_versions_stats() -> str:
    """So sánh win rate active vs shadow từ shadow_signals logs."""
    import json as _json
    from pathlib import Path as _Path

    shadow_base = _Path("data/shadow_signals")
    if not shadow_base.exists():
        return "📭 Chưa có dữ liệu shadow. Bật Shadow mode và chờ vài ngày."

    versions = [d.name for d in shadow_base.iterdir() if d.is_dir()]
    if not versions:
        return "📭 Chưa có dữ liệu shadow."

    lines = ["```", "📊 SO SÁNH SHADOW SIGNALS", "─" * 36]
    for ver in sorted(versions):
        files = sorted((shadow_base / ver).glob("*.json"))
        total_signals = sum(
            len(_json.loads(f.read_text()).get("signals", []))
            for f in files
        )
        lines.append(f"  {ver}: {len(files)} ngày  |  {total_signals} signals tổng")
    lines += [
        "",
        "💡 Win rate sẽ có sau T+20 từ ngày signal đầu tiên.",
        "```"
    ]
    return "\n".join(lines)


# ── Retrain views (2-step: train → confirm deploy) ────────────────────────────

class RetrainConfirmView(View):
    """Step 1: Confirm to START training (not deploy yet)."""

    def __init__(self) -> None:
        super().__init__(timeout=60)

    @discord.ui.button(label="✅ Bắt đầu Train", style=discord.ButtonStyle.danger, row=0)
    async def btn_confirm(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        await interaction.response.edit_message(
            content=(
                "⏳ **Đang train candidate model...**\n"
                "Bot vẫn hoạt động bình thường. Kết quả sẽ hiển thị sau ~3 phút."
            ),
            view=None,
        )
        try:
            report = await asyncio.to_thread(_run_train_candidate)
            msg    = report.get("discord_message", "*(no message)*")
            from app.services.shortlist_job import _split_message
            # Gửi báo cáo + nút deploy
            chunks = _split_message(msg, limit=1950)
            for i, chunk in enumerate(chunks):
                view = RetrainDeployView(report) if i == len(chunks) - 1 else None
                await interaction.followup.send(chunk, ephemeral=True, view=view)
        except Exception as exc:
            await interaction.followup.send(
                f"❌ Retrain crashed:\n```{exc}```", ephemeral=True
            )

    @discord.ui.button(label="❌ Huỷ", style=discord.ButtonStyle.secondary, row=0)
    async def btn_cancel(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        await interaction.response.edit_message(content="🔕 Đã huỷ retrain.", view=None)


class RetrainDeployView(View):
    """Step 2: After training, user chooses Deploy or Keep old model."""

    def __init__(self, report: dict) -> None:
        super().__init__(timeout=300)   # 5 phút để quyết định
        self._report = report

    @discord.ui.button(label="🚀 Deploy model mới", style=discord.ButtonStyle.success, row=0)
    async def btn_deploy(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        result = await asyncio.to_thread(_do_deploy)
        new_auc = self._report.get("new_auc", 0.0)
        old_auc = self._report.get("old_auc", 0.0)
        if result["success"]:
            await interaction.followup.send(
                f"✅ **Model mới đã được deploy!**\n"
                f"Test AUC: `{old_auc:.4f}` → `{new_auc:.4f}` "
                f"(`{new_auc - old_auc:+.4f}`)\n"
                f"Backup lưu tại `lgbm_model_20d_backup.pkl`",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(result["message"], ephemeral=True)
        self.stop()

    @discord.ui.button(label="🗑️ Giữ model cũ", style=discord.ButtonStyle.secondary, row=0)
    async def btn_discard(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        result = await asyncio.to_thread(_do_discard)
        await interaction.followup.send(
            f"🔒 **Model cũ được giữ nguyên.** Candidate đã xoá.\n"
            f"_(AUC production: `{self._report.get('old_auc', 0.0):.4f}`)_",
            ephemeral=True,
        )
        self.stop()


def _run_train_candidate() -> dict:
    """Synchronous: train candidate model. Runs in thread."""
    from pipeline.retrain_pipeline import train_candidate, format_train_report
    report = train_candidate()
    report["discord_message"] = format_train_report(report)
    return report


def _do_deploy() -> dict:
    """Synchronous: deploy candidate to production. Runs in thread."""
    from pipeline.retrain_pipeline import deploy_candidate
    return deploy_candidate()


def _do_discard() -> dict:
    """Synchronous: discard candidate. Runs in thread."""
    from pipeline.retrain_pipeline import discard_candidate
    return discard_candidate()


def _get_feedback_stats() -> dict:
    """Synchronous: load and format feedback stats. Runs in thread."""
    from pipeline.feedback_tracker import get_stats, format_stats_discord
    stats = get_stats()
    stats["discord_message"] = format_stats_discord(stats)
    return stats


async def _send_mtd_shortlist(
    interaction: discord.Interaction,
    followup: bool = False,
) -> None:
    """Run MTD scan in thread and send result to Discord."""
    try:
        data = await asyncio.to_thread(_score_mtd_20d_sync)
    except Exception as exc:
        msg = f"⚠️ Lỗi khi quét shortlist MTD:\n```{exc}```"
        if followup:
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return

    message = _format_mtd_message(data)

    from app.services.shortlist_job import _split_message
    chunks = _split_message(message, limit=1950)

    for idx, chunk in enumerate(chunks):
        view = ShortlistResultView("20d") if idx == len(chunks) - 1 else None
        if followup:
            await interaction.followup.send(chunk, ephemeral=False, view=view)
        else:
            if idx == 0:
                await interaction.response.send_message(chunk, ephemeral=False, view=view)
            else:
                await interaction.followup.send(chunk, ephemeral=False, view=view)
