# Learning App with Clickstream Tracking

A minimal Flask app: learners log in, view a text+video lesson, take a quiz,
and every interaction (page views, clicks, video play/pause/seek, quiz
attempts) is logged to a local SQLite database as clickstream data.

## Run it locally

**1. Requirements:** Python 3.9+ installed.

**2. Set up a virtual environment (recommended):**
```bash
cd learnapp
python3 -m venv venv

# Activate it:
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Run the app:**
```bash
python app.py
```
This creates `app.db` (SQLite) automatically on first run, with the
`users`, `events`, and `quiz_questions` tables, plus one seed quiz question.

**5. Open in your browser:**
```
http://127.0.0.1:5000
```
Sign up for an account, log in, view the lesson, play the video, take the
quiz, then check "My Activity" to see your own logged events.

## Inspect the clickstream data directly

```bash
sqlite3 app.db
sqlite> SELECT * FROM events ORDER BY timestamp DESC LIMIT 20;
sqlite> SELECT event_type, COUNT(*) FROM events GROUP BY event_type;
```

## Git

```bash
git init
git add .
git commit -m "Initial commit: learning app with clickstream tracking"
```
Then create a repo on GitHub and:
```bash
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```

## Project structure
```
learnapp/
├── app.py                 # Flask routes, auth, clickstream API
├── requirements.txt
├── static/
│   ├── js/tracker.js       # client-side event capture
│   └── css/style.css
└── templates/
    ├── base.html
    ├── login.html / signup.html
    ├── lesson.html          # text + video content
    ├── quiz.html
    └── dashboard.html       # shows learner's own logged events
```

## Data captured (see events table)
| event_type      | event_details (JSON) fields                                              |
|------------------|----------------------------------------------------------------------------|
| page_view        | page_id                                                                    |
| click             | element_id, element_type                                                  |
| video_action     | video_id, action (play/pause/ended/seeked), video_timestamp (seconds)     |
| quiz_attempt     | quiz_id, question_id, selected_option, is_correct, time_taken (seconds)   |
