import sqlite3
from .config import DB_FILE, ORIGINAL_DB

def create_details_table():
    """Ensure 'game_details' table has all required columns in SQLite."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
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
            scraped INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

def get_game_links():
    """Retrieve all game URLs that haven't been scraped yet from 'itch_games.db'."""
    conn = sqlite3.connect(ORIGINAL_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM games")
    all_links = {row[0] for row in cursor.fetchall()}
    conn.close()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM game_details WHERE scraped = 1")
    scraped_links = {row[0] for row in cursor.fetchall()}
    conn.close()

    remaining_links = list(all_links - scraped_links)
    print(f"{len(remaining_links)} games left to scrape.")
    return remaining_links

def save_game_details(game_details): 
    """Save extracted game details into the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    sql = """
        INSERT INTO game_details 
        (url, title, developer, genre, platforms, price, published_date, description, scraped)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            title=excluded.title,
            developer=excluded.developer,
            genre=excluded.genre,
            platforms=excluded.platforms,
            price=excluded.price,
            published_date=excluded.published_date,
            description=excluded.description,
            scraped=excluded.scraped
    """
    cursor.executemany(sql, game_details)
    conn.commit()
    conn.close()
