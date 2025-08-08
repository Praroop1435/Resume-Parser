# db_setup.py
import sqlite3
import bcrypt

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

# Add admin with hashed password
admin_password = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
               ("admin", admin_password, "admin"))

conn.commit()
conn.close()
