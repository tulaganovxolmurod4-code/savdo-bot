import psycopg2
from config import DATABASE_URL


def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id),
            category TEXT,
            title TEXT,
            description TEXT,
            price TEXT,
            photo_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Eski jadvallarni yangilash
    for sql in [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_registered BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS photo_id TEXT;",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS sold_at TIMESTAMP;",
    ]:
        cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()


def get_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, full_name, username, phone, is_registered, is_banned FROM users WHERE user_id = %s;",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    keys = ["user_id", "full_name", "username", "phone", "is_registered", "is_banned"]
    return dict(zip(keys, row))
import psycopg2
from config import DATABASE_URL


def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id),
            category TEXT,
            title TEXT,
            description TEXT,
            price TEXT,
            photo_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Eski jadvallarni yangilash
    for sql in [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_registered BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS photo_id TEXT;",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS sold_at TIMESTAMP;",
    ]:
        cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()


def get_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, full_name, username, phone, is_registered, is_banned FROM users WHERE user_id = %s;",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    keys = ["user_id", "full_name", "username", "phone", "is_registered", "is_banned"]
    return dict(zip(keys, row))

