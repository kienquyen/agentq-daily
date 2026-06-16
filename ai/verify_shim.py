import sys
import os
import pandas as pd

# Add current dir to path
sys.path.insert(0, os.getcwd())

try:
    from vnstock_data import Market, show_api
    print("--- Testing vnstock_data shim ---")
    show_api()
    
    mkt = Market()
    print("Testing Market().equity('VCB').ohlcv()...")
    df = mkt.equity("VCB").ohlcv(start="2024-04-01", end="2024-04-03")
    print(f"OHLCV Result:\n{df.head() if not df.empty else 'Empty'}")
    
    print("\nTesting Market().equity('VCB').session_stats()...")
    df_stats = mkt.equity("VCB").session_stats()
    print(f"Stats Result:\n{df_stats.head() if not df_stats.empty else 'Empty'}")

    print("\n✅ Shim verification complete.")
except Exception as e:
    print(f"❌ Shim verification failed: {e}")
    import traceback
    traceback.print_exc()
