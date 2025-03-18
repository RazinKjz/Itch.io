import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
from datetime import datetime
from .config import MAX_RETRIES, CONCURRENT_REQUESTS
from .database import save_game_details

def format_date(date_text):
    """Convert date to 'YYYY-MM-DD' format, removing time information."""
    try:
        return datetime.strptime(date_text, "%d %B %Y").strftime("%Y-%m-%d")
    except ValueError:
        return "Unknown"

def extract_price(price_text):
    """Extract numeric price value (e.g., '2.99' from '$2.99 USD') or return 0 for free games."""
    price_match = re.search(r"(\d+(\.\d+)?)", price_text)
    return float(price_match.group(1)) if price_match else 0.00

async def fetch(session, url, semaphore, attempt=1):
    """Fetch game data asynchronously with retries."""
    async with semaphore:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 429:
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        return await fetch(session, url, semaphore, attempt + 1)
                    else:
                        print(f"Failed after {MAX_RETRIES} attempts: {url}")
                        return None
                return await response.text()
        except Exception as e:
            print(f"Error scraping {url} (Attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)
                return await fetch(session, url, semaphore, attempt + 1)
            return None

async def scrape_game_info(session, url, semaphore):
    """Extract game details asynchronously."""
    html = await fetch(session, url, semaphore)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    def get_info(label):
        tag = soup.find("td", string=label)
        return tag.find_next_sibling("td").text.strip() if tag else "Unknown"

    title = get_info("Title")  
    if title == "Unknown":
        title_tag = soup.find("h1", class_="game_title")
        title = title_tag.text.strip() if title_tag else "Unknown"

    developer = get_info("Author")  
    genre = get_info("Genre")
    platforms = get_info("Platforms")

    published_date = "Unknown"
    published_tag = soup.find("abbr", title=True)
    if published_tag:
        published_date = published_tag["title"].split(" @")[0]

    description = get_info("Description")
    if description == "Unknown":
        meta_description = soup.find("meta", {"name": "description"})
        description = meta_description["content"].strip() if meta_description else "No description available"

    price = 0.00
    price_tag = soup.select_one("span[itemprop='price'].dollars")
    if price_tag:
        price = extract_price(price_tag.text.strip())

    print(f"Extracted: {title} | {developer} | {genre} | {platforms} | ${price} | {published_date}")

    return (url, title, developer, genre, platforms, price, published_date, description, 1)

async def scrape_all_games(links):
    """Scrape and store game details asynchronously."""
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_game_info(session, url, semaphore) for url in links]
        game_details = await asyncio.gather(*tasks)

    game_details = list(filter(None, game_details))
    save_game_details(game_details)
    print("All game details extracted and saved.")
