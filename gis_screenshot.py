import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

MAP_URL = "https://www.arcgis.com/apps/View/index.html?appid=b5118cb926c64ebeac59c8d0b01f6e45"
ADDRESS = "133 18th Avenue Northwest, Center Point, AL 35215"
OUTPUT_FILE = "parcel_details.png"


async def open_parcel_popup(page, address: str):
    """
    1. Type the address into #search_input and press Enter.
    2. Wait for the map to recenter.
    3. Click the map at center and tiny pixel offsets (including 5px offset)
       until the popup appears.
    4. Return a locator for the 'additional Property Information' link.
    """
    popup_selector = ".esriViewPopup a[href*='CA_PropertyTaxParcelInfo.aspx']"

    # Wait for the search input
    await page.wait_for_selector("#search_input")

    search_input = page.locator("#search_input")
    await search_input.click()
    await search_input.fill(address)
    await search_input.press("Enter")

    # Give the map some time to recenter / redraw
    await page.wait_for_timeout(4000)

    # If popup appears just from the search, grab it
    try:
        await page.wait_for_selector(popup_selector, timeout=3000)
        return page.locator(popup_selector).first
    except PlaywrightTimeoutError:
        pass

    # Otherwise, click near the center with tiny offsets
    map_locator = page.locator("#mapDiv_root")
    await map_locator.wait_for()
    box = await map_locator.bounding_box()
    if not box:
        raise RuntimeError("Could not get bounding box for mapDiv_root")

    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2

    # Tuned offset and a few neighbors (5px dead-zone workaround)
    pixel_offsets = [
        (0, 0),
        (5, 0),   # your tuned working offset
        (-5, 0),
        (0, 5),
        (0, -5),
    ]

    for dx, dy in pixel_offsets:
        click_x = center_x + dx
        click_y = center_y + dy
        # Uncomment to debug:
        # print(f"Clicking map at ({click_x}, {click_y}) offset ({dx}, {dy})")
        await page.mouse.click(click_x, click_y)
        try:
            await page.wait_for_selector(popup_selector, timeout=3000)
            return page.locator(popup_selector).first
        except PlaywrightTimeoutError:
            continue

    raise RuntimeError("Parcel popup link did not appear after search and tiny offset clicks.")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,   # set True once you're happy with it
            slow_mo=75,       # small delay to keep the UI sane
        )
        context = await browser.new_context()
        page = await context.new_page()

        # 1. Open the ArcGIS viewer
        await page.goto(MAP_URL, wait_until="domcontentloaded")

        # 1a. Accept disclaimer if it’s there
        try:
            await page.wait_for_selector("#closeOverlay", timeout=8000)
            await page.click("#closeOverlay")
            await page.wait_for_timeout(500)
        except PlaywrightTimeoutError:
            # no overlay, carry on
            pass

        # 2–3. Search and open the parcel popup
        popup_link = await open_parcel_popup(page, ADDRESS)

        # 4. Click the "additional Property Information" link and capture the new tab
        async with context.expect_page() as new_page_info:
            await popup_link.click()
        details_page = await new_page_info.value
        await details_page.wait_for_load_state("domcontentloaded")
        # Give iframes / styles a moment to settle
        await details_page.wait_for_timeout(2000)

        # 5. Screenshot the rendered page
        await details_page.screenshot(path=OUTPUT_FILE, full_page=True)
        print(f"Saved parcel details screenshot to {OUTPUT_FILE}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
