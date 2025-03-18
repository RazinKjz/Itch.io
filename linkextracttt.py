import requests
from bs4 import BeautifulSoup
import sqlite3

# SQLite Database File (Stored Locally)
DB_FILE = "itch_games.db"

def create_table():
    """Create the games table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            url TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def save_to_db(game_data):
    """Save game data to SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Insert data into the table (ignore duplicates)
    sql = "INSERT OR IGNORE INTO games (name, url) VALUES (?, ?)"
    cursor.executemany(sql, game_data)
    conn.commit()

    print(f"Saved {len(game_data)} games to the database.")
    cursor.close()
    conn.close()

def GetPage(number):
    """Fetch game data from Itch.io and save it to SQLite."""
    url = f"https://itch.io/games?page={number}&format=json"
    response = requests.get(url)
    data = response.json()

    content = data.get("content", "")
    soup = BeautifulSoup(content, "html.parser")

    games = [(game.text.strip(), game["href"]) for game in soup.find_all("a", class_="title game_link")]

    print(f"Found {len(games)} games on page {number}")
    save_to_db(games)

# Create table before scraping
create_table()

# Scrape and save multiple pages
for page in range(1, 9):  # Change range to scrape more pages
    GetPage(page)

print("Database saved as 'itch_games.db'")
