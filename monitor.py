import json
import os
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import requests

# --- Configuration ---
BASE_URL = "https://www.dndbeyond.com/changelog"
STATE_FILE = "seen_quick_links.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Months to filter out
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# --- Helper functions ---
def load_seen_links():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen_links(links):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(links), f, indent=2, ensure_ascii=False)


def send_to_discord(message):
    if not WEBHOOK_URL:
        print("No Discord webhook set. Skipping sending.")
        return

    payload = {"content": message[:1900]}  # limit to Discord max length
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10, verify=False)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending to Discord: {e}")


# --- Scraping function ---
def scrape_quick_menu_links():
    links = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)

        # Wait for at least one element with the target class
        page.wait_for_selector(".quick-menu-item-link", timeout=30000)

        elements = page.query_selector_all(".quick-menu-item-link")
        for el in elements:
            text = el.inner_text().strip()
            href = el.get_attribute("href") or ""

            # Skip links that contain month names
            if any(month in text for month in MONTHS):
                continue

            full_url = urljoin(BASE_URL, href)
            links.append({"text": text, "url": full_url})

        browser.close()

    return links


# --- Main script ---
def main():
    seen_links = load_seen_links()
    scraped_links = scrape_quick_menu_links()

    new_links = []

    for link in scraped_links:
        key = link["url"]
        if key not in seen_links:
            new_links.append(link)
            seen_links.add(key)

    if new_links:
        print(f"🆕 Found {len(new_links)} new changelog links!\n")
        for link in new_links:
            message = (
                f"**New D&D Beyond Changelog Entry**\n"
                f"{link['text']}\n"
                f"[View Change]({link['url']})"
            )
            print(message)
            send_to_discord(message)
    else:
        print("No new changelog links found.")

    save_seen_links(seen_links)


if __name__ == "__main__":
    main()
