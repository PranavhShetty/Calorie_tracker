# Backend Guide — CalorieTracker

This document explains every meaningful part of the backend so you can read,
modify, and extend it confidently on your own.

---

## How the backend fits together

```
Browser (React)
    │
    │  HTTP requests  (/api/...)
    ▼
app.py  ←─── receives requests, checks auth, calls db/llm, returns JSON
    │
    ├── db.py   ←─── all database reads and writes
    └── llm.py  ←─── all AI calls (Groq: food macros, workout calories, transcription)
```

The browser never talks to the database or the AI directly — everything goes
through `app.py` first.

---

## app.py — The Flask Web Server

### What Flask is

Flask is a Python web framework. It lets you write a function in Python and say
"run this function whenever someone visits this URL". Those functions are called
**routes** or **endpoints**.

---

### Imports (lines 10–18)

```python
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
```
These are the tools Flask gives you:
- `Flask` — the class that creates your app
- `request` — the incoming HTTP request (body, headers, query params)
- `jsonify` — converts a Python dict into a JSON response
- `session` — a dictionary stored in the user's browser cookie; persists across requests
- `send_from_directory` — sends a file from a folder (used to serve the React build)

```python
from flask_cors import CORS
```
CORS (Cross-Origin Resource Sharing) is a browser security rule. When your
React dev server runs on port 3000 and Flask runs on port 5000, the browser
blocks requests between them by default. This package adds the right headers to
allow it.

```python
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
```
Google's official library for verifying that a login token actually came from
Google and wasn't forged.

```python
import db      # our database layer
import llm     # our AI layer
from datetime import datetime, timedelta
from dotenv import load_dotenv   # reads .env file into os.environ
import os
```

---

### App setup (lines 20–40)

```python
load_dotenv()
```
Reads your `.env` file and loads values like `GROQ_API_KEY` into environment
variables so `os.getenv()` can access them.

```python
_is_production = os.getenv('RENDER', False)
```
Render (your hosting provider) automatically sets an env var called `RENDER`.
So this is `True` on the live site and `False` on your laptop.

```python
app = Flask(
    __name__,
    static_folder=os.path.join('frontend', 'build', 'static'),
    static_url_path='/static'
)
```
Creates the Flask app. `__name__` tells Flask where the project root is.
`static_folder` points Flask at the compiled React CSS/JS files so it can
serve them.

```python
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-...')
```
Flask uses this key to **sign** the session cookie so users can't tamper with
it. In production this is a strong random value set in Render's dashboard. In
dev it falls back to a hardcoded string (fine for local testing only).

```python
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE']   = bool(_is_production)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
```
Cookie security settings:
- `SameSite=Lax` — cookie is sent on normal navigations but not cross-site
  POST requests (protects against CSRF attacks)
- `Secure=True` in production — cookie only sent over HTTPS, never plain HTTP
- `PERMANENT_SESSION_LIFETIME` — how long a "remember me" session lasts (30 days)
- `HttpOnly=True` — JavaScript in the browser cannot read the cookie
  (protects against XSS attacks)

