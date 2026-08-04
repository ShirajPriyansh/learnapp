import csv
import io
import sqlite3
import json
from datetime import datetime, timedelta
from flask import Flask, Response, request, session, jsonify, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dev-secret-change-this"  # change before any real deployment
DB_PATH = "app.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        event_details TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS quiz_questions (
        question_id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id TEXT NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
        correct_option TEXT NOT NULL
    );
    """)

    user_columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "is_admin" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")

    # seed sample quiz if empty - "Our Solar System" for 5th graders
    existing = conn.execute("SELECT COUNT(*) c FROM quiz_questions").fetchone()["c"]
    if existing == 0:
        questions = [
            ("quiz1", "Which planet is known as the Red Planet?",
             "Venus", "Mars", "Jupiter", "Saturn", "B"),
            ("quiz1", "What is the closest planet to the Sun?",
             "Earth", "Venus", "Mercury", "Mars", "C"),
            ("quiz1", "How many planets are in our solar system?",
             "7", "8", "9", "10", "B"),
            ("quiz1", "Which planet has the famous rings made of ice and rock?",
             "Saturn", "Mars", "Neptune", "Mercury", "A"),
            ("quiz1", "Why does Earth have day and night?",
             "The Sun moves around Earth", "Earth spins on its axis",
             "Earth changes size", "Clouds block the Sun", "B"),
            ("quiz1", "Which planet is the largest in our solar system?",
             "Earth", "Saturn", "Jupiter", "Uranus", "C"),
            ("quiz1", "About how long does it take Earth to orbit the Sun once?",
             "1 day", "1 month", "1 year", "10 years", "C"),
        ]
        conn.executemany(
            "INSERT INTO quiz_questions (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_option) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            questions
        )
    conn.commit()
    conn.close()


def selected_filters():
    return {
        "from_date": request.args.get("from_date", "").strip(),
        "to_date": request.args.get("to_date", "").strip(),
        "username": request.args.get("username", "").strip(),
        "event_type": request.args.get("event_type", "").strip(),
    }


def end_of_day(value):
    if not value:
        return value
    try:
        return (datetime.fromisoformat(value) + timedelta(days=1)).isoformat()
    except ValueError:
        return value


def build_clickstream_query(filters):
    query = """
        SELECT e.timestamp, u.username, e.event_type, e.event_details
        FROM events e
        JOIN users u ON e.user_id = u.user_id
    """
    clauses = []
    params = []

    if filters["from_date"]:
        clauses.append("e.timestamp >= ?")
        params.append(filters["from_date"])
    if filters["to_date"]:
        clauses.append("e.timestamp < ?")
        params.append(end_of_day(filters["to_date"]))
    if filters["username"]:
        clauses.append("u.username = ?")
        params.append(filters["username"])
    if filters["event_type"]:
        clauses.append("e.event_type = ?")
        params.append(filters["event_type"])

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY e.timestamp DESC LIMIT 500"
    return query, params


# ---------- AUTH ----------

@app.route("/", methods=["GET"])
def home():
    if "user_id" in session:
        if session.get("is_admin"):
            return redirect(url_for("clickstream"))
        return redirect(url_for("lesson"))
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), datetime.utcnow().isoformat())
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("signup.html", error="Username already taken.")
        conn.close()
        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            if session["is_admin"]:
                return redirect(url_for("clickstream"))
            return redirect(url_for("lesson"))
        return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def login_required(view):
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


def learner_required(view):
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("is_admin"):
            return render_template("access_denied.html", username=session.get("username")), 403
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


def admin_required(view):
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if not session.get("is_admin"):
            return render_template("access_denied.html", username=session.get("username")), 403
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


# ---------- LEARNER CONTENT ----------

@app.route("/lesson")
@learner_required
def lesson():
    return render_template("lesson.html", username=session.get("username"))


@app.route("/quiz")
@learner_required
def quiz():
    conn = get_db()
    questions = conn.execute("SELECT * FROM quiz_questions WHERE quiz_id = 'quiz1'").fetchall()
    conn.close()
    return render_template("quiz.html", questions=questions, username=session.get("username"))


# ---------- ADMIN CLICKSTREAM ----------

@app.route("/dashboard")
@admin_required
def dashboard():
    return redirect(url_for("clickstream"))


@app.route("/admin/clickstream")
@admin_required
def clickstream():
    filters = selected_filters()
    query, params = build_clickstream_query(filters)

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    usernames = conn.execute("""
        SELECT DISTINCT u.username
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        ORDER BY u.username
    """).fetchall()
    event_types = conn.execute("""
        SELECT DISTINCT event_type
        FROM events
        ORDER BY event_type
    """).fetchall()
    conn.close()

    return render_template(
        "clickstream.html",
        rows=rows,
        usernames=[row["username"] for row in usernames],
        event_types=[row["event_type"] for row in event_types],
        filters=filters,
        username=session.get("username")
    )


@app.route("/admin/clickstream/download")
@admin_required
def clickstream_download():
    filters = selected_filters()
    query, params = build_clickstream_query(filters)

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "username", "event_type", "event_details"])
    for row in rows:
        writer.writerow([row["timestamp"], row["username"], row["event_type"], row["event_details"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=clickstream_export.csv"}
    )


# ---------- CLICKSTREAM API ----------

@app.route("/api/log", methods=["POST"])
@learner_required
def log_event():
    data = request.get_json(force=True)
    conn = get_db()
    conn.execute(
        "INSERT INTO events (user_id, event_type, event_details, timestamp) VALUES (?, ?, ?, ?)",
        (session["user_id"], data.get("event_type"), json.dumps(data.get("event_details", {})),
         data.get("timestamp", datetime.utcnow().isoformat()))
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/quiz-submit", methods=["POST"])
@learner_required
def quiz_submit():
    data = request.get_json(force=True)
    conn = get_db()
    q = conn.execute("SELECT correct_option FROM quiz_questions WHERE question_id = ?",
                      (data["question_id"],)).fetchone()
    is_correct = bool(q and q["correct_option"] == data["selected_option"])
    conn.execute(
        "INSERT INTO events (user_id, event_type, event_details, timestamp) VALUES (?, ?, ?, ?)",
        (session["user_id"], "quiz_attempt",
         json.dumps({
             "quiz_id": data.get("quiz_id"),
             "question_id": data.get("question_id"),
             "selected_option": data.get("selected_option"),
             "is_correct": is_correct,
             "time_taken": data.get("time_taken")
         }),
         datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "is_correct": is_correct})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
