"""
Database layer — SQLite locally, Turso (HTTP API) in production.

Local dev  : TURSO_DATABASE_URL not set  →  ./calorie_tracker.db  (Python sqlite3)
Production : TURSO_DATABASE_URL=libsql://yourdb-org.turso.io
             TURSO_AUTH_TOKEN=your-token
"""

import os, json, sqlite3
from datetime import datetime, timedelta

import requests as _requests

MAX_SAVED_MEALS = 5000
RETENTION_DAYS  = 183   # ~6 months

_TURSO_URL   = os.getenv("TURSO_DATABASE_URL", "")
_TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")
_USE_TURSO   = bool(_TURSO_URL and _TURSO_URL.startswith("libsql://"))
_LOCAL_DB    = "./calorie_tracker.db"

if _USE_TURSO:
    _HTTP_URL = _TURSO_URL.replace("libsql://", "https://")
    _HEADERS  = {
        "Authorization": f"Bearer {_TURSO_TOKEN}",
        "Content-Type":  "application/json",
    }


# ── Result wrapper ────────────────────────────────────────────────────────────

class _Result:
    def __init__(self, columns, rows):
        self.columns = tuple(columns)
        self.rows    = rows   # list of tuples

    def to_dict(self):
        if not self.rows:
            return None
        return {self.columns[i]: self.rows[0][i] for i in range(len(self.columns))}

    def to_dicts(self):
        return [{self.columns[i]: row[i] for i in range(len(self.columns))}
                for row in self.rows]


# ── Execution layer ───────────────────────────────────────────────────────────

def _turso_arg(v):
    """Convert a Python value to a Turso typed arg."""
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    return {"type": "text", "value": str(v)}


def _turso_val(v):
    """Parse a Turso response value (may be typed dict or raw Python value)."""
    if v is None:
        return None
    if isinstance(v, dict):
        t   = v.get("type")
        val = v.get("value")
        if t == "null" or val is None:
            return None
        if t == "integer":
            return int(val)
        if t == "float":
            return float(val)
        return str(val)
    return v


def _exec_turso(sql: str, args: list = None) -> _Result:
    stmt = {"sql": sql}
    if args:
        stmt["args"] = [_turso_arg(a) for a in args]
    payload = {
        "requests": [
            {"type": "execute", "stmt": stmt},
            {"type": "close"},
        ]
    }
    resp = _requests.post(
        f"{_HTTP_URL}/v2/pipeline",
        headers=_HEADERS,
        json=payload,
        timeout=10,
    )
    if not resp.ok:
        raise Exception(f"Turso HTTP {resp.status_code}: {resp.text}")
    data   = resp.json()
    result = data["results"][0]
    if result["type"] == "error":
        raise Exception(result.get("error", {}).get("message", "Turso error"))
    execute = result["response"]["result"]
    columns = [c["name"] for c in execute["cols"]]
    rows    = [tuple(_turso_val(v) for v in row) for row in execute["rows"]]
    return _Result(columns, rows)


def _exec_local(sql: str, args: list = None) -> _Result:
    conn = sqlite3.connect(_LOCAL_DB)
    cur  = conn.cursor()
    cur.execute(sql, args or [])
    cols = tuple(d[0] for d in cur.description) if cur.description else ()
    rows = [tuple(row) for row in cur.fetchall()]
    conn.commit()
    conn.close()
    return _Result(cols, rows)


def _exec(sql: str, args: list = None) -> _Result:
    if _USE_TURSO:
        return _exec_turso(sql, args)
    return _exec_local(sql, args)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _process_entry(d: dict) -> dict:
    if d:
        d["is_saved_meal"] = bool(d.get("is_saved_meal", 0))
    return d


def _process_meal(d: dict) -> dict:
    if d:
        raw = d.get("aliases") or "[]"
        d["aliases"] = json.loads(raw) if isinstance(raw, str) else raw
    return d


# ── Schema init ───────────────────────────────────────────────────────────────

def _init_schema():
    ddl = [
        """CREATE TABLE IF NOT EXISTS profiles (
            user_id TEXT PRIMARY KEY, name TEXT NOT NULL,
            bmr REAL NOT NULL, created_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS food_entries (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            date TEXT NOT NULL, food_name TEXT NOT NULL,
            calories REAL NOT NULL, protein REAL NOT NULL,
            carbs REAL NOT NULL, fats REAL NOT NULL,
            meal_type TEXT NOT NULL DEFAULT 'meal',
            is_saved_meal INTEGER NOT NULL DEFAULT 0,
            logged_at TEXT NOT NULL)""",
        "CREATE INDEX IF NOT EXISTS idx_food_ud ON food_entries(user_id, date)",
        """CREATE TABLE IF NOT EXISTS daily_summaries (
            user_id TEXT NOT NULL, date TEXT NOT NULL,
            total_calories_in REAL, total_protein REAL,
            total_carbs REAL, total_fats REAL,
            workout_description TEXT DEFAULT '',
            calories_burned REAL DEFAULT 0, bmr REAL,
            total_burned REAL, deficit REAL,
            notes TEXT DEFAULT '', num_food_items INTEGER,
            logged_at TEXT NOT NULL,
            PRIMARY KEY (user_id, date))""",
        """CREATE TABLE IF NOT EXISTS saved_meals (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            label TEXT NOT NULL, calories REAL NOT NULL,
            protein REAL NOT NULL, carbs REAL NOT NULL,
            fats REAL NOT NULL, description TEXT DEFAULT '',
            aliases TEXT DEFAULT '[]', created_at TEXT NOT NULL)""",
        "CREATE INDEX IF NOT EXISTS idx_meals_u ON saved_meals(user_id)",
        """CREATE TABLE IF NOT EXISTS weight_entries (
            user_id TEXT NOT NULL, date TEXT NOT NULL,
            weight REAL NOT NULL, logged_at TEXT NOT NULL,
            PRIMARY KEY (user_id, date))""",
    ]
    for stmt in ddl:
        try:
            _exec(stmt)
        except Exception:
            pass


