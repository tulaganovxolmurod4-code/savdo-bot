import threading
import psycopg2
from psycopg2 import pool
from config import DATABASE_URL

_pool = None
_lock = threading.Lock()


def _get_pool():
    """Ulanishlar pulini birinchi marta kerak bo'lganda yaratadi."""
    global _pool
    if _pool is None:
        with _lock:
            if _pool is None:
                _pool = pool.ThreadedConnectionPool(
                    1, 10, DATABASE_URL,
                    sslmode='require',
                    connect_timeout=10,
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5,
                )
    return _pool


class PooledConnection:
    """psycopg2 ulanishini o'raydi: close() ulanishni yopmaydi, pulga qaytaradi."""

    def __init__(self, conn):
        self._conn = conn
        self._released = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        if self._released:
            return
        self._released = True
        p = _get_pool()
        try:
            if self._conn.closed:
                p.putconn(self._conn, close=True)
            else:
                self._conn.rollback()
                p.putconn(self._conn)
        except Exception:
            try:
                p.putconn(self._conn, close=True)
            except Exception:
                pass


def get_connection():
    """Puldan tayyor ulanish beradi. O'lik ulanish chiqsa, yangisini oladi."""
    p = _get_pool()
    for _ in range(3):
        conn = p.getconn()
        try:
            if conn.closed:
                raise psycopg2.OperationalError("closed")
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.rollback()
            return PooledConnection(conn)
        except Exception:
            try:
                p.putconn(conn, close=True)
            except Exception:
                pass
    raise psycopg2.OperationalError("Bazaga ulanib bo'lmadi")


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
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS address TEXT;",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;",
        "ALTER TABLE ads ADD COLUMN IF NOT EXISTS subcategory TEXT;",
    ]:
        cur.execute(sql)
    conn.commit()

    # Indekslar: qidiruv va admin ro'yxatlarini tezlashtiradi.
    # Har biri alohida: biri xato bersa ham bot ishga tushaveradi.
    for sql in [
        "CREATE INDEX IF NOT EXISTS idx_ads_cat_status ON ads (category, status, id DESC);",
        "CREATE INDEX IF NOT EXISTS idx_ads_cat_sub ON ads (category, subcategory, status, id DESC);",
        "CREATE INDEX IF NOT EXISTS idx_ads_user ON ads (user_id);",
        "CREATE INDEX IF NOT EXISTS idx_ads_status ON ads (status);",
        "CREATE INDEX IF NOT EXISTS idx_users_reg ON users (is_registered, created_at DESC);",
    ]:
        try:
            cur.execute(sql)
            conn.commit()
        except Exception:
            conn.rollback()

    cur.close()
    conn.close()


def get_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, full_name, username, phone, is_registered, is_banned, latitude, longitude "
        "FROM users WHERE user_id = %s;",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    keys = ["user_id", "full_name", "username", "phone", "is_registered", "is_banned", "latitude", "longitude"]
    return dict(zip(keys, row))
