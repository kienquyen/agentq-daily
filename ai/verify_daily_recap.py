import asyncio
import sys
import os
import json
from typing import Dict, Any

# Add project root to path
sys.path.append(os.getcwd())

# Force debug AI to see logs
os.environ["DEBUG_AI"] = "1"

async def verify_flow():
    # symbols for testing
    test_symbols = ["FPT", "MWG", "VCB", "VIC"]
    
    print(f"--- 1. Fetching News (Priority for {test_symbols}) ---")
    try:
        from features.daily_recap.data_fetcher import get_news
        news = get_news(symbols=test_symbols)
        print(f"Fetched {len(news)} news items.")
        for i, n in enumerate(news):
            marker = " [PRIORITY]" if any(s.upper() in n['headline'].upper() or s.upper() in n['impact_base'].upper() for s in test_symbols) else ""
            print(f"[{i}]{marker} {n['headline']}")
    except Exception as e:
        print(f"Error fetching news: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n--- 2. Generating Enhanced AI Summary ---")
    try:
        from features.daily_recap.ai_generator import AICapacityPlanner
        from features.ai.gemini import GeminiService
        
        # Initialize components
        ai_service = GeminiService()
        planner = AICapacityPlanner(ai_service)
        
        # Mock input data with flow for ticker extraction
        mock_data = {
            "snapshot": {
                "vnindex": 1250.5,
                "change_pct": 0.5,
                "vs_ma50_pct": 1.2,
                "volume_ratio": 1.1,
                "ad_advances": 250,
                "ad_unchanged": 50,
                "ad_declines": 100,
                "foreign_flow_bil": -150.0,
                "dist_days": 2
            },
            "flow": {
                "inflow": [{"sector": "Công nghệ", "tickers": ["FPT", "CMG"]}],
                "outflow": [{"sector": "Bán lẻ", "tickers": ["MWG", "PNJ"]}]
            },
            "news": news,
            "watchlist": {
                "breakout": [{"ticker": "FPT"}],
                "breakdown": [{"ticker": "MWG"}],
                "anomaly": []
            }
        }
        
        ai_recap = await planner.generate_recap(mock_data, include_ai_news=True)
        print("AI Recap generated successfully.")
        print(f"Regime: {ai_recap['regime']}")
        print(f"AI News count: {len(ai_recap.get('ai_news', []))}")
        for item in ai_recap.get('ai_news', []):
            print(f"- {item.get('tag')} | {item.get('headline')}")
            print(f"  Summary: {item.get('ai_summary')}")
            
    except Exception as e:
        print(f"Error generating AI recap: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n--- 3. Formatting Output (Full) ---")
    try:
        from features.daily_recap.formatter import format_daily_recap
        full_output = format_daily_recap(mock_data, ai_recap, mode="full")
        print("--- FULL OUTPUT ---")
        print(full_output)
        
        print("\n--- 4. Formatting Output (Compact) ---")
        compact_output = format_daily_recap(mock_data, ai_recap, mode="compact")
        print("--- COMPACT OUTPUT ---")
        print(compact_output)
        
    except Exception as e:
        print(f"Error formatting recap: {e}")

    print("\n--- 5. Generating Image Output ---")
    try:
        from features.daily_recap.formatter import generate_recap_image
        image_path = await generate_recap_image(mock_data, ai_recap, output_filename="daily_recap_verified.png")
        print(f"✅ Image generated: {image_path}")
    except Exception as e:
        print(f"Error generating image: {e}")

if __name__ == "__main__":
    asyncio.run(verify_flow())
