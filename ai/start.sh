#!/bin/bash
set -e

echo "🎭 Installing Playwright Chromium + system dependencies..."
playwright install --with-deps chromium
echo "✅ Playwright Chromium ready."

exec python main.py
