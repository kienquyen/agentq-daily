import discord
import traceback
from discord.ui import View, Button, Select, Modal, TextInput

# Feature functions are now imported lazily inside callbacks
fetch_all = None
AICapacityPlanner = None
format_daily_recap = None
generate_recap_image = None
import os
import datetime


def _split_message(text: str, limit: int = 1950) -> list[str]:
    """Split a long message into ≤limit-char chunks, breaking at newlines."""
    if len(text) <= limit:
        return [text]
    chunks, current, current_len = [], [], 0
    for line in text.splitlines(keepends=True):
        if current_len + len(line) > limit and current:
            chunks.append("".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line)
    if current:
        chunks.append("".join(current))
    return chunks


async def _send_recap_fallback(interaction: discord.Interaction, msg: str) -> None:
    """Send recap text (no image) safely — splits if > 1950 chars."""
    chunks = _split_message(msg)
    if len(chunks) == 1:
        await interaction.edit_original_response(content=chunks[0])
    else:
        await interaction.edit_original_response(content="✅ **Bản tin đã sẵn sàng:**")
        for chunk in chunks:
            await interaction.followup.send(content=chunk, ephemeral=True)

# Global mock for setting storage
DAILY_RECAP_SETTINGS = {
    "is_active": True,
    "channel_id": None,
    "time": "07:00",
    "mode": "full", 
    "ai_news": True # Enabled by default for best UX
}

class RecapDateModal(Modal):
    def __init__(self):
        super().__init__(title="Gửi bản tin theo ngày")
        self.date_input = TextInput(
            label="Ngày (Định dạng: YYYY-MM-DD)",
            placeholder="Ví dụ: 2024-03-25",
            min_length=10,
            max_length=10,
            default=datetime.date.today().strftime("%Y-%m-%d"),
            required=True
        )
        self.add_item(self.date_input)

    async def on_submit(self, interaction: discord.Interaction):
        target_date = self.date_input.value.strip()
        # Basic validation
        try:
            datetime.datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message("❌ Định dạng ngày không hợp lệ. Vui lòng dùng YYYY-MM-DD (Ví dụ: 2024-03-25)", ephemeral=True)
            return

        await interaction.response.send_message(f"⏳ **Đang lấy thông tin thị trường cho ngày {target_date}...**\nVui lòng chờ trong giây lát.", ephemeral=True)
        
        async def progress_callback(current, total):
            if current % 50 == 0 or current == total:
                try:
                    await interaction.edit_original_response(content=f"⏳ **Đang xử lý dữ liệu ngày {target_date}...**\nTiến độ: Đã quét `{current}/{total}` mã.")
                except Exception:
                    pass
                    
        try:
            # Lazy imports
            global fetch_all, AICapacityPlanner, format_daily_recap, generate_recap_image
            if fetch_all is None:
                from features.daily_recap.data_fetcher import fetch_all as _fa
                fetch_all = _fa
            if AICapacityPlanner is None:
                from features.daily_recap.ai_generator import AICapacityPlanner as _ap
                AICapacityPlanner = _ap
            if format_daily_recap is None:
                from features.daily_recap.formatter import format_daily_recap as _fr
                format_daily_recap = _fr
            if generate_recap_image is None:
                from features.daily_recap.formatter import generate_recap_image as _gi
                generate_recap_image = _gi

            # 1. Fetch
            data = await fetch_all(progress_callback=progress_callback, target_date=target_date)
            # 2. AI
            planner = AICapacityPlanner()
            ai_data = await planner.generate_recap(data, DAILY_RECAP_SETTINGS["ai_news"], user_id=interaction.user.id, target_date=target_date)
            
            # 3. Create PNG/Text Dual Output
            image_path = await generate_recap_image(data, ai_data)
            msg = format_daily_recap(data, ai_data, DAILY_RECAP_SETTINGS["mode"])
            print(f"DEBUG: Date Modal - Recieved msg length: {len(msg)}")
            
            if image_path and os.path.exists(image_path):
                file = discord.File(image_path, filename=f"daily_recap_{target_date}.png")
                if len(msg) < 1900:
                    await interaction.channel.send(
                        content=msg + f"\n\n🖼️ **Bản tin đồ họa — {target_date}**",
                        file=file
                    )
                else:
                    for chunk in _split_message(msg):
                        await interaction.channel.send(content=chunk)
                    await interaction.channel.send(
                        content=f"🖼️ **Bản tin đồ họa — {target_date}**",
                        file=file
                    )
                await interaction.edit_original_response(content=f"✅ **Bản tin ngày {target_date} đã gửi thành công (Text + PNG)!**")
            else:
                await _send_recap_fallback(interaction, msg)
        except Exception as e:
            traceback.print_exc()
            await interaction.edit_original_response(content=f"Lỗi: {str(e)[:1800]}")

class DailyRecapSettingsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        
        # Mode Select
        mode_select = Select(
            placeholder=f"Mode: {'Full' if DAILY_RECAP_SETTINGS['mode'] == 'full' else 'Compact'}",
            options=[
                discord.SelectOption(label="Full Mode", value="full", description="Bản đầy đủ tin tức, risk radar"),
                discord.SelectOption(label="Compact Mode", value="compact", description="Bản siêu ngắn gọn 1 phút")
            ]
        )
        async def mode_callback(interaction: discord.Interaction):
            DAILY_RECAP_SETTINGS["mode"] = mode_select.values[0]
            await self.refresh_ui(interaction)
        mode_select.callback = mode_callback
        self.add_item(mode_select)

        # Time Select
        time_select = Select(
            placeholder=f"Time: {DAILY_RECAP_SETTINGS['time']} AM",
            options=[
                discord.SelectOption(label="06:30 AM", value="06:30"),
                discord.SelectOption(label="07:00 AM", value="07:00"),
                discord.SelectOption(label="07:30 AM", value="07:30")
            ]
        )
        async def time_callback(interaction: discord.Interaction):
            DAILY_RECAP_SETTINGS["time"] = time_select.values[0]
            await self.refresh_ui(interaction)
        time_select.callback = time_callback
        self.add_item(time_select)

        # Status Toggle
        is_on = DAILY_RECAP_SETTINGS["is_active"]
        btn_toggle = Button(
            label="Turn OFF" if is_on else "Turn ON", 
            style=discord.ButtonStyle.danger if is_on else discord.ButtonStyle.success,
            emoji="🔴" if is_on else "🟢"
        )
        async def btn_toggle_callback(interaction: discord.Interaction):
            DAILY_RECAP_SETTINGS["is_active"] = not DAILY_RECAP_SETTINGS["is_active"]
            await self.refresh_ui(interaction)
        btn_toggle.callback = btn_toggle_callback
        self.add_item(btn_toggle)

        # AI News Toggle
        ai_on = DAILY_RECAP_SETTINGS["ai_news"]
        btn_ai = Button(
            label="AI News: ON" if ai_on else "AI News: OFF", 
            style=discord.ButtonStyle.primary if ai_on else discord.ButtonStyle.secondary,
            emoji="🤖"
        )
        async def btn_ai_callback(interaction: discord.Interaction):
            DAILY_RECAP_SETTINGS["ai_news"] = not DAILY_RECAP_SETTINGS["ai_news"]
            await self.refresh_ui(interaction)
        btn_ai.callback = btn_ai_callback
        self.add_item(btn_ai)

        # Test Send Now
        btn_test = Button(label="Send Test MSG", style=discord.ButtonStyle.primary, emoji="📤")
        async def btn_test_callback(interaction: discord.Interaction):
            await interaction.response.send_message("⏳ **Đang lấy thông tin thị trường mới nhất...**\nVui lòng chờ trong giây lát (Quá trình quét nhóm VN100 có thể mất 15-30 giây).", ephemeral=True)
            
            async def progress_callback(current, total):
                if current % 50 == 0 or current == total:
                    try:
                        await interaction.edit_original_response(content=f"⏳ **Đang lấy thông tin thị trường mới nhất...**\nTiến độ: Đã quét `{current}/{total}` mã. (Còn lại: `{total - current}` mã)")
                    except Exception:
                        pass
                        
            try:
                # Lazy imports
                global fetch_all, AICapacityPlanner, format_daily_recap, generate_recap_image
                if fetch_all is None:
                    from features.daily_recap.data_fetcher import fetch_all as _fa
                    fetch_all = _fa
                if AICapacityPlanner is None:
                    from features.daily_recap.ai_generator import AICapacityPlanner as _ap
                    AICapacityPlanner = _ap
                if format_daily_recap is None:
                    from features.daily_recap.formatter import format_daily_recap as _fr
                    format_daily_recap = _fr
                if generate_recap_image is None:
                    from features.daily_recap.formatter import generate_recap_image as _gi
                    generate_recap_image = _gi

                # 1. Fetch
                data = await fetch_all(progress_callback=progress_callback)
                # 2. AI
                planner = AICapacityPlanner()
                ai_data = await planner.generate_recap(data, DAILY_RECAP_SETTINGS["ai_news"], user_id=interaction.user.id)
                
                # 3. Create PNG/Text Dual Output
                image_path = await generate_recap_image(data, ai_data)
                msg = format_daily_recap(data, ai_data, DAILY_RECAP_SETTINGS["mode"])
                print(f"DEBUG: Manual Trigger - Recieved msg length: {len(msg)}")
                
                if image_path and os.path.exists(image_path):
                    file = discord.File(image_path, filename="daily_recap.png")
                    today_str = datetime.date.today().strftime('%d/%m/%Y')
                    if len(msg) < 1900:
                        await interaction.followup.send(
                            content=msg + f"\n\n🖼️ **Bản tin đồ họa — {today_str}**",
                            file=file,
                            ephemeral=False
                        )
                    else:
                        for chunk in _split_message(msg):
                            await interaction.followup.send(content=chunk, ephemeral=False)
                        await interaction.followup.send(
                            content=f"🖼️ **Bản tin đồ họa — {today_str}**",
                            file=file,
                            ephemeral=False
                        )
                    await interaction.edit_original_response(content="✅ **Bản tin đã gửi thành công (Text + PNG)!**")
                else:
                    await _send_recap_fallback(interaction, msg)
            except Exception as e:
                traceback.print_exc()
                await interaction.edit_original_response(content=f"Lỗi: {e}")
        btn_test.callback = btn_test_callback
        self.add_item(btn_test)

        # [NEW] Send by Date
        btn_date = Button(label="Gửi theo ngày", style=discord.ButtonStyle.secondary, emoji="📅")
        async def btn_date_callback(interaction: discord.Interaction):
            await interaction.response.send_modal(RecapDateModal())
        btn_date.callback = btn_date_callback
        self.add_item(btn_date)

    async def refresh_ui(self, interaction: discord.Interaction):
        self.update_buttons()
        # Save channel if interacting in a guild
        if interaction.channel:
            DAILY_RECAP_SETTINGS["channel_id"] = interaction.channel.id
            
        embed = discord.Embed(
            title="⚙️ AgentQ Bản tin buổi sáng Configuration",
            description=(f"*Status:* {'🟢 **ACTIVE**' if DAILY_RECAP_SETTINGS['is_active'] else '🔴 **INACTIVE**'}\n"
                         f"*Channel:* <#{DAILY_RECAP_SETTINGS.get('channel_id', 'Chưa chọn')}>\n"
                         f"*Time:* `{DAILY_RECAP_SETTINGS['time']} AM (ICT)`\n"
                         f"*Mode:* `{DAILY_RECAP_SETTINGS['mode'].title()}`\n"
                         f"*AI News Summary:* `{'ON' if DAILY_RECAP_SETTINGS['ai_news'] else 'OFF'}`")
        )
        await interaction.response.edit_message(embed=embed, view=self)

async def open_daily_recap_settings(interaction: discord.Interaction):
    # Register current channel by default if none exists
    if not DAILY_RECAP_SETTINGS.get("channel_id") and interaction.channel:
        DAILY_RECAP_SETTINGS["channel_id"] = interaction.channel.id
    
    view = DailyRecapSettingsView()
    embed = discord.Embed(
        title="⚙️ AgentQ Bản tin buổi sáng Configuration",
        description=(f"*Status:* {'🟢 **ACTIVE**' if DAILY_RECAP_SETTINGS['is_active'] else '🔴 **INACTIVE**'}\n"
                     f"*Channel:* <#{DAILY_RECAP_SETTINGS.get('channel_id', 'Chưa chọn')}>\n"
                     f"*Time:* `{DAILY_RECAP_SETTINGS['time']} AM (ICT)`\n"
                     f"*Mode:* `{DAILY_RECAP_SETTINGS['mode'].title()}`\n"
                     f"*AI News Summary:* `{'ON' if DAILY_RECAP_SETTINGS['ai_news'] else 'OFF'}`")
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
