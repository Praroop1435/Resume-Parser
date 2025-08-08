# auth.py
import sqlite3
import bcrypt

DB_NAME = "users.db"

def create_user(username, password, role="user"):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hashed, role)  # Use the role
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT password, role FROM users WHERE username = ?", (username,))
    data = cursor.fetchone()
    conn.close()

    if data and bcrypt.checkpw(password.encode(), data[0].encode()):
        return True, data[1]  # is_valid, role
    return False, None
