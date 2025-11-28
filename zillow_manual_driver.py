import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


DEFAULT_URL = "https://www.homedepot.com/"


def create_driver() -> webdriver.Chrome:
    chrome_options = Options()

    # Visible window (not headless) so you can interact manually
    chrome_options.add_argument("--start-maximized")

    # Optional: make it look more like a regular browser session
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # If you want to reuse a real Chrome profile (helps with logins / bot checks),
    # set this to your profile directory path:
    # chrome_options.add_argument(
    #     r'--user-data-dir=C:\Users\YOURNAME\AppData\Local\Google\Chrome\User Data'
    # )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options,
    )
    return driver


def main():
    # If a URL is passed as an argument, open that; else open Zillow home
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    driver = create_driver()
    driver.get(url)

    print(f"Opened: {url}")
    print("You can now interact with Zillow in the browser window.")
    print("When you're done, return here and press Enter to close the browser...")

    try:
        input()
    except KeyboardInterrupt:
        pass
    finally:
        print("Closing browser...")
        # small delay just so you can see the message
        time.sleep(1)
        driver.quit()


if __name__ == "__main__":
    main()
