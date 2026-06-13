# features.portfolio/ui.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import discord
from discord.ui import View, Button, Modal, TextInput, Select

from .parser import parse_portfolio_modal_input
from .storage import (
    replace_holdings,
    get_latest_portfolio,
    load_portfolio_state,
    serialize_holdings_to_modal,
    add_holding,
    update_holding,
    delete_holding,
)
from .service import generate_pm_grade_report_v3
from .formatter import build_compact_embeds, build_details_embeds

# ============================================================
# Safe helpers
# ============================================================


async def _safe_defer(interaction: discord.Interaction, ephemeral: bool = True) -> bool:
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)
        return True
    except discord.errors.NotFound:
        return False
    except Exception:
        return False


async def _safe_send(
    interaction: discord.Interaction, content: str, *, ephemeral: bool = True, **kwargs
):
    try:
        if interaction.response.is_done():
            return await interaction.followup.send(
                content=content, ephemeral=ephemeral, **kwargs
            )
        return await interaction.response.send_message(
            content=content, ephemeral=ephemeral, **kwargs
        )
    except discord.errors.NotFound:
        return None


async def _safe_followup(
    interaction: discord.Interaction, content: str, *, ephemeral: bool = True, **kwargs
):
    try:
        return await interaction.followup.send(
            content=content, ephemeral=ephemeral, **kwargs
        )
    except discord.errors.NotFound:
        return None


async def _run_report(user_id: int, interaction: discord.Interaction):
    await _safe_followup(
        interaction, "⏳ Fetch dữ liệu & tính **PM Report v3**…", ephemeral=True
    )
    try:
        report = await generate_pm_grade_report_v3(user_id, mode="compact")
        embeds = build_compact_embeds(report)
        await _safe_followup(
            interaction,
            "✅ **PM Report v3 (COMPACT):**",
            embeds=embeds,
            view=DetailsView(user_id),
            ephemeral=True,
        )
    except Exception as ex:
        await _safe_followup(
            interaction, f"❌ Lỗi khi generate report: `{ex}`", ephemeral=True
        )


# ============================================================
# Modals
# ============================================================


class PortfolioModal(Modal):
    def __init__(self, title: str = "Task 3 — Nhập / Chỉnh sửa danh mục"):
        super().__init__(title=title)

        self.stocks = TextInput(
            label="1) VN Stocks (ticker,qty,avg_cost)",
            placeholder="FPT,1000,90000\nMBB,2000,18000",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
        )
        self.crypto = TextInput(
            label="2) Crypto (symbol,qty,avg_cost)",
            placeholder="BTCUSDT,0.5,40000\nETHUSDT,2,2500",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
        )
        self.cash_vnd = TextInput(
            label="3) Cash VND",
            placeholder="500000000",
            required=False,
            max_length=30,
        )
        self.cash_usdt = TextInput(
            label="4) Cash USDT",
            placeholder="20000",
            required=False,
            max_length=30,
        )
        self.risk = TextInput(
            label="5) Risk score (1-10)",
            placeholder="7",
            required=False,
            max_length=2,
        )

        self.add_item(self.stocks)
        self.add_item(self.crypto)
        self.add_item(self.cash_vnd)
        self.add_item(self.cash_usdt)
        self.add_item(self.risk)


