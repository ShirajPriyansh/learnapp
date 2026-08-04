# Learning App with Clickstream Tracking — "Our Solar System"

A Flask + SQLite learning app for 5th graders. Learners log in and work through
a solar-system lesson (text, embedded video, and an interactive puzzle) plus a
quiz. Every interaction — clicks, page views, video actions (including seeking),
quiz attempts, and puzzle attempts — is captured as clickstream data. This data
is visible **only** to a separate admin role, never to learners.

Live demo: `https://<your-username>.pythonanywhere.com`

## Features

- Learner signup/login (session-based, hashed passwords)
- Interactive lesson: reading material, a "fun fact" reveal, an embedded
  YouTube video, and a click-to-order planets puzzle
- 7-question quiz on the solar system, graded server-side
- Full clickstream capture — page views, clicks, video play/pause/seek,
  quiz attempts, puzzle attempts
- Strict role separation:
  - **Learners** can access the lesson and quiz, but never clickstream data
  - **Admin** can view/filter/export clickstream data, but has no access to
    lesson or quiz content
- Admin dashboard with filters (date range, learner, event type) and CSV export,
  timestamps shown in IST
- Deployed on PythonAnywhere, version-controlled with Git

## Tech stack

Flask (Python) · SQLite · Jinja2 · vanilla JS (client-side event tracking) ·
YouTube IFrame API (video embed + tracking) · Werkzeug (password hashing)

## Run it locally

**1. Requirements:** Python 3.9+

**2. Set up an environment** (conda or venv):
```bash
conda create -n learnapp python=3.10
conda activate learnapp
# or: python3 -m venv venv && source venv/bin/activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Initialize the database and run:**
```bash
python app.py
```
This creates `app.db` on first run, with `users`, `events`, and `quiz_questions`
tables, plus 7 seeded solar-system quiz questions.

**5. Create an admin account** (separate terminal — the app must not be
interrupted). Admin accounts are **never** created through `/signup`:
```bash
python create_admin.py
```
Follow the prompts for a username and password.

**6. Open in your browser:**
```
http://127.0.0.1:5000
```
- Log in with a normal signup account → lands on `/lesson`
- Log in with the admin account you just created → lands on `/admin/clickstream`

## Deployed version (PythonAnywhere)

The live version is deployed by pulling from this GitHub repo:
```bash
cd ~/learnapp
git pull
```
then reloading the web app from the PythonAnywhere **Web** tab. See
`DB_PATH` in `app.py` — it's set as an **absolute path** (resolved from the
script's own location), which is required for the database to be found
correctly under PythonAnywhere's WSGI setup.

## Git

```bash
git init
git add .
git commit -m "Initial commit: learning app with clickstream tracking"
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```
Ongoing changes: commit locally → push to GitHub → `git pull` on
PythonAnywhere → reload. See commit history for the project's full
development timeline (auth → content → role separation → video tracking →
deployment fixes).

## Project structure
```
learnapp/
├── app.py                  # Flask routes, auth, RBAC, clickstream API
├── create_admin.py         # Standalone script to create an admin account
├── requirements.txt
├── static/
│   ├── js/tracker.js        # client-side event capture (clicks, page views)
│   └── css/style.css
└── templates/
    ├── base.html             # nav bar — differs for learner vs admin
    ├── login.html / signup.html
    ├── lesson.html            # text + YouTube video + puzzle, with tracking
    ├── quiz.html
    ├── clickstream.html       # admin-only: filters, table, CSV export
    └── access_denied.html     # shown on role-mismatched route access
```

## Roles & access control

| | Learner | Admin |
|---|---|---|
| Created via | Public `/signup` | `python create_admin.py` only |
| `/lesson`, `/quiz` | ✅ | ❌ (403) |
| `/admin/clickstream` | ❌ (403) | ✅ |
| Generates clickstream data | ✅ (as the data subject) | — |
| Views clickstream data | ❌ | ✅, with filters + CSV export |

## Clickstream data captured

All events are stored in a single `events` table with a flexible JSON
`event_details` column — this let new event types (like `puzzle_attempt`)
get added without any schema change.

| `event_type` | Captured fields (`event_details`) | Data types |
|---|---|---|
| `page_view` | `page_id` | string |
| `click` | `element_id`, `element_type` | string, string |
| `video_action` | `video_id`, `action` (play / pause / seek / ended), `video_timestamp` (or `from_timestamp`/`to_timestamp` for seeks) | string, enum, float (seconds) |
| `quiz_attempt` | `quiz_id`, `question_id`, `selected_option`, `is_correct`, `time_taken` | string, int, string, boolean, float |
| `puzzle_attempt` | `puzzle_id`, `user_order` (array), `is_correct` | string, array, boolean |

Every row also stores: `event_id`, `user_id` (FK), `event_type`,
`event_details` (JSON text), `timestamp` (ISO 8601, stored in UTC —
converted to IST when displayed or exported by the admin).

## Inspect the database directly
```bash
sqlite3 app.db
sqlite> SELECT event_type, COUNT(*) FROM events GROUP BY event_type;
sqlite> SELECT username, is_admin FROM users;
```
