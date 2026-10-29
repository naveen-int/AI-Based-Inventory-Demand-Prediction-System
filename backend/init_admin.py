
import sqlite3
import getpass
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventory.db"


def main():
    db = sqlite3.connect(DB_PATH)

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'staff',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

    existing = db.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin'"
    ).fetchone()[0]

    if existing:
        print("An Admin account already exists.")
        db.close()
        return

    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm password: ")

    if not name or not email:
        print("Name and email are required.")
        db.close()
        return

    if len(password) < 10:
        print("Password must contain at least 10 characters.")
        db.close()
        return

    if password != confirm:
        print("Passwords do not match.")
        db.close()
        return

    try:
        db.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (?, ?, ?, 'admin')
            """,
            (name, email, generate_password_hash(password))
        )
        db.commit()
        print("Admin account created successfully!")

    except sqlite3.IntegrityError:
        print("That email is already registered.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
