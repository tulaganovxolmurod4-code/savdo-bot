import psycopg2
from config import DATABASE_URL

def get_connection():
    """PostgreSQL ma'lumotlar bazasiga ulanishni qaytaradi"""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """Kerakli jadvallarni yaratish (Agar mavjud bo'lmasa)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # E'lonlar jadvali
    cursor.execute("""
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
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Ma'lumotlar bazasi muvaffaqiyatli sozlandi!")

if __name__ == "__main__":
    init_db()
