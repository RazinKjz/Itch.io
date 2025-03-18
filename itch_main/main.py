import subprocess
import asyncio
from itch_main.database import get_game_links
from itch_main.scraper import scrape_all_games

async def main():
    print("🔹 Running linkextracttt.py to gather game links...")
    
    # Run linkextracttt.py before scraping
    subprocess.run(["python", "linkextracttt.py"], check=True)

    # Now retrieve the game links
    links = get_game_links()
    
    if not links:
        print("❌ No game links found. Exiting...")
        return

    print(f"✅ Found {len(links)} game links. Starting full scrape...")
    await scrape_all_games(links)

if __name__ == "__main__":
    asyncio.run(main())
