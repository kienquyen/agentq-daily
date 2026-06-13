#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgentQ - Buytrend/Vnstock Portfolio Management System
Main Entry Point

Scalable architecture for 100k+ users.
"""

import sys
import os
from dotenv import load_dotenv

# Load env variables before importing anything
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import vnstock_bootstrap
except Exception as e:
    print(f"⚠️ Warning: vnstock_bootstrap failed to run: {e}")

print("⏳ Loading AI & Bot libraries (this might take a few moments)...")
from app.bot import main

if __name__ == "__main__":
    main()
