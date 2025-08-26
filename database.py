# database.py

import aiosqlite

DB_NAME = "users.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                tg_id INTEGER UNIQUE,
                birth_date TEXT,
                zodiac_sign TEXT,
                subscribed BOOLEAN DEFAULT FALSE,
                birth_time TEXT,
                birth_place TEXT
            )
        """)
        await db.commit()

async def save_user(tg_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (tg_id) VALUES (?)
        """, (tg_id,))
        await db.commit()

async def update_user_data(tg_id, birth_date, zodiac_sign, birth_time=None, birth_place=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users 
            SET birth_date = ?, zodiac_sign = ?, birth_time = ?, birth_place = ? 
            WHERE tg_id = ?
        """, (birth_date, zodiac_sign, birth_time, birth_place, tg_id))
        await db.commit()

async def subscribe_user(tg_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users SET subscribed = TRUE WHERE tg_id = ?
        """, (tg_id,))
        await db.commit()

async def unsubscribe_user(tg_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users SET subscribed = FALSE WHERE tg_id = ?
        """, (tg_id,))
        await db.commit()

async def get_subscribed_users():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT tg_id, zodiac_sign FROM users WHERE subscribed = TRUE AND zodiac_sign IS NOT NULL") as cursor:
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]

async def get_user_data(tg_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT birth_date, zodiac_sign, birth_time, birth_place FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return row