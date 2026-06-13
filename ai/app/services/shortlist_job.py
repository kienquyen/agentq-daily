"""
Shortlist Job — Discord Cog

Sends the daily ML buy-shortlist to a configured Discord channel
every trading day at 19:00 ICT (12:00 UTC).

Configuration (via .env):
    SHORTLIST_CHANNEL_ID=<discord_channel_id>
    SHORTLIST_ENABLED=1          # set to 0 to disable
"""

import asyncio
import datetime
import logging
import os

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

# ── Runtime settings (can be toggled via bot commands) ────────────────────────
SHORTLIST_SETTINGS: dict = {
    "is_active":  bool(int(os.getenv("SHORTLIST_ENABLED", "1"))),
    "channel_id": int(os.getenv("SHORTLIST_CHANNEL_ID", "0")) or None,
}

# 19:00 ICT = UTC+7 → 12:00 UTC
_FIRE_TIME = datetime.time(hour=12, minute=0, tzinfo=datetime.timezone.utc)


class ShortlistCog(commands.Cog):
    """Daily 19:00 ICT shortlist notifier."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.daily_shortlist_loop.start()

    def cog_unload(self) -> None:
        self.daily_shortlist_loop.cancel()

    # ── Scheduled task ────────────────────────────────────────────────────────

    @tasks.loop(time=_FIRE_TIME)
    async def daily_shortlist_loop(self) -> None:
        if not SHORTLIST_SETTINGS.get("is_active"):
            log.debug("[shortlist_job] disabled — skipping.")
            return

        channel_id = SHORTLIST_SETTINGS.get("channel_id")
        if not channel_id:
            log.warning(
                "[shortlist_job] SHORTLIST_CHANNEL_ID not set — skipping. "
                "Add it to .env or set SHORTLIST_SETTINGS['channel_id']."
            )
            return

        # Skip weekends (ICT date at fire time = UTC+12h offset already passed)
        today = datetime.date.today()
        if today.weekday() >= 5:   # 5=Sat, 6=Sun
            log.info("[shortlist_job] Weekend — no shortlist today.")
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            log.error("[shortlist_job] Channel %s not found.", channel_id)
            return

        date_str = today.strftime("%Y-%m-%d")

        # Collect matured signals (T+20 outcomes) before sending new shortlist
        try:
            from pipeline.feedback_tracker import collect_matured
            n = await asyncio.to_thread(collect_matured, date_str)
            if n:
                log.info("[shortlist_job] Feedback: resolved %d matured signal(s).", n)
        except Exception as exc:
            log.warning("[shortlist_job] Feedback collect failed (non-fatal): %s", exc)

        await self._send_shortlist(channel, date_str)

    @daily_shortlist_loop.before_loop
    async def before_loop(self) -> None:
        await self.bot.wait_until_ready()

    # ── Core send logic ───────────────────────────────────────────────────────

    async def _send_shortlist(
        self,
        channel: discord.TextChannel,
        date_str: str,
    ) -> None:
        """Run the full pipeline (blocking) in a thread, then send to Discord."""
        log.info("[shortlist_job] Generating shortlist for %s …", date_str)

        try:
            result = await asyncio.to_thread(
                _run_phase6, date_str
            )
        except Exception as exc:
            log.error("[shortlist_job] phase6 crashed: %s", exc, exc_info=True)
            await channel.send(
                f"⚠️ **Shortlist job lỗi** ({date_str})\n```{exc}```"
            )
            return

        message = result.get("discord_message", "*(no message)*")

        # Discord limit is 2000 chars per message — split if needed
        chunks = _split_message(message, limit=1950)
        for chunk in chunks:
            await channel.send(chunk)

        n = len(result.get("signals", []))
        log.info("[shortlist_job] Sent %d signal(s) to channel %s.", n, channel.id)

    # ── Manual trigger (slash command or prefix) ──────────────────────────────

    @commands.command(name="shortlist")
    @commands.has_permissions(manage_messages=True)
    async def shortlist_cmd(
        self,
        ctx: commands.Context,
        date: str = "",
    ) -> None:
        """
        Manually trigger the shortlist for today or a specific date.
        Usage: !shortlist              → today
               !shortlist 2026-04-07  → specific date
        """
        date_str = date.strip() or datetime.date.today().strftime("%Y-%m-%d")
        await ctx.send(f"⏳ Đang tạo shortlist cho `{date_str}` …")
        await self._send_shortlist(ctx.channel, date_str)

    # ── v5 VALUE shortlist (separate model — distinct branding) ───────────────

    @commands.command(name="shortlist_value", aliases=["value", "v5"])
    @commands.has_permissions(manage_messages=True)
    async def shortlist_value_cmd(
        self,
        ctx: commands.Context,
        date: str = "",
    ) -> None:
        """
        AI VALUE shortlist (v5 model: outperform VNINDEX +10%/1mo, SL -7%).
        Riêng biệt với !shortlist (momentum v3b).
        Usage: !shortlist_value          → hôm nay
               !value 2026-04-15         → ngày cụ thể
        """
        date_str = date.strip() or datetime.date.today().strftime("%Y-%m-%d")
        await ctx.send(f"⏳ Đang tạo **VALUE shortlist (v5)** cho `{date_str}` …")
        try:
            msg = await asyncio.to_thread(_run_v5_shortlist, date_str)
        except Exception as exc:
            log.error("[v5_shortlist] crashed: %s", exc, exc_info=True)
            await ctx.send(f"⚠️ **VALUE shortlist lỗi** ({date_str})\n```{exc}```")
            return
        for chunk in _split_message(msg, limit=1950):
            await ctx.send(chunk)

    # ── Admin toggle ─────────────────────────────────────────────────────────

    @commands.command(name="shortlist_toggle")
    @commands.has_permissions(administrator=True)
    async def toggle_cmd(self, ctx: commands.Context) -> None:
        """Toggle the daily shortlist job on/off."""
        SHORTLIST_SETTINGS["is_active"] = not SHORTLIST_SETTINGS["is_active"]
        state = "✅ BẬT" if SHORTLIST_SETTINGS["is_active"] else "🔕 TẮT"
        await ctx.send(f"Shortlist job: **{state}**")

    @commands.command(name="shortlist_setchannel")
    @commands.has_permissions(administrator=True)
    async def set_channel_cmd(self, ctx: commands.Context) -> None:
        """Set the current channel as the shortlist destination."""
        SHORTLIST_SETTINGS["channel_id"] = ctx.channel.id
        await ctx.send(
            f"✅ Shortlist sẽ được gửi vào kênh **#{ctx.channel.name}** lúc 19:00 ICT."
        )

    @commands.command(name="shortlist_status")
    async def status_cmd(self, ctx: commands.Context) -> None:
        """Show current shortlist job status."""
        ch_id  = SHORTLIST_SETTINGS.get("channel_id")
        active = SHORTLIST_SETTINGS.get("is_active")
        ch_str = f"<#{ch_id}>" if ch_id else "*(chưa cấu hình)*"
        state  = "✅ Đang chạy" if active else "🔕 Tắt"
        await ctx.send(
            f"**Shortlist Job Status**\n"
            f"Trạng thái: {state}\n"
            f"Kênh:       {ch_str}\n"
            f"Giờ gửi:    19:00 ICT (12:00 UTC) — thứ 2 đến thứ 6"
        )


# ── helpers ────────────────────────────────────────────────────────────────────

def _run_phase6(date_str: str) -> dict:
    """
    Synchronous wrapper — runs 20-day model by default for the daily cron job.
    Runs in a thread via asyncio.to_thread.
    """
    from pipeline.phase6_shortlist_discord import get_shortlist_20d
    return get_shortlist_20d(
        date_str=date_str,
        update_ohlcv=True,
        update_features=True,
    )


def _run_v5_shortlist(date_str: str) -> str:
    """Synchronous wrapper — v5 VALUE shortlist (refresh data first)."""
    from pipeline.phase6_shortlist_discord import _update_ohlcv, _update_features
    try:
        _update_ohlcv(date_str)
        _update_features(date_str)
    except Exception as exc:
        log.warning("[v5_shortlist] data refresh failed (dùng file có sẵn): %s", exc)
    from pipeline.v5_shadow import build_v5_discord_message
    return build_v5_discord_message(date_str)


def _split_message(text: str, limit: int = 1950) -> list[str]:
    """Split a long message into ≤limit-char chunks, breaking at newlines."""
    if len(text) <= limit:
        return [text]

    chunks, current = [], []
    current_len = 0
    for line in text.splitlines(keepends=True):
        if current_len + len(line) > limit and current:
            chunks.append("".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line)
    if current:
        chunks.append("".join(current))
    return chunks


# ── Cog setup ─────────────────────────────────────────────────────────────────

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ShortlistCog(bot))
