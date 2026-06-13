import datetime
import asyncio
import os
from discord.ext import commands, tasks

from features.daily_recap.data_fetcher import fetch_all
from features.daily_recap.ai_generator import AICapacityPlanner
from features.daily_recap.formatter import format_daily_recap, generate_recap_image
from app.api.daily_recap.views import DAILY_RECAP_SETTINGS
import discord

# Define UTC time for 7:00 AM ICT (ICT is UTC+7, so 00:00 UTC)
ict_7_am_utc = datetime.time(hour=0, minute=0, tzinfo=datetime.timezone.utc)


class DailyRecapCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_report_loop.start()

    def cog_unload(self):
        self.daily_report_loop.cancel()

    @tasks.loop(time=ict_7_am_utc)
    async def daily_report_loop(self):
        if not DAILY_RECAP_SETTINGS.get("is_active"):
            return

        channel_id = DAILY_RECAP_SETTINGS.get("channel_id")
        if not channel_id:
            return

        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        # Skip Sunday (weekday=6) and Monday (weekday=0)
        # because previous trading day is Friday, not a recent report
        if today.weekday() in (0, 6):
            return

        channel = self.bot.get_channel(channel_id)
        if channel:
            try:
                target_date = yesterday.strftime("%Y-%m-%d")

                # 1. Fetch data for previous trading day
                data = await fetch_all(target_date=target_date)

                # 2. Generate AI insights
                planner = AICapacityPlanner()
                default_user_id = None
                try:
                    from features.portfolio.db import SessionLocal, Holding

                    _db = SessionLocal()
                    _h = _db.query(Holding).filter(Holding.asset_type == "VN").first()
                    if _h:
                        default_user_id = _h.user_id
                    _db.close()
                except Exception:
                    default_user_id = 885131043772973097

                ai_data = await planner.generate_recap(
                    data,
                    DAILY_RECAP_SETTINGS.get("ai_news", False),
                    user_id=default_user_id,
                )

                # 3. Create PNG + Text output
                # format_daily_recap calls fetch_technical_signals (blocking I/O)
                # — must run in a thread to avoid blocking the Discord event loop.
                image_path = await generate_recap_image(data, ai_data)
                msg = await asyncio.to_thread(
                    format_daily_recap,
                    data, ai_data, DAILY_RECAP_SETTINGS.get("mode", "full")
                )

                def _split(text, limit=1950):
                    if len(text) <= limit:
                        return [text]
                    chunks, cur, cur_len = [], [], 0
                    for line in text.splitlines(keepends=True):
                        if cur_len + len(line) > limit and cur:
                            chunks.append("".join(cur))
                            cur, cur_len = [], 0
                        cur.append(line)
                        cur_len += len(line)
                    if cur:
                        chunks.append("".join(cur))
                    return chunks

                if image_path and os.path.exists(image_path):
                    file = discord.File(image_path, filename="daily_recap.png")
                    if len(msg) < 1900:
                        await channel.send(
                            content=msg + f"\n\n🖼️ **Bản tin đồ họa — {yesterday.strftime('%d/%m/%Y')}**",
                            file=file,
                        )
                    else:
                        for chunk in _split(msg):
                            await channel.send(content=chunk)
                        await channel.send(
                            content=f"🖼️ **Bản tin đồ họa — {yesterday.strftime('%d/%m/%Y')}**",
                            file=file,
                        )
                else:
                    for chunk in _split(msg):
                        await channel.send(content=chunk)

            except Exception as e:
                print(f"Error sending daily recap: {e}")

    @daily_report_loop.before_loop
    async def before_daily_report(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DailyRecapCog(bot))