```python
_allowed_origins = ['http://localhost:3000'] if not _is_production else []
CORS(app, resources={r"/api/*": {"origins": _allowed_origins or "*"}}, supports_credentials=True)
```
In dev: only allow cross-origin requests from the React dev server (port 3000).
In production: Flask serves both the API and the React files on the same
domain, so `"*"` is fine (same-origin requests don't need CORS headers).
`supports_credentials=True` allows the session cookie to be included.

---

### Auth middleware (lines 47–55)

```python
@app.before_request
def require_login():
```
`@app.before_request` means this function runs **before every single request**,
like a gatekeeper. It checks if the user is logged in.

```python
    if request.method == 'OPTIONS':
        return  # Allow CORS preflight
```
Browsers send an OPTIONS request before a cross-origin POST to ask "is this
allowed?" — we must let it through without checking auth.

```python
    if request.path.startswith('/api/auth/'):
        return  # Auth endpoints are public
```
Login endpoints must be accessible without being logged in (obviously).
Returning `None` means "no problem, continue to the actual route".

```python
    if request.path.startswith('/api/') and 'user' not in session:
        return jsonify({'error': 'Authentication required', 'code': 'UNAUTHENTICATED'}), 401
```
For any other `/api/` route, if there's no `user` in the session cookie, reject
the request with HTTP 401 (Unauthorized). The React app sees this 401 and
redirects to the login screen.

---

### Auth endpoints

#### POST /api/auth/google
```python
credential = request.get_json().get('credential')
```
The React app sends a JWT token it got from Google's OAuth button. We pull it
out of the request body.

```python
idinfo = id_token.verify_oauth2_token(credential, grequests.Request(), GOOGLE_CLIENT_ID)
```
This calls Google's servers to verify the token is real and extract the user's
info (`email`, `name`, `picture`, `sub`). If the token is forged or expired,
it raises a `ValueError`.

```python
session.permanent = True
session['user'] = { 'email': ..., 'sub': idinfo['sub'], ... }
```
`session` is like a dictionary attached to a cookie. Setting `session['user']`
means every future request from this browser will have this dict available.
`sub` is Google's unique user ID — we use it as the database key for everything.
`session.permanent = True` makes the cookie last for `PERMANENT_SESSION_LIFETIME`
(30 days) instead of expiring when the browser closes.

#### POST /api/auth/guest
```python
guest_id = f"guest_{uuid.uuid4().hex}"
```
`uuid4()` generates a random 128-bit ID. `.hex` converts it to a hex string
like `a3f92b1c...`. So every guest gets a unique ID like
`guest_a3f92b1c4d5e6f7a...`. Their data is stored normally in the DB —
it just never gets linked to a real account.

#### GET /api/auth/me
Called on every page load by the React app to check "am I still logged in?"
Returns the user from the session if it exists, or 401 if not.

---

### Data endpoints — the pattern

Every data endpoint follows the same 3-step pattern:

```python
@app.route('/api/something', methods=['GET'])
def api_something():
    user_id = session['user']['sub']   # 1. Who is asking?
    # ... call db functions ...         # 2. Get the data
    return jsonify({ ... })             # 3. Return it as JSON
```

You get `user_id` from the session (set at login). This ensures users can only
ever see their own data — it's passed to every `db.*` function call.

---

### /api/home-data

Fetches everything needed for the dashboard in one go:
- Today's summary and food entries
- This week's summaries → weekly deficit total
- This month's summaries → monthly deficit total
- Which days this week have no log (shown as reminders)

```python
start_of_week = today - timedelta(days=today.weekday())
```
`today.weekday()` returns 0 for Monday, 6 for Sunday. Subtracting it from
today gives you the Monday of the current week.

```python
unlogged_days = []
for i in range(today.weekday() + 1):   # loop Mon → today (not future days)
    check_day = start_of_week + timedelta(days=i)
    if not db.get_daily_summary(user_id, check_day_str):
        unlogged_days.append(...)
```
Checks each past day this week. If there's no summary for it, it's "unlogged".

---

### /api/week-data

```python
summaries_list = db.get_summaries_between_dates(user_id, start_str, end_str)
summaries_map  = {s['date']: s for s in summaries_list}
food_map       = db.get_food_entries_between_dates(user_id, start_str, end_str)
```
Fetches the whole week in **2 database queries** instead of 14. The dict
comprehension `{s['date']: s for s in summaries_list}` turns a list like
`[{date:'2026-03-10', ...}, ...]` into `{'2026-03-10': {...}, ...}` so
you can do instant lookups by date in the loop below.

---

### /api/parse-food

This is the core food-logging logic. It handles two types of items:

**1. Saved meals (instant, no AI needed)**
```python
for saved_meal in all_saved_meals:
    if name in food_description.lower():
        saved_items.append(...)                              # found a match
        remaining_description = remaining_description.replace(name, "")  # remove it from the text
```
It scans the user's saved meals (and their aliases). If "dal" is a saved meal
and the user typed "dal and rice", it picks up "dal" immediately and removes
it from the string, leaving "and rice" for the AI.

**2. Everything else → AI (LLM)**
```python
if remaining_description and remaining_description not in [',', 'and', '']:
    llm_items = llm.calculate_food_macros(remaining_description)
```
Whatever wasn't matched by a saved meal gets sent to Groq. The check avoids
sending just `","` or `"and"` to the AI when all items were saved meals.

---

### /api/save-food-log

```python
for item in food_items:
    db.add_food_entry(user_id=user_id, date=today, ...)
```
Inserts each food item as a separate row in the database.

```python
summary = db.calculate_and_save_daily_summary(...)
```
After inserting items, recalculates the day's totals (calories in, calories
burned, deficit) and saves them to `daily_summaries`. This keeps the summary
always up-to-date.

```python
db.cleanup_old_data(user_id)
```
Deletes data older than 6 months. Called after every save so the database
doesn't grow forever.

