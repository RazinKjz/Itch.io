import aiohttp
import asyncio
import re
import random
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
    """Fetch game data asynchronously with retries, timeouts, and SSL verification disabled."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    ssl_context = aiohttp.TCPConnector(ssl=False)  # ✅ Disable SSL verification

    async with semaphore:
        try:
            async with session.get(url, headers=headers, timeout=15, ssl=False) as response:  # ✅ Ignore SSL errors
                if response.status == 429:
                    print(f"❌ Too many requests (429) on {url}, retrying...")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        return await fetch(session, url, semaphore, attempt + 1)
                    else:
                        print(f"❌ Failed after {MAX_RETRIES} attempts: {url}")
                        return None
                return await response.text()

        except asyncio.TimeoutError:
            print(f"⏳ Timeout on {url} (Attempt {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)  # Retry with backoff
                return await fetch(session, url, semaphore, attempt + 1)
            print(f"❌ Skipping {url} after repeated timeouts.")
            return None

        except aiohttp.ClientError as e:
            print(f"❌ Request failed for {url}: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)
                return await fetch(session, url, semaphore, attempt + 1)
            print(f"❌ Skipping {url} due to persistent errors.")
            return None

    """Fetch game data asynchronously with retries, timeouts, and delays."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    async with semaphore:
        try:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 429:
                    print(f"❌ Too many requests (429) on {url}, retrying...")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        return await fetch(session, url, semaphore, attempt + 1)
                    else:
                        print(f"❌ Failed after {MAX_RETRIES} attempts: {url}")
                        return None
                return await response.text()

        except asyncio.TimeoutError:
            print(f"⏳ Timeout on {url} (Attempt {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)  # Retry with backoff
                return await fetch(session, url, semaphore, attempt + 1)
            print(f"❌ Skipping {url} after repeated timeouts.")
            return None

        except aiohttp.ClientError as e:
            print(f"❌ Request failed for {url}: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)
                return await fetch(session, url, semaphore, attempt + 1)
            print(f"❌ Skipping {url} due to persistent errors.")
            return None

async def scrape_game_info(session, url, semaphore):
    """Extract game details asynchronously, including rating."""
    html = await fetch(session, url, semaphore)
    if not html:
        print(f"⚠️ Skipping {url} due to fetch failure.")
        return None

    try:
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

        # ✅ Extract rating value (fallback to text if `content` is missing)
        rating = 0.0
        rating_tag = soup.find("div", class_="star_value", itemprop="ratingValue")
        if rating_tag:
            try:
                rating = float(rating_tag.get("content", rating_tag.text.strip() or 0))
            except ValueError:
                rating = 0.0

        # ✅ Extract rating count (fallback to text if `content` is missing)
        rating_count = 0
        rating_count_tag = soup.find("span", class_="rating_count", itemprop="ratingCount")
        if rating_count_tag:
            try:
                rating_count = int(rating_count_tag.get("content", rating_count_tag.text.strip() or 0))
            except ValueError:
                rating_count = 0

        print(f"✅ Extracted: {title} | {developer} | {genre} | {platforms} | ${price} | {published_date} | Rating: {rating} ({rating_count} ratings)")

        return (url, title, developer, genre, platforms, price, published_date, description, rating, rating_count, 1)

    except Exception as e:
        print(f"❌ Error parsing game data for {url}: {e}")
        return None

async def scrape_all_games(links, batch_size=50):
    """Scrape and store game details asynchronously, saving every batch_size games."""
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession() as session:
        game_details = []

        for i in range(0, len(links), batch_size):
            batch_links = links[i : i + batch_size]
            
            # ✅ Use `asyncio.create_task()` instead of `asyncio.shield()`
            tasks = [asyncio.create_task(scrape_game_info(session, url, semaphore)) for url in batch_links]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    print(f"❌ Error on game {i + idx + 1}: {batch_links[idx]} - {result}")
                else:
                    game_details.append(result)

            if game_details:
                await save_game_details(game_details)  # Save batch to DB
                print(f"💾 Saved {len(game_details)} games to the database.")
                game_details.clear()  # Clear list after saving

            # ✅ Add a random delay between 1-3 seconds to reduce server load
            sleep_time = random.uniform(1, 3)
            print(f"⏳ Pausing for {sleep_time:.2f} seconds before next batch...")
            await asyncio.sleep(sleep_time)

    print("✅ All game details extracted and saved.")