class AddHoldingModal(Modal):
    def __init__(self, user_id: int, on_done_callback=None):
        super().__init__(title="Thêm / Cập nhật vị thế")
        self.user_id = user_id
        self._on_done = on_done_callback

        self.asset_type = Select(
            placeholder="Loại tài sản",
            options=[
                discord.SelectOption(label="VN Stocks", value="VN", emoji="📈"),
                discord.SelectOption(label="Crypto", value="CRYPTO", emoji="🪙"),
                discord.SelectOption(label="Cash VND", value="CASH_VND", emoji="💰"),
                discord.SelectOption(label="Cash USDT", value="CASH_USDT", emoji="💵"),
            ],
            row=0,
        )
        self.symbol = TextInput(
            label="Symbol / Mã",
            placeholder="FPT, BTCUSDT, VND, USDT",
            required=True,
            max_length=16,
            row=1,
        )
        self.qty = TextInput(
            label="Số lượng (qty)",
            placeholder="1000",
            required=True,
            max_length=20,
            row=2,
        )
        self.avg_cost = TextInput(
            label="Giá mua trung bình (avg_cost)",
            placeholder="90000",
            required=True,
            max_length=20,
            row=3,
        )
        self.hint = TextInput(
            label="Ghi chú (tùy chọn)",
            placeholder="",
            required=False,
            max_length=100,
            row=4,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(f"❌ Lỗi: {error}", ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        asset_val = self.asset_type.values[0] if self.asset_type.values else ""
        sym = self.symbol.value.strip().upper()
        try:
            qty = float(self.qty.value.strip())
            avg = float(self.avg_cost.value.strip())
        except ValueError:
            await interaction.followup.send(
                "❌ qty và avg_cost phải là số.", ephemeral=True
            )
            return

        if asset_val == "CASH_VND":
            atype, ccy = "CASH", "VND"
        elif asset_val == "CASH_USDT":
            atype, ccy = "CASH", "USDT"
        else:
            atype, ccy = asset_val, ("VND" if asset_val == "VN" else "USDT")

        ok = add_holding(self.user_id, atype, sym, qty, avg, ccy)
        if ok:
            msg = f"✅ Đã {'cập nhật' if atype != 'CASH' and False else 'thêm'} **{sym}** ({qty:.0f} @ {avg:,.0f} {ccy})"
        else:
            msg = f"❌ Không thể thêm {sym}."

        await interaction.followup.send(msg, ephemeral=True)

        if self._on_done:
            await self._on_done(interaction)


class EditHoldingModal(Modal):
    def __init__(self, user_id: int, holding: dict, on_done_callback=None):
        super().__init__(title=f"Sửa {holding['symbol']} — {holding['type']}")
        self.user_id = user_id
        self._holding = holding
        self._on_done = on_done_callback

        atype = holding.get("asset_type", "VN")
        ccy = holding.get("cost_ccy", "VND")
        sym = holding.get("symbol", "")
        qty = holding.get("qty", 0)
        avg = holding.get("avg_cost", 0)

        self.symbol_display = TextInput(
            label="Symbol",
            default_value=sym,
            required=True,
            max_length=16,
            row=0,
        )
        self.qty = TextInput(
            label="Số lượng (qty)",
            default_value=str(qty),
            required=True,
            max_length=20,
            row=1,
        )
        self.avg_cost = TextInput(
            label="Giá mua trung bình (avg_cost)",
            default_value=str(avg),
            required=True,
            max_length=20,
            row=2,
        )
        self.asset_type = atype
        self.ccy = ccy

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        sym = self.symbol_display.value.strip().upper()
        try:
            qty = float(self.qty.value.strip())
            avg = float(self.avg_cost.value.strip())
        except ValueError:
            await interaction.followup.send(
                "❌ qty và avg_cost phải là số.", ephemeral=True
            )
            return

        ok = update_holding(self.user_id, sym, self.asset_type, qty, avg)
        if ok:
            await interaction.followup.send(
                f"✅ Đã cập nhật **{sym}** → qty={qty:.0f}, avg={avg:,.0f} {self.ccy}",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"❌ Không tìm thấy {sym} để cập nhật.", ephemeral=True
            )

        if self._on_done:
            await self._on_done(interaction)


# ============================================================
# Views
# ============================================================


class DetailsView(View):
    def __init__(self, user_id: int, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.user_id = user_id

    @discord.ui.button(
        label="View Details", style=discord.ButtonStyle.secondary, emoji="🔎"
    )
    async def btn_details(self, interaction: discord.Interaction, button: Button):
        ok = await _safe_defer(interaction, ephemeral=True)
        if not ok:
            return
        await _safe_followup(interaction, "⏳ Đang tải **Details v3**…", ephemeral=True)
        try:
            report = await generate_pm_grade_report_v3(self.user_id, mode="details")
            embeds = build_details_embeds(report)
            await _safe_followup(
                interaction, "✅ **Details v3:**", embeds=embeds, ephemeral=True
            )
        except Exception as ex:
            await _safe_followup(interaction, f"❌ Lỗi: `{ex}`", ephemeral=True)


class HoldingsManageView(View):
    def __init__(
        self, user_id: int, holdings: list, on_done_callback=None, timeout: int = 300
    ):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self._holdings = holdings
        self._on_done = on_done_callback

        options = []
        for h in holdings:
            sym = h.get("symbol", "?")
            atype = h.get("asset_type", "?")
            qty = h.get("qty", 0)
            avg = h.get("avg_cost", 0)
            ccy = h.get("cost_ccy", "VND")
            emoji = "📈" if atype == "VN" else ("🪙" if atype == "CRYPTO" else "💰")
            label = f"{emoji} {sym} | {qty:,.0f} @ {avg:,.0f} {ccy}"
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=f"{sym}|{atype}",
                    description=f"Xóa hoặc sửa {sym}",
                )
            )

        if options:
            select = Select(
                placeholder="Chọn vị thế để quản lý…",
                options=options,
                row=0,
            )
            select.callback = self._on_select  # type: ignore
            self.add_item(select)

        self.add_item(
            Button(
                label="+ Thêm vị thế mới",
                style=discord.ButtonStyle.success,
                emoji="➕",
                row=2,
            )
        )
        self.children[-1].callback = self._on_add  # type: ignore

        self.add_item(
            Button(
                label="↩️ Quay lại",
                style=discord.ButtonStyle.secondary,
                emoji="🔙",
                row=2,
            )
        )
        self.children[-1].callback = self._on_back  # type: ignore

    async def _on_select(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        val = interaction.data.get("values", [None])[0]
        if not val:
            return
        sym, atype = val.split("|", 1)

        h = next(
            (
                x
                for x in self._holdings
                if x.get("symbol") == sym and x.get("asset_type") == atype
            ),
            None,
        )
        if not h:
            await interaction.followup.send(f"❌ Không tìm thấy {sym}.", ephemeral=True)
            return

        action_view = SingleHoldingActionView(self.user_id, h, self._on_done)
        await interaction.followup.send(
            f"📋 **{sym}** — Chọn thao tác:",
            view=action_view,
            ephemeral=True,
        )

    async def _on_add(self, interaction: discord.Interaction):
        modal = AddHoldingModal(self.user_id, on_done_callback=self._on_done)
        await interaction.response.send_modal(modal)

    async def _on_back(self, interaction: discord.Interaction):
        if self._on_done:
            await self._on_done(interaction)
        else:
            await interaction.response.defer(ephemeral=True)
            await interaction.delete_original_response()


class SingleHoldingActionView(View):
    def __init__(
        self, user_id: int, holding: dict, on_done_callback=None, timeout: int = 60
    ):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self._holding = holding
        self._on_done = on_done_callback

        sym = holding.get("symbol", "?")
        atype = holding.get("asset_type", "?")
        qty = holding.get("qty", 0)
        avg = holding.get("avg_cost", 0)
        ccy = holding.get("cost_ccy", "VND")

        self.info_label = f"{sym} | qty={qty:,.0f} | avg={avg:,.0f} {ccy}"

        self.add_item(
            Button(
                label=f"✏️ Sửa {sym}",
                style=discord.ButtonStyle.primary,
                emoji="✏️",
                row=0,
            )
        )
        self.children[-1].callback = self._on_edit  # type: ignore

        self.add_item(
            Button(
                label=f"🗑️ Xóa {sym}",
                style=discord.ButtonStyle.danger,
                emoji="🗑️",
                row=0,
            )
        )
        self.children[-1].callback = self._on_delete  # type: ignore

    async def _on_edit(self, interaction: discord.Interaction):
        modal = EditHoldingModal(
            self.user_id, self._holding, on_done_callback=self._on_done
        )
        await interaction.response.send_modal(modal)

    async def _on_delete(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sym = self._holding.get("symbol", "")
        atype = self._holding.get("asset_type", "")

        ok = delete_holding(self.user_id, sym, atype)
        if ok:
            await interaction.followup.send(
                f"🗑️ Đã xóa **{sym}** khỏi danh mục.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"❌ Không tìm thấy {sym} để xóa.", ephemeral=True
            )

        if self._on_done:
            await self._on_done(interaction)


# ============================================================
# Entry menu view
# ============================================================


class PortfolioChoiceView(View):
    def __init__(self, timeout: int = 180):
        super().__init__(timeout=timeout)

    @discord.ui.button(
        label="Nhập / Chỉnh sửa danh mục", style=discord.ButtonStyle.primary, emoji="🆕"
    )
    async def btn_new(self, interaction: discord.Interaction, button: Button):
        modal = PortfolioModal()

        state = load_portfolio_state(interaction.user.id)
        rows = state.get("holdings", [])
        stocks_txt, crypto_txt, cash_vnd, cash_usdt = serialize_holdings_to_modal(rows)
        risk = str(state.get("risk", 7))

        modal.stocks.default = stocks_txt
        modal.crypto.default = crypto_txt
        modal.cash_vnd.default = cash_vnd
        modal.cash_usdt.default = cash_usdt
        modal.risk.default = risk

        async def on_submit(i: discord.Interaction):
            ok = await _safe_defer(i, ephemeral=True)
            if not ok:
                return

            ok_parse, payload = parse_portfolio_modal_input(
                stocks_text=str(modal.stocks.value or ""),
                crypto_text=str(modal.crypto.value or ""),
                cash_vnd=str(modal.cash_vnd.value or ""),
                cash_usdt=str(modal.cash_usdt.value or ""),
                risk_text=str(modal.risk.value or ""),
            )
            if not ok_parse:
                await _safe_followup(i, f"❌ Input error: {payload}", ephemeral=True)
                return

            replace_holdings(
                user_id=i.user.id,
                base="VND",
                risk=int(payload["risk"]),
                holdings_rows=payload["rows"],
            )

            await _run_report(i.user.id, i)

        modal.on_submit = on_submit  # type: ignore

        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "⚠️ Interaction expired. Gọi lại /menu nhé.", ephemeral=True
                )
                return
            await interaction.response.send_modal(modal)
        except discord.errors.NotFound:
            return

    @discord.ui.button(
        label="Quản lý Holdings", style=discord.ButtonStyle.secondary, emoji="⚙️"
    )
    async def btn_manage(self, interaction: discord.Interaction, button: Button):
        ok = await _safe_defer(interaction, ephemeral=True)
        if not ok:
            return

        snap = get_latest_portfolio(interaction.user.id)
        rows = snap.get("holdings", [])
        if not rows:
            await _safe_followup(
                interaction, "❌ Chưa có danh mục nào để quản lý.", ephemeral=True
            )
            return

        async def on_done(i: discord.Interaction):
            snap2 = get_latest_portfolio(interaction.user.id)
            rows2 = snap2.get("holdings", [])
            if not rows2:
                await _safe_followup(
                    i,
                    "✅ Đã xóa hết holdings. Danh mục trống.",
                    ephemeral=True,
                )
                return
            view2 = HoldingsManageView(
                interaction.user.id, rows2, on_done_callback=on_done
            )
            await i.edit_original_response(
                content="📋 **Quản lý Holdings** — Cập nhật:", view=view2
            )

        view = HoldingsManageView(interaction.user.id, rows, on_done_callback=on_done)
        await _safe_followup(
            interaction,
            "📋 **Quản lý Holdings** — Chọn vị thế hoặc thêm mới:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(
        label="Dùng danh mục gần nhất", style=discord.ButtonStyle.success, emoji="♻️"
    )
    async def btn_last(self, interaction: discord.Interaction, button: Button):
        ok = await _safe_defer(interaction, ephemeral=True)
        if not ok:
            return

        snap = get_latest_portfolio(interaction.user.id)
        if not snap or not snap.get("holdings"):
            await _safe_followup(
                interaction, "❌ Chưa có danh mục trước đó.", ephemeral=True
            )
            return

        await _run_report(interaction.user.id, interaction)

    @discord.ui.button(
        label="Xem danh mục hiện tại", style=discord.ButtonStyle.secondary, emoji="👀"
    )
    async def btn_view(self, interaction: discord.Interaction, button: Button):
        ok = await _safe_defer(interaction, ephemeral=True)
        if not ok:
            return

        snap = get_latest_portfolio(interaction.user.id)
        rows = snap.get("holdings", [])

        if not rows:
            await _safe_followup(interaction, "❌ Chưa có danh mục.", ephemeral=True)
            return

        lines = [f"**BASE={snap.get('base', 'VND')} | RISK={snap.get('risk', '7')}**"]
        vn = [r for r in rows if r.get("asset_type") == "VN"]
        crypto = [r for r in rows if r.get("asset_type") == "CRYPTO"]
        cash = [r for r in rows if r.get("asset_type") == "CASH"]

        if vn:
            lines.append("\n📈 **VN Stocks:**")
            for r in vn:
                lines.append(
                    f"  {r.get('symbol'):<8} qty={r.get('qty'):>10,.0f}  avg={r.get('avg_cost'):>10,.0f} VND"
                )
        if crypto:
            lines.append("\n🪙 **Crypto:**")
            for r in crypto:
                lines.append(
                    f"  {r.get('symbol'):<12} qty={r.get('qty'):>12}  avg={r.get('avg_cost'):>10,.2f} USDT"
                )
        if cash:
            lines.append("\n💰 **Cash:**")
            for r in cash:
                ccy = r.get("cost_ccy", "VND")
                val = r.get("qty", 0)
                lines.append(f"  {r.get('symbol'):<6}  {val:>15,.0f} {ccy}")

        await _safe_followup(interaction, "\n".join(lines), ephemeral=True)


# ============================================================
# Entry point
# ============================================================


async def open_task3_entry(interaction: discord.Interaction):
    view = PortfolioChoiceView()
    msg = "📊 **Task 3 — Portfolio Manager (v3)**\nChọn thao tác:"
    await _safe_send(interaction, msg, view=view, ephemeral=True)
