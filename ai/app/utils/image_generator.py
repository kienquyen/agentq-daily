import os
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    async_playwright = None
    _PLAYWRIGHT_AVAILABLE = False
    logger.error("[image_generator] playwright not installed — run: playwright install chromium")

async def html_to_png(
    html: str, 
    output_path: str, 
    width: int = 480, 
    full_page: bool = True,
    device_scale_factor: float = 2.0
) -> str:
    """
    Renders an HTML string to a PNG image using Playwright.
    
    Args:
        html: The HTML content to render.
        output_path: The file path to save the PNG image.
        width: The viewport width in pixels (default: 480 for mobile-style report).
        full_page: Whether to take a screenshot of the entire page or just the viewport.
        device_scale_factor: The device scale factor (high DPI for better quality).
        
    Returns:
        The path to the generated image.
    """
    if not _PLAYWRIGHT_AVAILABLE:
        logger.error("[html_to_png] Playwright not available — cannot render PNG")
        return None

    try:
        async with async_playwright() as p:
            # --no-sandbox is required in Docker/Railway containers.
            # --disable-dev-shm-usage prevents crashes when /dev/shm is small (default 64MB on Railway).
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            try:
                context = await browser.new_context(
                    viewport={'width': width, 'height': 800},
                    device_scale_factor=device_scale_factor
                )
                page = await context.new_page()

                # domcontentloaded is faster and avoids hanging on Google Fonts network idle.
                # A 500ms delay lets fonts paint before screenshot.
                await page.set_content(html, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(500)

                await page.screenshot(path=output_path, full_page=full_page)
                print(f"[html_to_png] ✅ PNG saved → {output_path}")
                return output_path
            except Exception as e:
                print(f"[html_to_png] ❌ Playwright render failed: {e}")
                logger.error(f"[html_to_png] Playwright render failed: {e}", exc_info=True)
                return None
            finally:
                await browser.close()
    except Exception as e:
        print(f"[html_to_png] ❌ Playwright launch failed: {e}")
        logger.error(f"[html_to_png] Playwright launch failed: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    # Test script
    test_html = "<html><body style='background: #000; color: #fff;'><h1>Test Render</h1><p>AgentQ is rendering this...</p></body></html>"
    asyncio.run(html_to_png(test_html, "test_render.png"))
    print("Test render complete: test_render.png")
