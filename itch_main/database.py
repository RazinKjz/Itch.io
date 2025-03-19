import aiosqlite
from .config import DB_FILE, ORIGINAL_DB

async def create_details_table():
    """Ensure 'game_details' table exists in `itch_games_final.db` before scraping."""
    async with aiosqlite.connect(DB_FILE) as conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                developer TEXT,
                genre TEXT,
                platforms TEXT,
                price REAL,
                published_date TEXT,
                description TEXT,
                rating REAL DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                scraped INTEGER DEFAULT 0
            )
        """)
        await conn.commit()

async def get_game_links():
    """Retrieve all game URLs that haven't been scraped yet from `itch_games.db`."""
    async with aiosqlite.connect(ORIGINAL_DB) as conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT url FROM games")
        all_links = {row[0] for row in await cursor.fetchall()}

    async with aiosqlite.connect(DB_FILE) as conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT url FROM game_details WHERE scraped = 1")
        scraped_links = {row[0] for row in await cursor.fetchall()}

    remaining_links = list(all_links - scraped_links)
    print(f"{len(remaining_links)} games left to scrape.")
    return remaining_links

async def get_final_game_links():
    """Retrieve all game URLs that haven't been re-scraped yet from `itch_games_final.db`."""
    async with aiosqlite.connect(DB_FILE) as conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT url FROM game_details WHERE scraped = 0")  # ✅ Fetch only unprocessed games
        final_links = [row[0] for row in await cursor.fetchall()]

    print(f"{len(final_links)} games left to re-scrape in `itch_games_final.db`.")
    return final_links

async def save_game_details(game_details):
    """Save extracted game details into `itch_games_final.db` asynchronously, preventing None values."""
    async with aiosqlite.connect(DB_FILE) as conn:
        cursor = await conn.cursor()
        sql = """
            INSERT INTO game_details 
            (url, title, developer, genre, platforms, price, published_date, description, rating, rating_count, scraped)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title,
                developer=excluded.developer,
                genre=excluded.genre,
                platforms=excluded.platforms,
                price=excluded.price,
                published_date=excluded.published_date,
                description=excluded.description,
                rating=excluded.rating,
                rating_count=excluded.rating_count,
                scraped=excluded.scraped
        """
        # ✅ Ensure no `None` values before inserting into the database
        cleaned_data = [
            (
                url,
                title or "Unknown", 
                developer or "Unknown",
                genre or "Unknown",
                platforms or "Unknown",
                price if price is not None else 0.0, 
                published_date or "Unknown",
                description or "No description available",
                rating if rating is not None else 0.0, 
                rating_count if rating_count is not None else 0, 
                1
            )
            for (url, title, developer, genre, platforms, price, published_date, description, rating, rating_count, _) in game_details
        ]

        await cursor.executemany(sql, cleaned_data)
        await conn.commit()
    """Save extracted game details into `itch_games_final.db` asynchronously."""
    async with aiosqlite.connect(DB_FILE) as conn:
        cursor = await conn.cursor()
        sql = """
            INSERT INTO game_details 
            (url, title, developer, genre, platforms, price, published_date, description, rating, rating_count, scraped)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title,
                developer=excluded.developer,
                genre=excluded.genre,
                platforms=excluded.platforms,
                price=excluded.price,
                published_date=excluded.published_date,
                description=excluded.description,
                rating=excluded.rating,
                rating_count=excluded.rating_count,
                scraped=excluded.scraped
        """
        await cursor.executemany(sql, game_details)
        await conn.commit()