---

### /api/save-specific-day-log (editing past logs)

```python
db.delete_food_entries_for_date(user_id, log_date)   # wipe old entries
for item in food_items:
    db.add_food_entry(...)                             # insert new entries
```
"Edit" is implemented as delete-then-reinsert. This is simpler and more
reliable than trying to diff the old and new lists.

---

### Serving the React app (lines 524–534)

```python
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
```
This catches **every URL that isn't an `/api/` route** and serves the React
`index.html`. This is needed because React Router handles navigation in the
browser — Flask just needs to serve `index.html` for any URL and React takes
over from there.

```python
if path and os.path.exists(file_path):
    return send_from_directory(build_dir, path)   # serve actual files (CSS, JS, images)
return send_from_directory(build_dir, 'index.html')  # everything else → React app
```

---

### Running the server

```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```
`if __name__ == '__main__'` means this only runs when you execute `python app.py`
directly — NOT when Gunicorn (the production server) imports the file.
`host='0.0.0.0'` means accept connections from any network interface (not just
localhost). In production, Gunicorn is used instead (see `render.yaml`).

---

## db.py — The Database Layer

### Why a separate db.py?

All SQL lives in one file. If you ever want to change the database (e.g. switch
from Turso to PostgreSQL), you only edit `db.py`. `app.py` never writes raw SQL.

### Two databases: local SQLite vs Turso

```python
_USE_TURSO = bool(_TURSO_URL and _TURSO_URL.startswith("libsql://"))
```
- **Local (dev)**: uses SQLite — a simple file `calorie_tracker.db`. No server needed.
- **Production**: uses Turso — a cloud SQLite database accessed over HTTP.

```python
def _exec(sql: str, args: list = None) -> _Result:
    if _USE_TURSO:
        return _exec_turso(sql, args)
    return _exec_local(sql, args)
```
This is the single function everything calls. It automatically routes to the
right database. You never have to think about which database you're on — just
call `_exec(sql, args)`.

---

### The _Result class

```python
class _Result:
    def __init__(self, columns, rows): ...
    def to_dict(self):  ...   # returns first row as {column: value} — for single-row queries
    def to_dicts(self): ...   # returns all rows as a list of dicts — for multi-row queries
```
SQLite and Turso return data in different formats. This wrapper normalises both
into the same interface. `to_dict()` is for "get one row" queries (e.g. get
profile). `to_dicts()` is for "get many rows" queries (e.g. get all food entries).

---

### HTTP connection reuse (_session)

```python
_session = _requests.Session()
```
Instead of opening a new TCP connection to Turso on every query, `Session()`
reuses the same connection. This is one of the performance improvements — it
avoids the ~50-100ms of reconnect overhead on every database call.

---

### Schema init

```python
def _init_schema():
    ddl = [
        "CREATE TABLE IF NOT EXISTS profiles (...)",
        "CREATE TABLE IF NOT EXISTS food_entries (...)",
        ...
    ]
    for stmt in ddl:
        _exec(stmt)

_init_schema()   # runs automatically when db.py is imported
```
`CREATE TABLE IF NOT EXISTS` means "create this table only if it doesn't already
exist". So this is safe to run every time the app starts. The tables are only
created on the very first run.

---

### Tables and what they store

| Table | What it stores |
|---|---|
| `profiles` | One row per user: their name and BMR (daily calorie target) |
| `food_entries` | Every individual food item logged (one row per item) |
| `daily_summaries` | Pre-calculated daily totals (calories in, burned, deficit) |
| `saved_meals` | User's custom meal library with macros |
| `weight_entries` | Daily weight measurements |

The indexes (`CREATE INDEX`) make lookups by `user_id + date` fast instead of
scanning the whole table.

---

### The user_id key

Every table has a `user_id` column. All queries filter by it:
```python
"SELECT * FROM food_entries WHERE user_id=? AND date=?"
```
This is how one user's data is kept separate from another's. The `?` placeholders
(parameterised queries) prevent SQL injection — user input is never concatenated
directly into SQL strings.

---

### calculate_and_save_daily_summary

```python
def calculate_and_save_daily_summary(user_id, date, workout_description="", calories_burned=0, notes=""):
    entries = get_food_entries_for_date(user_id, date)
    cal     = sum(e["calories"] for e in entries)
    deficit = (bmr + calories_burned) - cal
    # INSERT OR UPDATE the daily_summaries row
```
This is called after every food log save and every edit. It recounts everything
from the raw `food_entries` rows so the summary is always accurate. It uses
`INSERT ... ON CONFLICT ... DO UPDATE` (an "upsert") — inserts a new row if
none exists for that date, updates it if one already does.

