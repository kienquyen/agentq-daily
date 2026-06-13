#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgentQ Discord Bot - Main Entry Point
Buytrend/Vnstock Portfolio Management System
"""

import discord
from discord.ext import commands

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import validate_required, DISCORD_TOKEN
from app.api.menu.views import build_menu_view

# init_db is now called inside setup_hook asynchronously


class AgentQBot(commands.Bot):
    """
    Proper subclass of commands.Bot.
    Overriding on_message as a class method ensures that
    BotBase.on_message (which calls process_commands) is
    completely replaced — no double-dispatch, no double menus.
    """

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self._seen_messages: set = set()  # dedup cache

    async def setup_hook(self):
        # 1. Database initialization (Non-blocking)
        print("🗄️ Connecting to database...")
        try:
            import asyncio
            from infrastructure.database import init_db
            await asyncio.to_thread(init_db)
            print("✅ Database connected.")
        except Exception as e:
            print(f"⚠️ Database initialization failed: {e}")

        # 2. Background Tasks
        try:
            from app.services.daily_recap_job import DailyRecapCog
            await self.add_cog(DailyRecapCog(self))
            print("Loaded DailyRecapCog background task.")
        except Exception as e:
            print(f"Failed to load DailyRecapCog: {e}")

        # 3. ML Shortlist Job (Phase 6 — 19:00 ICT daily)
        try:
            from app.services.shortlist_job import ShortlistCog
            await self.add_cog(ShortlistCog(self))
            print("✅ Loaded ShortlistCog (19:00 ICT daily shortlist).")
        except Exception as e:
            print(f"⚠️ Failed to load ShortlistCog: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (id={self.user.id})")

    async def on_message(self, message: discord.Message):
        # Ignore bot messages
        if message.author.bot:
            return

        # Deduplication — safety net against any phantom duplicates
        if message.id in self._seen_messages:
            return
        self._seen_messages.add(message.id)
        if len(self._seen_messages) > 200:
            try:
                self._seen_messages.discard(next(iter(self._seen_messages)))
            except StopIteration:
                pass

        # Send menu on plain @mention only (no "!" prefix, no command text)
        content = message.content.strip()
        is_plain_mention = (
            self.user is not None and
            self.user.mentioned_in(message) and
            not content.startswith("!")
        )
        if is_plain_mention:
            await message.reply(
                "Bạn cần hỗ trợ gì? 👇",
                view=build_menu_view(),
                mention_author=False,
            )
            return

        # For all other messages (e.g. "!some_command"), process normally
        await self.process_commands(message)


def main():
    validate_required()
    bot = AgentQBot()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
