import asyncio
import json
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

MAP_URL = "https://www.arcgis.com/apps/View/index.html?appid=b5118cb926c64ebeac59c8d0b01f6e45"
ADDRESS = "133 18th Avenue Northwest, Center Point, AL 35215"
OUTPUT_FILE = "parcel_details.json"


def parse_property_details_html(html: str) -> dict:
    """
    Parse the Additional Property Information HTML into a JSON-able dict.

    Structure:
      {
        "UNNAMED_SECTION": {"rows": [ { "PARCEL #": "...", "OWNER": "..." }, ...]},
        "SUMMARY": {"rows": [ { ... }, ...]},
        "ASSESSMENT": {"rows": [ ...]},
        "VALUE": {"rows": [ ...]},
        "Assesment Override:": {"rows": [ ...]},
        "TAX INFO": {"rows": [ ...]},
        "DEEDS": {"rows": [ ...]},
        "PAYMENT INFO": {"rows": [ ...]}
      }
    """
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    for fs in soup.find_all("fieldset"):
        legend = fs.find("legend")
        title = legend.get_text(" ", strip=True) if legend else "UNNAMED_SECTION"
        rows = []

        for tr in fs.find_all("tr"):
            tds = tr.find_all("td")
            if not tds:
                continue

            cells = [td.get_text(" ", strip=True) for td in tds]
            if not any(cells):
                continue

            if len(cells) % 2 == 0:
                # label/value pairs
                row_obj = {}
                for i in range(0, len(cells), 2):
                    key = cells[i].strip().rstrip(":").strip()
                    val = cells[i + 1].strip()

                    if not key and not val:
                        continue
                    if not key:
                        key = f"__col_{i // 2}__"

                    if key in row_obj:
                        existing = row_obj[key]
                        if isinstance(existing, list):
                            existing.append(val)
                        else:
                            row_obj[key] = [existing, val]
                    else:
                        row_obj[key] = val

                if row_obj:
                    rows.append(row_obj)
            else:
                rows.append({"__raw__": cells})

        if title in result:
            result[title]["rows"].extend(rows)
        else:
            result[title] = {"rows": rows}

    return result


async def open_parcel_popup(page, address: str):
    """
    1. Type the address into #search_input and press Enter.
    2. Wait for the map to recenter.
    3. Click the map at center and tiny pixel offsets (including 5px offset)
       until the popup appears.
    4. Return a locator for the 'additional Property Information' link.
    """
    popup_selector = ".esriViewPopup a[href*='CA_PropertyTaxParcelInfo.aspx']"

    await page.wait_for_selector("#search_input")

    search_input = page.locator("#search_input")
    await search_input.click()
    await search_input.fill(address)
    await search_input.press("Enter")

    await page.wait_for_timeout(4000)

    # If popup appears just from the search
    try:
        await page.wait_for_selector(popup_selector, timeout=3000)
        return page.locator(popup_selector).first
    except PlaywrightTimeoutError:
        pass

    map_locator = page.locator("#mapDiv_root")
    await map_locator.wait_for()
    box = await map_locator.bounding_box()
    if not box:
        raise RuntimeError("Could not get bounding box for mapDiv_root")

    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2

    pixel_offsets = [
        (0, 0),
        (5, 0),   # tuned working offset
        (-5, 0),
        (0, 5),
        (0, -5),
    ]

    for dx, dy in pixel_offsets:
        click_x = center_x + dx
        click_y = center_y + dy
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
            headless=False,
            slow_mo=75,
        )
        context = await browser.new_context()
        page = await context.new_page()

        # Open viewer
        await page.goto(MAP_URL, wait_until="domcontentloaded")

        # Accept disclaimer if present
        try:
            await page.wait_for_selector("#closeOverlay", timeout=8000)
            await page.click("#closeOverlay")
            await page.wait_for_timeout(500)
        except PlaywrightTimeoutError:
            pass

        # Search + popup
        popup_link = await open_parcel_popup(page, ADDRESS)

        # Click "additional Property Information" → new tab
        async with context.expect_page() as new_page_info:
            await popup_link.click()
        details_page = await new_page_info.value
        await details_page.wait_for_load_state("domcontentloaded")
        await details_page.wait_for_timeout(2000)

        # Parse all frames & merge sections
        combined_sections = {}
        for frame in details_page.frames:
            try:
                html = await frame.content()
            except Exception:
                continue
            frame_sections = parse_property_details_html(html)
            for title, info in frame_sections.items():
                if title in combined_sections:
                    combined_sections[title]["rows"].extend(info["rows"])
                else:
                    combined_sections[title] = {"rows": list(info["rows"])}

        # Save to JSON file instead of printing
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(combined_sections, f, indent=2, ensure_ascii=False)

        print(f"Saved parcel details to {OUTPUT_FILE}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