---

### get_food_entries_between_dates

```python
def get_food_entries_between_dates(user_id, start_date, end_date) -> dict:
    rows = _exec("SELECT * FROM food_entries WHERE user_id=? AND date>=? AND date<=? ORDER BY date, logged_at", ...)
    result = {}
    for d in rows:
        result.setdefault(d["date"], []).append(d)
    return result   # { "2026-03-10": [...entries...], "2026-03-11": [...], ... }
```
`setdefault(key, [])` means: if `key` doesn't exist yet, create it with an
empty list, then return the list. This groups all entries by date in one pass
through the results.

---

## llm.py — The AI Layer

### What Groq is

Groq is an AI API provider (like OpenAI) that hosts open-source language models.
We use it because it's very fast and has a free tier. The model we use is
`llama-3.1-8b-instant` — a smaller, faster model good for structured tasks like
returning JSON.

```python
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
```
Creates an authenticated client. The API key is read from the `.env` file.

---

### calculate_food_macros

```python
prompt = f"""You are an expert Indian nutritionist. Calculate macros for:
USER ATE: {food_description}
Return ONLY valid JSON in this exact format: {{ "items": [...] }}
REFERENCE VALUES: Roti (40g): ~120 kcal ...
"""
```
The prompt is carefully engineered:
- **Role** ("expert Indian nutritionist") makes the model respond in context
- **Reference values** anchor the model to realistic numbers instead of guessing
- **"Return ONLY valid JSON"** prevents the model from adding explanatory text
  that would break `json.loads()`
- **Low temperature (0.3)** makes responses more consistent and less random

```python
response_text = response.choices[0].message.content.strip()
if response_text.startswith("```"):
    response_text = response_text.split("```")[1]   # strip markdown fences
result = json.loads(response_text)
```
Even with instructions, models sometimes wrap JSON in markdown code fences
(` ```json ... ``` `). The code strips those before parsing.

---

### calculate_workout_calories

Same pattern as food macros, but uses MET (Metabolic Equivalent of Task) values:
```
Calories = MET × weight_kg × duration_hours
```
The model is given the formula and reference MET values so it applies them
consistently.

---

### transcribe_audio

```python
transcription = client.audio.transcriptions.create(
    file=(filename, audio_bytes),
    model='whisper-large-v3-turbo',
    language='en',
)
```
Groq also hosts OpenAI's Whisper model for speech-to-text. The React app
records audio from the microphone, sends it as a file upload to
`/api/transcribe`, and this function converts it to text. The text then gets
put into the food description field.

---

## How to add a new feature — the pattern

If you want to add a new data endpoint, here's the recipe:

**Step 1 — Add a db function in `db.py`** (if you need new data):
```python
def get_something(user_id: str) -> list:
    return _exec(
        "SELECT * FROM some_table WHERE user_id=?",
        [user_id]
    ).to_dicts()
```

**Step 2 — Add a route in `app.py`**:
```python
@app.route('/api/something', methods=['GET'])
def api_something():
    user_id = session['user']['sub']          # always get the user id
    data = db.get_something(user_id)          # call your db function
    return jsonify({'something': data})       # return JSON
```

**Step 3 — Call it from React** (in a component):
```javascript
const res = await axios.get(`${API_URL}/api/something`);
console.log(res.data.something);
```

That's the full loop. The auth middleware protects the endpoint automatically —
you don't need to add any login checks.

---

## HTTP status codes used in this app

| Code | Meaning | When used |
|---|---|---|
| 200 | OK | Successful response |
| 400 | Bad Request | Missing or invalid input from the client |
| 401 | Unauthorized | Not logged in |
| 404 | Not Found | Profile doesn't exist yet |
| 500 | Server Error | Something crashed on the server |

---

## Environment variables

| Variable | Where set | What it does |
|---|---|---|
| `SECRET_KEY` | Render dashboard | Signs session cookies |
| `GOOGLE_CLIENT_ID` | Render dashboard + `.env` | Verifies Google logins |
| `GROQ_API_KEY` | Render dashboard + `.env` | Authenticates AI calls |
| `TURSO_DATABASE_URL` | Render dashboard | Points to the cloud database |
| `TURSO_AUTH_TOKEN` | Render dashboard | Authenticates DB access |
| `RENDER` | Set automatically by Render | Tells app it's in production |
