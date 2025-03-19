import sys
import asyncio
import subprocess
from itch_main.database import create_details_table, get_game_links, get_final_game_links
from itch_main.scraper import scrape_all_games

async def main():
    """Main function to run the scraper based on user input."""
    if len(sys.argv) < 2:
        print("❌ Missing arguments! Use one of the following:")
        print("  python -m itch_main.main pages <start_page> <end_page>  # Scrape Itch.io pages"
              "\n  python -m itch_main.main database  # Scrape from itch_games.db"
              "\n  python -m itch_main.main final  # Scrape from itch_games_final.db"
              "\n  python -m itch_main.main all <start_page> <end_page>  # Run both steps")
        sys.exit(1)

    command = sys.argv[1].lower()

    # ✅ Ensure the database table exists before any queries
    print("🔹 Ensuring `itch_games_final.db` has the correct structure...")
    await create_details_table()

    if command == "pages":
        if len(sys.argv) != 4:
            print("❌ Invalid usage for pages! Use: python -m itch_main.main pages <start_page> <end_page>")
            sys.exit(1)

        start_page = int(sys.argv[2])
        end_page = int(sys.argv[3])
        print(f"🔹 Scraping Itch.io pages {start_page} to {end_page}...")

        subprocess.run(["python", "linkextracttt.py", str(start_page), str(end_page)], check=True)
    
    elif command == "database":
        print("🔹 Scraping games from `itch_games.db`...")
        links = await get_game_links()
        if not links:
            print("✅ All games are already scraped.")
            return
        
        await scrape_all_games(links)

    elif command == "final":
        print("🔹 Scraping games from `itch_games_final.db`...")
        links = await get_final_game_links()
        if not links:
            print("✅ No new games to scrape in `itch_games_final.db`.")
            return
        
        await scrape_all_games(links)

    elif command == "all":
        if len(sys.argv) != 4:
            print("❌ Invalid usage for all! Use: python -m itch_main.main all <start_page> <end_page>")
            sys.exit(1)

        start_page = int(sys.argv[2])
        end_page = int(sys.argv[3])

        print(f"🔹 Scraping Itch.io pages {start_page} to {end_page}...")
        subprocess.run(["python", "linkextracttt.py", str(start_page), str(end_page)], check=True)

        print("🔹 Scraping games from `itch_games.db`...")
        links = await get_game_links()
        if not links:
            print("✅ All games are already scraped.")
            return
        
        await scrape_all_games(links)

    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
