import asyncio
import json

from playwright.async_api import async_playwright


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Navigate to the page
        await page.goto("http://localhost:8080/NewGUIforClient.html")

        # Wait for page to load
        await page.wait_for_load_state("networkidle")

        # Add some logs manually to ensure there is content
        await page.evaluate("""
            const logStore = document.getElementById('logContainer');
            if (logStore) {
                const entry = document.createElement('div');
                entry.className = 'log-entry log-info log-entry-new';
                entry.innerHTML = `
                    <div class="log-icon-wrapper">I</div>
                    <div class="log-timestamp">12:00:00</div>
                    <div class="log-level-badge log-level-info">INFO</div>
                    <div class="log-message">Test log message</div>
                `;
                logStore.appendChild(entry);
            }
        """)

        # Take a screenshot of the logs section
        await page.locator("section.logs").screenshot(path="logs_debug.png")

        # Get computed styles for container
        container_styles = await page.evaluate("""
            () => {
                const el = document.getElementById('logContainer');
                const computed = window.getComputedStyle(el);
                return {
                    display: computed.display,
                    height: computed.height,
                    maxHeight: computed.maxHeight,
                    overflowY: computed.overflowY,
                    whiteSpace: computed.whiteSpace,
                    backgroundColor: computed.backgroundColor
                };
            }
        """)

        # Get computed styles for an entry
        entry_styles = await page.evaluate("""
            () => {
                const el = document.querySelector('.log-entry');
                if (el) {
                    const computed = window.getComputedStyle(el);
                    return {
                        display: computed.display,
                        flexDirection: computed.flexDirection,
                        alignItems: computed.alignItems,
                        height: computed.height,
                        opacity: computed.opacity,
                        visibility: computed.visibility
                    };
                }
                return null;
            }
        """)

        print(
            json.dumps({"container": container_styles, "entry": entry_styles}, indent=2)
        )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
