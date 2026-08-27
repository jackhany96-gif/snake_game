"""Discord OAuth + global Free Mode leaderboard backend for the Snake game.

Run with:
  set DISCORD_CLIENT_ID=...
  set DISCORD_CLIENT_SECRET=...
  set GAME_URL=http://localhost:5000/game
  python auth_server.py

For production, use HTTPS and a real database/host.
"""
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlencode

import requests
from flask import Flask, redirect, request, session, jsonify, send_from_directory
from flask_cors import CORS

BASE = Path(__file__).resolve().parent
DB = BASE / "snake_users.db"
GAME_DIR = BASE / "build" / "web"

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
GAME_URL = os.getenv("GAME_URL", "https://jackhany96-gif.github.io/snake_game/")
REDIRECT_URI = os.getenv(
    "DISCORD_REDIRECT_URI",
    "https://snakegame12.pythonanywhere.com/callback",
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=os.getenv("SESSION_COOKIE_SAMESITE", "None"),
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "1") == "1",
)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://jackhany96-gif.github.io",
).split(",")
CORS(app, supports_credentials=True, origins=[origin.strip() for origin in ALLOWED_ORIGINS])


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        discord_id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        email TEXT,
        best_score INTEGER NOT NULL DEFAULT 0,
        achievements TEXT NOT NULL DEFAULT '[]',
        games INTEGER NOT NULL DEFAULT 0
    )""")
    conn.commit()
    return conn


@app.get("/login")
def login():
    if not CLIENT_ID or not CLIENT_SECRET:
        return "Set DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET first.", 500
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "identify email",
        "state": "snake-game",
    }
    return redirect("https://discord.com/oauth2/authorize?" + urlencode(params))


@app.get("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Discord login was cancelled or failed.", 400

    token = requests.post(
        "https://discord.com/api/v10/oauth2/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=15,
    )
    token.raise_for_status()
    access_token = token.json()["access_token"]

    user = requests.get(
        "https://discord.com/api/v10/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    user.raise_for_status()
    data = user.json()

    discord_id = data["id"]
    username = data.get("username") or data.get("global_name") or "DiscordUser"
    email = data.get("email")

    conn = db()
    conn.execute(
        "INSERT INTO users(discord_id, username, email) VALUES(?,?,?) "
        "ON CONFLICT(discord_id) DO UPDATE SET username=excluded.username, email=excluded.email",
        (discord_id, username, email),
    )
    conn.commit()
    conn.close()

    session["discord_id"] = discord_id
    # Main.py reads these after the server has authenticated the user.
    return redirect(GAME_URL + "?discord_username=" + requests.utils.quote(username) + "&discord_user_id=" + discord_id)


@app.get("/api/me")
def me():
    discord_id = session.get("discord_id")
    if not discord_id:
        return jsonify({"logged_in": False}), 401
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE discord_id=?", (discord_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"logged_in": False}), 401
    return jsonify({
        "logged_in": True,
        "discord_id": row["discord_id"],
        "username": row["username"],
        "best_score": row["best_score"],
        "achievements": __import__("json").loads(row["achievements"]),
        "games": row["games"],
    })


@app.get("/api/leaderboard")
def leaderboard():
    conn = db()
    rows = conn.execute(
        "SELECT username, best_score, achievements FROM users ORDER BY best_score DESC, username ASC"
    ).fetchall()
    conn.close()
    import json
    return jsonify([
        {"name": r["username"], "score": r["best_score"], "achievements": json.loads(r["achievements"])}
        for r in rows
    ])


@app.post("/api/score")
def score():
    discord_id = session.get("discord_id")
    if not discord_id:
        return jsonify({"error": "Discord login required"}), 401
    payload = request.get_json(silent=True) or {}
    score_value = int(payload.get("score", 0))
    achievements = list(payload.get("achievements", []))[:100]
    if score_value < 0 or score_value > 1000000:
        return jsonify({"error": "Invalid score"}), 400

    import json
    conn = db()
    row = conn.execute("SELECT best_score, achievements, games FROM users WHERE discord_id=?", (discord_id,)).fetchone()
    old_ach = set(json.loads(row["achievements"])) if row else set()
    old_ach.update(str(a)[:64] for a in achievements)
    best = max(row["best_score"], score_value) if row else score_value
    games = (row["games"] + 1) if row else 1
    conn.execute(
        "UPDATE users SET best_score=?, achievements=?, games=? WHERE discord_id=?",
        (best, json.dumps(sorted(old_ach)), games, discord_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "best_score": best, "achievements": sorted(old_ach)})


@app.get("/game")
def game():
    if GAME_DIR.exists():
        return send_from_directory(GAME_DIR, "index.html")
    return "Build the Pygbag game first, or set GAME_URL to your hosted game URL.", 404


if __name__ == "__main__":
    db().close()
    app.run(host="0.0.0.0", port=5000, debug=True)
