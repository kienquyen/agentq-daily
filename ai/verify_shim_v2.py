import sys
import os
import pandas as pd

# Add current directory to path to pick up local vnstock_data
sys.path.insert(0, os.getcwd())

try:
    from vnstock_data import Market, show_api, show_doc
    print("Successfully imported Market, show_api, show_doc from local vnstock_data")
    
    show_api()
    show_doc("Market.equity")

    mkt = Market()
    symbol = "VCB"
    
    print(f"\n--- Testing Market().equity('{symbol}').ohlcv() ---")
    df_ohlcv = mkt.equity(symbol).ohlcv(start="2026-03-30", end="2026-04-03")
    print(df_ohlcv.head())
    
    print(f"\n--- Testing Market().equity('{symbol}').history() ---")
    df_hist = mkt.equity(symbol).history(start="2026-03-30", end="2026-04-03")
    print(df_hist.head())

    print(f"\n--- Testing Market().equity('{symbol}').foreign_flow() ---")
    df_foreign = mkt.equity(symbol).foreign_flow(limit=5)
    print(df_foreign.head() if not df_foreign.empty else "Empty DataFrame returned (as expected if not implemented or no data)")

    print(f"\n--- Testing Market().equity('{symbol}').session_stats() ---")
    df_stats = mkt.equity(symbol).session_stats()
    print(df_stats.head() if not df_stats.empty else "Empty DataFrame returned (fallback worked or no data)")

    print("\nShim verification complete!")

except Exception as e:
    print(f"Error during verification: {e}")
    import traceback
    traceback.print_exc()