_init_schema()


# ── Data retention ────────────────────────────────────────────────────────────

def cleanup_old_data(user_id: str):
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")
    _exec("DELETE FROM food_entries    WHERE user_id=? AND date<?", [user_id, cutoff])
    _exec("DELETE FROM daily_summaries WHERE user_id=? AND date<?", [user_id, cutoff])
    _exec("DELETE FROM weight_entries  WHERE user_id=? AND date<?", [user_id, cutoff])


# ── Profile ───────────────────────────────────────────────────────────────────

def save_profile(user_id: str, name: str, bmr: float):
    _exec(
        """INSERT INTO profiles (user_id,name,bmr,created_at) VALUES (?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET name=excluded.name, bmr=excluded.bmr""",
        [user_id, name, float(bmr), datetime.now().isoformat()]
    )
    return get_profile(user_id)


def get_profile(user_id: str):
    return _exec("SELECT * FROM profiles WHERE user_id=?", [user_id]).to_dict()


# ── Food entries ──────────────────────────────────────────────────────────────

def add_food_entry(user_id: str, date: str, food_name: str,
                   calories: float, protein: float, carbs: float, fats: float,
                   meal_type: str = "meal", is_saved_meal: bool = False):
    eid = f"{user_id}__{date}_{datetime.now().strftime('%H%M%S%f')}"
    now = datetime.now().isoformat()
    _exec(
        """INSERT INTO food_entries
           (id,user_id,date,food_name,calories,protein,carbs,fats,
            meal_type,is_saved_meal,logged_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [eid, user_id, date, food_name,
         float(calories), float(protein), float(carbs), float(fats),
         meal_type, 1 if is_saved_meal else 0, now]
    )
    return {"date": date, "food_name": food_name, "calories": calories,
            "protein": protein, "carbs": carbs, "fats": fats,
            "meal_type": meal_type, "is_saved_meal": is_saved_meal, "logged_at": now}


def get_food_entries_for_date(user_id: str, date: str) -> list:
    r = _exec(
        "SELECT * FROM food_entries WHERE user_id=? AND date=? ORDER BY logged_at",
        [user_id, date]
    )
    return [_process_entry(d) for d in r.to_dicts()]


def delete_food_entries_for_date(user_id: str, date: str):
    """Delete all food entries for a given date (used before re-saving an edited log)."""
    _exec("DELETE FROM food_entries WHERE user_id=? AND date=?", [user_id, date])


def delete_food_entry_by_id(user_id: str, entry_id: str) -> bool:
    """Delete a single food entry by its ID. Returns True if a row was deleted."""
    # We include user_id in the WHERE clause so users can only delete their own entries
    r = _exec(
        "DELETE FROM food_entries WHERE id=? AND user_id=?",
        [entry_id, user_id]
    )
    return True


# ── Daily summary ─────────────────────────────────────────────────────────────

def calculate_and_save_daily_summary(user_id: str, date: str,
                                      workout_description: str = "",
                                      calories_burned: float = 0, notes: str = ""):
    profile = get_profile(user_id)
    if not profile:
        raise Exception("No profile found.")

    entries = get_food_entries_for_date(user_id, date)
    if not entries:
        return None

    bmr          = float(profile["bmr"])
    cal          = sum(e["calories"] for e in entries)
    prot         = sum(e["protein"]  for e in entries)
    carbs        = sum(e["carbs"]    for e in entries)
    fats         = sum(e["fats"]     for e in entries)
    total_burned = bmr + float(calories_burned)
    deficit      = total_burned - cal

    _exec(
        """INSERT INTO daily_summaries
           (user_id,date,total_calories_in,total_protein,total_carbs,total_fats,
            workout_description,calories_burned,bmr,total_burned,deficit,
            notes,num_food_items,logged_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(user_id,date) DO UPDATE SET
               total_calories_in=excluded.total_calories_in,
               total_protein=excluded.total_protein,
               total_carbs=excluded.total_carbs,
               total_fats=excluded.total_fats,
               workout_description=excluded.workout_description,
               calories_burned=excluded.calories_burned,
               bmr=excluded.bmr, total_burned=excluded.total_burned,
               deficit=excluded.deficit, notes=excluded.notes,
               num_food_items=excluded.num_food_items,
               logged_at=excluded.logged_at""",
        [user_id, date, round(cal,1), round(prot,1), round(carbs,1), round(fats,1),
         workout_description or "", float(calories_burned), bmr,
         round(total_burned,1), round(deficit,1),
         notes or "", len(entries), datetime.now().isoformat()]
    )
    return get_daily_summary(user_id, date)


def get_daily_summary(user_id: str, date: str):
    return _exec(
        "SELECT * FROM daily_summaries WHERE user_id=? AND date=?",
        [user_id, date]
    ).to_dict()


def get_summaries_between_dates(user_id: str, start_date: str, end_date: str) -> list:
    return _exec(
        "SELECT * FROM daily_summaries WHERE user_id=? AND date>=? AND date<=? ORDER BY date",
        [user_id, start_date, end_date]
    ).to_dicts()


# ── Saved meals ───────────────────────────────────────────────────────────────

def _meal_id(user_id: str, label: str) -> str:
    return f"{user_id}__{label.lower().replace(' ','_').replace(chr(39),'')}"


def count_saved_meals(user_id: str) -> int:
    r = _exec("SELECT COUNT(*) AS cnt FROM saved_meals WHERE user_id=?", [user_id])
    return int(r.rows[0][0]) if r.rows else 0


def save_custom_meal(user_id: str, label: str, calories: float, protein: float,
                     carbs: float, fats: float, description: str = "", aliases: list = None):
    if aliases is None:
        aliases = []
    mid = _meal_id(user_id, label)
    is_new = not _exec("SELECT id FROM saved_meals WHERE id=?", [mid]).rows
    if is_new and count_saved_meals(user_id) >= MAX_SAVED_MEALS:
        raise Exception(f"Saved meals limit reached ({MAX_SAVED_MEALS}). Delete some to add new ones.")

    _exec(
        """INSERT INTO saved_meals
           (id,user_id,label,calories,protein,carbs,fats,description,aliases,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
               calories=excluded.calories, protein=excluded.protein,
               carbs=excluded.carbs, fats=excluded.fats,
               description=excluded.description, aliases=excluded.aliases""",
        [mid, user_id, label, float(calories), float(protein),
         float(carbs), float(fats), description or "",
         json.dumps(aliases), datetime.now().isoformat()]
    )
    return _process_meal(
        _exec("SELECT * FROM saved_meals WHERE id=?", [mid]).to_dict()
    )


def search_saved_meal(user_id: str, query: str):
    q = query.lower()
    r = _exec(
        "SELECT * FROM saved_meals WHERE user_id=? AND (LOWER(label)=? OR LOWER(label) LIKE ?) LIMIT 1",
        [user_id, q, f"%{q}%"]
    )
    if r.rows:
        return _process_meal(r.to_dict())
    for meal in get_all_saved_meals(user_id):
        aliases = [a.lower() for a in meal.get("aliases", [])]
        if q in aliases or any(a in q for a in aliases):
            return meal
    return None


def get_all_saved_meals(user_id: str) -> list:
    return [_process_meal(d) for d in
            _exec("SELECT * FROM saved_meals WHERE user_id=? ORDER BY created_at DESC",
                  [user_id]).to_dicts()]


def delete_saved_meal(user_id: str, label: str) -> bool:
    try:
        _exec("DELETE FROM saved_meals WHERE id=?", [_meal_id(user_id, label)])
        return True
    except Exception:
        return False


def update_saved_meal(user_id: str, label: str, calories=None,
                      protein=None, carbs=None, fats=None):
    meal = search_saved_meal(user_id, label)
    if not meal:
        return None
    if calories is not None: meal["calories"] = float(calories)
    if protein  is not None: meal["protein"]  = float(protein)
    if carbs    is not None: meal["carbs"]    = float(carbs)
    if fats     is not None: meal["fats"]     = float(fats)
    return save_custom_meal(user_id=user_id, label=meal["label"],
                            calories=meal["calories"], protein=meal["protein"],
                            carbs=meal["carbs"], fats=meal["fats"],
                            description=meal.get("description",""),
                            aliases=meal.get("aliases",[]))


# ── Weight ────────────────────────────────────────────────────────────────────

def save_weight(user_id: str, date: str, weight: float):
    _exec(
        """INSERT INTO weight_entries (user_id,date,weight,logged_at)
           VALUES (?,?,?,?)
           ON CONFLICT(user_id,date) DO UPDATE SET
               weight=excluded.weight, logged_at=excluded.logged_at""",
        [user_id, date, float(weight), datetime.now().isoformat()]
    )
    return {"date": date, "weight": weight}


def get_weight_for_date(user_id: str, date: str):
    return _exec(
        "SELECT * FROM weight_entries WHERE user_id=? AND date=?",
        [user_id, date]
    ).to_dict()


def get_weight_history(user_id: str, start_date: str, end_date: str) -> list:
    return _exec(
        "SELECT * FROM weight_entries WHERE user_id=? AND date>=? AND date<=? ORDER BY date",
        [user_id, start_date, end_date]
    ).to_dicts()
