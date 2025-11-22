"""Check page height and capture stats grid."""
from playwright.sync_api import sync_playwright


def main():
    target_url = "http://localhost:9091/NewGUIforClient.html"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})

        print(f"Navigating to {target_url}...")
        response = page.goto(target_url, wait_until='networkidle', timeout=30000)
        print(f"Page loaded with status: {response.status}")

        page.wait_for_timeout(2000)

        # Check page dimensions
        page_height = page.evaluate("document.body.scrollHeight")
        viewport_height = page.evaluate("window.innerHeight")
        print(f"\nPage height: {page_height}px")
        print(f"Viewport height: {viewport_height}px")

        # Check if stats grid exists
        stats_grid = page.locator("#statsGrid")
        if stats_grid.count() > 0:
            print("\n✅ Stats grid found!")
            # Scroll to stats grid
            page.evaluate("document.getElementById('statsGrid').scrollIntoView({behavior: 'smooth', block: 'center'})")
            page.wait_for_timeout(1000)
            page.screenshot(path='web_gui_stats.png', full_page=False)
            print("Saved: web_gui_stats.png")
        else:
            print("\n❌ Stats grid not found!")

        # Check for action buttons
        actions_div = page.locator(".actions")
        if actions_div.count() > 0:
            print(f"✅ Actions div found: {actions_div.count()}")
            button_count = page.locator(".actions button").count()
            print(f"   Action buttons: {button_count}")

            # Get button details
            for i in range(button_count):
                btn = page.locator(".actions button").nth(i)
                text = btn.text_content()
                classes = btn.get_attribute("class") or ""
                print(f"   - Button {i+1}: '{text}' (classes: {classes})")

        browser.close()


if __name__ == "__main__":
    main()
