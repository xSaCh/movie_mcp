import sqlite3

DATABASE_URL = "./mcp.db"


def create_tables():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Film (
            film_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            release_date DATE,
            type TEXT CHECK(type IN ('movie', 'series')),
            status TEXT CHECK(status IN ('PlanToWatch', 'Watching', 'Watched', 'Dropped', 'OnHold')),
            watched_date DATE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Meta (
            meta_id INTEGER PRIMARY KEY AUTOINCREMENT,
            film_id INTEGER,
            imdb_id TEXT,
            runtime INTEGER,
            plot TEXT,
            rating REAL,
            poster_url TEXT,
            FOREIGN KEY (film_id) REFERENCES Film (film_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Genre (
            genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
            film_id INTEGER,
            name TEXT NOT NULL,
            FOREIGN KEY (film_id) REFERENCES Film (film_id)
        )
    """
    )

    conn.commit()
    conn.close()


create_tables()


def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
