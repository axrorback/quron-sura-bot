import os
import sqlite3
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "bot.db")

# Papkani avtomatik yaratamiz
os.makedirs(DATA_DIR, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS library (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        sura_number INTEGER
    )
    """)

    conn.commit()
    conn.close()


def add_to_library(user_id: int, sura_number: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO library (user_id, sura_number) VALUES (?, ?)", (user_id, sura_number))
    conn.commit()
    conn.close()


def remove_from_library(user_id: int, sura_number: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM library WHERE user_id=? AND sura_number=?", (user_id, sura_number))
    conn.commit()
    conn.close()


def get_library(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT sura_number FROM library WHERE user_id=?", (user_id,))
    result = [row[0] for row in cur.fetchall()]
    conn.close()
    return result
