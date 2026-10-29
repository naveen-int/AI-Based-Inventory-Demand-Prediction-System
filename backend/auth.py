import os
import sqlite3
from functools import wraps
from pathlib import Path
from flask import Blueprint, current_app, g, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash

AUTH = Blueprint("auth", __name__, url_prefix="/api/auth")
DB_PATH = Path(__file__).resolve().parent / "inventory.db"


def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_auth(app):
    app.config.setdefault("PERMANENT_SESSION_LIFETIME", 60 * 60 * 8)
    with connect_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'staff' CHECK(role IN ('admin','staff')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        db.commit()
    app.register_blueprint(AUTH)


def load_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with connect_db() as db:
        row = db.execute("SELECT id,name,email,role FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = load_user()
        if not user:
            session.clear()
            return jsonify({"error": "Please log in to continue."}), 401
        g.current_user = user
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.current_user["role"] not in roles:
                return jsonify({"error": "You do not have permission to access this feature."}), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator


@AUTH.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    confirm = str(data.get("confirmPassword", ""))
    if not name or not email or not password:
        return jsonify({"error": "Please fill in all required fields."}), 400
    if len(password) < 10:
        return jsonify({"error": "Password must contain at least 10 characters."}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match."}), 400
    try:
        with connect_db() as db:
            db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'staff')",
                       (name, email, generate_password_hash(password)))
            db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "An account with this email already exists."}), 409
    return jsonify({"message": "Staff account created successfully. Please log in."}), 201


@AUTH.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    with connect_db() as db:
        row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401
    session.clear()
    session.permanent = True
    session["user_id"] = row["id"]
    return jsonify({"message": "Login successful.", "user": {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"]}})


@AUTH.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out."})


@AUTH.get("/me")
def me():
    user = load_user()
    if not user:
        return jsonify({"error": "Not logged in."}), 401
    return jsonify({"user": user})
