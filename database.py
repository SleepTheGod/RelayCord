import aiosqlite
from cryptography.fernet import Fernet
import config

fernet = Fernet(config.DATABASE_ENCRYPTION_KEY)

def encrypt_number(number):
    return fernet.encrypt(number.encode()).decode()

def decrypt_number(encrypted):
    return fernet.decrypt(encrypted.encode()).decode()

async def init_db():
    async with aiosqlite.connect("calls.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_sid TEXT UNIQUE,
                channel_id TEXT,
                user_id TEXT,
                to_number TEXT,
                from_number TEXT,
                start_time DATETIME,
                end_time DATETIME,
                duration INTEGER
            )
        """)
        await db.commit()

async def log_call_start(call_sid, channel_id, user_id, to_number, from_number):
    encrypted_to = encrypt_number(to_number)
    encrypted_from = encrypt_number(from_number)
    async with aiosqlite.connect("calls.db") as db:
        await db.execute(
            "INSERT INTO calls (call_sid, channel_id, user_id, to_number, from_number, start_time) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (call_sid, channel_id, user_id, encrypted_to, encrypted_from)
        )
        await db.commit()

async def log_call_end(call_sid):
    async with aiosqlite.connect("calls.db") as db:
        await db.execute(
            "UPDATE calls SET end_time = CURRENT_TIMESTAMP, duration = (strftime('%s', 'now') - strftime('%s', start_time)) WHERE call_sid = ?",
            (call_sid,)
        )
        await db.commit()
