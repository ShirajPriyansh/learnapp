import sqlite3
from datetime import datetime
from getpass import getpass

from werkzeug.security import generate_password_hash

from app import DB_PATH, init_db


def main():
    init_db()

    username = input("Admin username: ").strip()
    if not username:
        print("Username is required.")
        return

    password = getpass("Admin password: ")
    confirm_password = getpass("Confirm password: ")
    if not password:
        print("Password is required.")
        return
    if password != confirm_password:
        print("Passwords do not match.")
        return

    password_hash = generate_password_hash(password)
    conn = sqlite3.connect(DB_PATH)
    try:
        existing = conn.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE users SET password_hash = ?, is_admin = 1 WHERE username = ?",
                (password_hash, username)
            )
            action = "Updated"
        else:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at, is_admin) VALUES (?, ?, ?, 1)",
                (username, password_hash, datetime.utcnow().isoformat())
            )
            action = "Created"

        conn.commit()
        print(f"{action} admin user: {username}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
