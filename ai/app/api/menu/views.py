"""
Menu Views - Discord UI Components
"""

import discord
from discord.ui import View, Button, Modal, TextInput

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from app.utils.helpers import safe_ticker
# Defer to callback
open_daily_recap_settings = None

# Feature handlers are now imported lazily inside callbacks to speed up startup.
handle_task1 = None
handle_task2 = None
handle_screener = None
open_task3_entry = None
open_shortlist = None
open_signal_weekly = None


class StockInputModal(Modal):
    def __init__(self, title: str = "Nhập mã cổ phiếu"):
        super().__init__(title=title)
        self.ticker = TextInput(
            label="Mã cổ phiếu",
            placeholder="Ví dụ: FPT",
            max_length=20,
            required=True,
        )
        self.add_item(self.ticker)


class ExpertMenuView(View):
    def __init__(self, timeout: int = 120):
        super().__init__(timeout=timeout)

    async def _ask_ticker_and_run(self, interaction: discord.Interaction, task: str):
        modal = StockInputModal()

        async def on_submit(i: discord.Interaction):
            await i.response.defer(ephemeral=True)
            ticker = safe_ticker(str(modal.ticker.value))
            if not ticker:
                await i.followup.send("Mã cổ phiếu không hợp lệ.", ephemeral=True)
                return

            try:
                await i.followup.send("Đang xử lý…", ephemeral=True)

                global handle_task1, handle_task2
                if task == "task1":
                    if handle_task1 is None:
                        try:
                            from features.quant.analysis import handle_task1 as _h1
                            handle_task1 = _h1
                        except ImportError:
                            from agentQquant.quantanalysis_singlestock import handle_task1 as _h1
                            handle_task1 = _h1
                    await handle_task1(i, ticker)
                    return

                if task == "task2":
                    if handle_task2 is None:
                        try:
                            from features.finance.analysis import handle_task2 as _h2
                            handle_task2 = _h2
                        except ImportError:
                            from agentQfinance.financeanalysis_singlestock import handle_task2 as _h2
                            handle_task2 = _h2
                    await handle_task2(i, ticker)
                    return

                await i.followup.send("Task không hợp lệ.", ephemeral=True)

            except Exception as e:
                await i.followup.send(f"Lỗi khi xử lý **{ticker}**: `{e}`", ephemeral=True)

        modal.on_submit = on_submit

        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "Tương tác đã hết hạn. Bạn gọi lại `/menu` rồi chọn lại nhé.",
                    ephemeral=True,
                )
                return
            await interaction.response.send_modal(modal)
        except discord.errors.NotFound:
            return

    @discord.ui.button(label="1. Tổng quan phiên đóng cửa gần nhất", style=discord.ButtonStyle.secondary, emoji="🌅", row=0)
    async def btn_daily_recap(self, interaction: discord.Interaction, button: Button):
        global open_daily_recap_settings
        if open_daily_recap_settings is None:
            from app.api.daily_recap.views import open_daily_recap_settings as _os
            open_daily_recap_settings = _os
        await open_daily_recap_settings(interaction)

    @discord.ui.button(label="2. Lọc cổ phiếu có thể mua/chờ mua", style=discord.ButtonStyle.secondary, emoji="🔍", row=1)
    async def btn_screener(self, interaction: discord.Interaction, button: Button):
        try:
            global handle_screener
            if handle_screener is None:
                from features.screener.classification import handle_screener as _hs
                handle_screener = _hs
            await handle_screener(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Screener chưa được liên kết: {e}", ephemeral=True)

    @discord.ui.button(label="3. Phân tích Định lượng", style=discord.ButtonStyle.primary, emoji="📈", row=2)
    async def btn_quant(self, interaction: discord.Interaction, button: Button):
        await self._ask_ticker_and_run(interaction, "task1")

    @discord.ui.button(label="4. Phân tích BCTC", style=discord.ButtonStyle.success, emoji="💼", row=3)
    async def btn_finance(self, interaction: discord.Interaction, button: Button):
        await self._ask_ticker_and_run(interaction, "task2")

    @discord.ui.button(label="5. Đánh giá danh mục & hành động", style=discord.ButtonStyle.primary, emoji="📊", row=4)
    async def btn_portfolio(self, interaction: discord.Interaction, button: Button):
        global open_task3_entry
        if open_task3_entry is None:
            try:
                from features.portfolio.discord_ui import open_task3_entry as _oe
                open_task3_entry = _oe
            except ImportError:
                try:
                    from Task3_AgentQ_Portfolio.ui import open_task3_entry as _oe
                    open_task3_entry = _oe
                except ImportError:
                    pass

        if open_task3_entry:
            await open_task3_entry(interaction)
        else:
            await interaction.response.send_message("Tính năng đang được phát triển.", ephemeral=True)

    @discord.ui.button(label="6. AI Shortlist hôm nay", style=discord.ButtonStyle.danger, emoji="🎯", row=4)
    async def btn_shortlist(self, interaction: discord.Interaction, button: Button):
        global open_shortlist
        if open_shortlist is None:
            from app.api.shortlist.views import open_shortlist_view as _osh
            open_shortlist = _osh
        await open_shortlist(interaction)

    @discord.ui.button(label="7. Signal AI Weekly", style=discord.ButtonStyle.danger, emoji="🤖", row=4)
    async def btn_signal_weekly(self, interaction: discord.Interaction, button: Button):
        global open_signal_weekly
        if open_signal_weekly is None:
            from features.signal.discord_ui import open_signal_weekly_entry as _osw
            open_signal_weekly = _osw
        await open_signal_weekly(interaction)


def build_menu_view() -> ExpertMenuView:
    """Build the main menu view."""
    return ExpertMenuView()
