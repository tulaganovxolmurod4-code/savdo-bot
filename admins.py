import os

from database import get_connection
from settings import NOTIFY_HELPERS

# Bosh admin: Render Environment'dagi ADMIN_ID. Yordamchilar bazada saqlanadi.
ADMIN_ID = int(os.environ.get("ADMIN_ID") or 0)

_helpers = set()


def _run(sql, params=(), fetch=False):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    finally:
        cur.close()
        conn.close()


def load_helpers():
    """Bot ishga tushganda yordamchi adminlarni bazadan xotiraga yuklaydi."""
    global _helpers
    rows = _run("SELECT user_id FROM admins;", fetch=True)
    _helpers = {r[0] for r in rows}


def is_super(user_id):
    return bool(ADMIN_ID) and user_id == ADMIN_ID


def is_admin(user_id):
    return is_super(user_id) or user_id in _helpers


def helper_ids():
    return sorted(_helpers)


def notify_ids():
    """Shikoyat xabarlari yuboriladigan adminlar."""
    ids = [ADMIN_ID] if ADMIN_ID else []
    if NOTIFY_HELPERS:
        ids += [h for h in sorted(_helpers) if h != ADMIN_ID]
    return ids


def add_helper(user_id, added_by):
    _run(
        "INSERT INTO admins (user_id, added_by) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING;",
        (user_id, added_by),
    )
    _helpers.add(user_id)


def remove_helper(user_id):
    _run("DELETE FROM admins WHERE user_id = %s;", (user_id,))
    _helpers.discard(user_id)
