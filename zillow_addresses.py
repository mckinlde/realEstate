# zillow_addresses.py
from pathlib import Path
from urllib.parse import urlparse


def load_urls_from_file(path: str = "urls.txt") -> list[str]:
    urls = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def extract_address_from_url(url: str) -> str:
    """
    Zillow URLs look like:
      https://www.zillow.com/homedetails/3550-Orchi-Rd-Memphis-TN-38108/2062142554_zpid/

    We grab the slug after 'homedetails', split on '-', and assume:
      [street + city tokens..., STATE, ZIP]

    Example:
      '3550-Orchi-Rd-Memphis-TN-38108'
      -> '3550 Orchi Rd Memphis, TN 38108'
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")               # 'homedetails/3550-Orchi-Rd-Memphis-TN-38108/2062142554_zpid'
    parts = path.split("/")                     # ['homedetails', '3550-Orchi-Rd-Memphis-TN-38108', '2062142554_zpid']

    try:
        idx = parts.index("homedetails")
    except ValueError:
        # Not a standard Zillow homedetails URL; just return the URL
        return url

    if len(parts) <= idx + 1:
        return url

    slug = parts[idx + 1]                       # '3550-Orchi-Rd-Memphis-TN-38108'
    tokens = slug.split("-")

    # If we don't have at least street + state + zip, just return a cleaned slug
    if len(tokens) < 3:
        return slug.replace("-", " ")

    # Everything except the last 2 tokens is street+city; then state, zip
    *street_city_tokens, state, zip_code = tokens
    street_city = " ".join(street_city_tokens)

    # Zillow uses "0-" when there's no house number, e.g. "0-Linwood-Rd-..."
    if street_city.startswith("0 "):
        street_city = street_city[2:]

    address = f"{street_city}, {state} {zip_code}"
    return address


def main():
    urls = load_urls_from_file("urls.txt")
    if not urls:
        print("No URLs found in urls.txt")
        return

    for url in urls:
        addr = extract_address_from_url(url)
        print(f"{url}\n  -> {addr}\n")


if __name__ == "__main__":
    main()

