"""
Flask Web Application for CalorieTracker
"""

print("=" * 50)
print("STARTING APP.PY")
print("=" * 50)


from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_cors import CORS
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import db
import llm
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

_is_production = os.getenv('RENDER', False)  # Render sets this env var automatically

app = Flask(
    __name__,
    static_folder=os.path.join('frontend', 'build', 'static'),
    static_url_path='/static'
)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = bool(_is_production)  # HTTPS only in prod

_allowed_origins = ['http://localhost:3000'] if not _is_production else []
CORS(app,
     resources={r"/api/*": {"origins": _allowed_origins or "*"}},
     supports_credentials=True)

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')


# ═══════════════════════════════════════════════════════════════════
# AUTH MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════

@app.before_request
def require_login():
    """Block all /api/ requests (except auth endpoints) if not logged in."""
    if request.method == 'OPTIONS':
        return  # Allow CORS preflight
    if request.path.startswith('/api/auth/'):
        return  # Auth endpoints are public
    if request.path.startswith('/api/') and 'user' not in session:
        return jsonify({'error': 'Authentication required', 'code': 'UNAUTHENTICATED'}), 401


# ═══════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/auth/google', methods=['POST'])
def auth_google():
    """Verify Google ID token and create session."""
    credential = request.get_json().get('credential')
    if not credential:
        return jsonify({'error': 'No credential provided'}), 400

    if not GOOGLE_CLIENT_ID:
        return jsonify({'error': 'GOOGLE_CLIENT_ID not configured on server'}), 500

    try:
        idinfo = id_token.verify_oauth2_token(
            credential, grequests.Request(), GOOGLE_CLIENT_ID
        )
        session['user'] = {
            'email': idinfo['email'],
            'name':  idinfo.get('name', ''),
            'picture': idinfo.get('picture', ''),
            'sub':   idinfo['sub'],
        }
        return jsonify({'success': True, 'user': session['user']})
    except ValueError as e:
        return jsonify({'error': 'Invalid token', 'detail': str(e)}), 401


@app.route('/api/auth/guest', methods=['POST'])
def auth_guest():
    """Create a guest session with a unique ID."""
    import uuid
    guest_id = f"guest_{uuid.uuid4().hex}"
    session['user'] = {
        'email': '',
        'name': 'Guest',
        'picture': '',
        'sub': guest_id,
        'is_guest': True,
    }
    return jsonify({'success': True, 'user': session['user']})


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    user = session.get('user')
    if user:
        return jsonify({'user': user})
    return jsonify({'user': None}), 401


# ═══════════════════════════════════════════════════════════════════
# HOME PAGE
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# API ENDPOINTS FOR REACT
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/save-profile', methods=['POST'])
def api_save_profile():
    user_id = session['user']['sub']
    data = request.get_json()
    db.save_profile(user_id, data.get('name'), float(data.get('bmr')))
    return jsonify({'success': True, 'profile': db.get_profile(user_id)})

@app.route('/api/profile', methods=['GET'])
def api_get_profile():
    user_id = session['user']['sub']
    profile = db.get_profile(user_id)
    if profile:
        return jsonify(profile)
    return jsonify(None), 404


@app.route('/api/home-data', methods=['GET'])
def api_home_data():
    user_id = session['user']['sub']
    profile = db.get_profile(user_id)
    if not profile:
        return jsonify({'error': 'No profile'}), 404

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    summary      = db.get_daily_summary(user_id, today_str)
    food_entries = db.get_food_entries_for_date(user_id, today_str)

    start_of_week  = today - timedelta(days=today.weekday())
    weekly_summaries = db.get_summaries_between_dates(
        user_id, start_of_week.strftime("%Y-%m-%d"), today_str)
    weekly_deficit = sum(s['deficit'] for s in weekly_summaries)

    start_of_month = today.replace(day=1)
    monthly_summaries = db.get_summaries_between_dates(
        user_id, start_of_month.strftime("%Y-%m-%d"), today_str)
    monthly_deficit = sum(s['deficit'] for s in monthly_summaries)

    unlogged_days = []
    for i in range(today.weekday() + 1):
        check_day = start_of_week + timedelta(days=i)
        check_day_str = check_day.strftime("%Y-%m-%d")
        if not db.get_daily_summary(user_id, check_day_str):
            unlogged_days.append({'date': check_day_str, 'day_name': check_day.strftime("%A")})

    return jsonify({
        'summary': summary,
        'food_entries': food_entries,
        'weekly_deficit': weekly_deficit,
        'monthly_deficit': monthly_deficit,
        'unlogged_days': unlogged_days
    })

@app.route('/api/today-data', methods=['GET'])
def api_today_data():
    user_id = session['user']['sub']
    profile = db.get_profile(user_id)
    if not profile:
        return jsonify({'error': 'No profile'}), 404
    today = datetime.now().strftime("%Y-%m-%d")
    return jsonify({
        'summary':      db.get_daily_summary(user_id, today),
        'food_entries': db.get_food_entries_for_date(user_id, today)
    })


@app.route('/api/week-data', methods=['GET'])
def api_week_data():
    user_id = session['user']['sub']
    profile = db.get_profile(user_id)
    if not profile:
        return jsonify({'error': 'No profile'}), 404

    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_str = start_of_week.strftime("%Y-%m-%d")
    end_str   = (start_of_week + timedelta(days=6)).strftime("%Y-%m-%d")

    # 2 bulk queries instead of 14 individual ones
    summaries_list = db.get_summaries_between_dates(user_id, start_str, end_str)
    summaries_map  = {s['date']: s for s in summaries_list}
    food_map       = db.get_food_entries_between_dates(user_id, start_str, end_str)

    week_days = []
    for i in range(7):
        day     = start_of_week + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        summary = summaries_map.get(day_str)
        week_days.append({
            'date':       day_str,
            'day_name':   day.strftime("%A"),
            'day_short':  day.strftime("%a"),
            'is_today':   day.date() == today.date(),
            'is_future':  day.date() > today.date(),
            'summary':    summary,
            'food_count': len(food_map.get(day_str, [])),
            'logged':     summary is not None
        })

    return jsonify({
        'week_days':     week_days,
        'total_deficit': sum(d['summary']['deficit'] for d in week_days if d['summary']),
        'days_logged':   sum(1 for d in week_days if d['logged']),
        'start_of_week': start_of_week.strftime("%Y-%m-%d"),
        'end_of_week':   (start_of_week + timedelta(days=6)).strftime("%Y-%m-%d")
    })

@app.route('/api/reports-data', methods=['GET'])
def api_reports_data():
    user_id = session['user']['sub']
    profile = db.get_profile(user_id)
    if not profile:
        return jsonify({'error': 'No profile'}), 404

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    start_of_week = today - timedelta(days=today.weekday())
    weekly_summaries = db.get_summaries_between_dates(
        user_id, start_of_week.strftime("%Y-%m-%d"), today_str)

    start_of_month = today.replace(day=1)
    monthly_summaries = db.get_summaries_between_dates(
        user_id, start_of_month.strftime("%Y-%m-%d"), today_str)

    return jsonify({
        'weekly_summaries':  weekly_summaries,
        'monthly_summaries': monthly_summaries,
        'weekly_total':      sum(s['deficit'] for s in weekly_summaries),
        'monthly_total':     sum(s['deficit'] for s in monthly_summaries)
    })

@app.route('/api/get-meals', methods=['GET'])
def api_get_meals():
    user_id = session['user']['sub']
    return jsonify({'meals': db.get_all_saved_meals(user_id)})





# ═══════════════════════════════════════════════════════════════════
# LOG FOOD
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/parse-food', methods=['POST'])
def api_parse_food():
    user_id = session['user']['sub']
    data = request.get_json()
    food_description = data.get('food_description', '')

    if not food_description:
        return jsonify({'error': 'No food description provided'}), 400

    saved_items = []
    remaining_description = food_description

    all_saved_meals = db.get_all_saved_meals(user_id)

    for saved_meal in all_saved_meals:
        label = saved_meal['label'].lower()
        aliases = [alias.lower() for alias in saved_meal.get('aliases', [])]
        all_names = [label] + aliases
        
        for name in all_names:
            if name in food_description.lower():
                saved_items.append({
                    'food_name': saved_meal['label'],
                    'calories': saved_meal['calories'],
                    'protein': saved_meal['protein'],
                    'carbs': saved_meal['carbs'],
                    'fats': saved_meal['fats'],
                    'notes': 'From saved meals',
                    'is_saved_meal': True
                })
                remaining_description = remaining_description.lower().replace(name, "").strip()
                break
    
    # Send remaining to LLM
    llm_items = []
    if remaining_description and remaining_description not in [',', 'and', '']:
        llm_items = llm.calculate_food_macros(remaining_description)
        
        if llm_items is None:
            return jsonify({'error': 'LLM failed to calculate macros'}), 500
        
        for item in llm_items:
            item['is_saved_meal'] = False
    
    all_items = saved_items + llm_items
    
    return jsonify({'items': all_items})


@app.route('/api/save-food-log', methods=['POST'])
def api_save_food_log():
    try:
        user_id = session['user']['sub']
        data = request.get_json()
        food_items          = data.get('food_items', [])
        workout_description = data.get('workout_description', '')
        calories_burned     = float(data.get('calories_burned', 0))
        notes               = data.get('notes', '')
        weight              = data.get('weight')

        today = datetime.now().strftime("%Y-%m-%d")

        if weight is not None:
            db.save_weight(user_id, today, float(weight))

        for item in food_items:
            db.add_food_entry(
                user_id=user_id,
                date=today,
                food_name=item['food_name'],
                calories=item['calories'],
                protein=item['protein'],
                carbs=item['carbs'],
                fats=item['fats'],
                meal_type='meal',
                is_saved_meal=item.get('is_saved_meal', False)
            )

        summary = db.calculate_and_save_daily_summary(
            user_id=user_id, date=today,
            workout_description=workout_description,
            calories_burned=calories_burned, notes=notes
        )

        # Enforce 6-month retention after every log save
        db.cleanup_old_data(user_id)

        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        import traceback
        print("ERROR in save-food-log:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/calculate-workout', methods=['POST'])
def api_calculate_workout():
    """Calculate calories burned from workout description"""
    
    data = request.get_json()
    workout_description = data.get('workout_description', '')
    weight = float(data.get('weight', 70))
    
    if not workout_description:
        return jsonify({'total_calories': 0, 'breakdown': []})
    
    result = llm.calculate_workout_calories(workout_description, weight)
    
    if result is None:
        return jsonify({'error': 'Failed to calculate workout calories'}), 500
    
    return jsonify(result)


@app.route('/api/transcribe', methods=['POST'])
def api_transcribe():
    """Transcribe audio using Groq Whisper"""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    audio_bytes = audio_file.read()
    filename = audio_file.filename or 'audio.webm'

    transcript = llm.transcribe_audio(audio_bytes, filename)
    if transcript is None:
        return jsonify({'error': 'Transcription failed'}), 500

    return jsonify({'transcript': transcript})


@app.route('/api/check-weight-today', methods=['GET'])
def api_check_weight_today():
    user_id = session['user']['sub']
    today = datetime.now().strftime("%Y-%m-%d")
    return jsonify({'has_weight': db.get_weight_for_date(user_id, today) is not None})


@app.route('/api/weight-history', methods=['GET'])
def api_weight_history():
    user_id = session['user']['sub']
    days = request.args.get('days', 30, type=int)
    today = datetime.now()
    weights = db.get_weight_history(
        user_id,
        (today - timedelta(days=days)).strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d")
    )
    return jsonify({'weights': weights})

@app.route('/api/food-entries-for-date', methods=['GET'])
def api_food_entries_for_date():
    """Fetch existing food entries for any date (used when editing a past log)."""
    user_id = session['user']['sub']
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'date param required'}), 400
    summary = db.get_daily_summary(user_id, date)
    return jsonify({
        'food_entries': db.get_food_entries_for_date(user_id, date),
        'summary': summary,
    })


@app.route('/api/save-specific-day-log', methods=['POST'])
def api_save_specific_day_log():
    user_id = session['user']['sub']
    data = request.get_json()
    log_date            = data.get('log_date')
    food_items          = data.get('food_items', [])
    workout_description = data.get('workout_description', '')
    calories_burned     = float(data.get('calories_burned', 0))
    notes               = data.get('notes', '')

    # Delete old entries so editing replaces instead of appending
    db.delete_food_entries_for_date(user_id, log_date)

    for item in food_items:
        db.add_food_entry(
            user_id=user_id, date=log_date,
            food_name=item['food_name'],
            calories=item['calories'], protein=item['protein'],
            carbs=item['carbs'], fats=item['fats'],
            meal_type='meal', is_saved_meal=item.get('is_saved_meal', False)
        )

    summary = db.calculate_and_save_daily_summary(
        user_id=user_id, date=log_date,
        workout_description=workout_description,
        calories_burned=calories_burned, notes=notes
    )
    return jsonify({'success': True, 'summary': summary})


# ═══════════════════════════════════════════════════════════════════
# SAVED MEALS LIBRARY
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/save-meal', methods=['POST'])
def api_save_meal():
    user_id = session['user']['sub']
    data = request.get_json()
    try:
        db.save_custom_meal(
            user_id=user_id,
            label=data['label'],
            calories=float(data['calories']),
            protein=float(data['protein']),
            carbs=float(data['carbs']),
            fats=float(data['fats']),
            description=data.get('description', ''),
            aliases=data.get('aliases', [])
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/delete-meal', methods=['POST'])
def api_delete_meal():
    user_id = session['user']['sub']
    data = request.get_json()
    db.delete_saved_meal(user_id, data.get('label'))
    return jsonify({'success': True})


@app.route('/api/delete-food-entry', methods=['POST'])
def api_delete_food_entry():
    """Delete a single food entry and recalculate the daily summary."""
    user_id = session['user']['sub']
    data = request.get_json()
    entry_id = data.get('entry_id')
    date = data.get('date')

    if not entry_id or not date:
        return jsonify({'error': 'entry_id and date are required'}), 400

    db.delete_food_entry_by_id(user_id, entry_id)

    # Recalculate the daily summary so totals stay accurate
    summary = db.calculate_and_save_daily_summary(user_id=user_id, date=date)
    remaining = db.get_food_entries_for_date(user_id, date)

    return jsonify({'success': True, 'summary': summary, 'food_entries': remaining})


# ═══════════════════════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# SERVE REACT BUILD (production)
# ═══════════════════════════════════════════════════════════════════

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    build_dir = os.path.join(app.root_path, 'frontend', 'build')
    print(f"[serve_react] build_dir={build_dir} exists={os.path.exists(build_dir)} path={path!r}")
    if not os.path.exists(build_dir):
        return f"Build dir not found: {build_dir}", 404
    file_path = os.path.join(build_dir, path)
    if path and os.path.exists(file_path):
        return send_from_directory(build_dir, path)
    return send_from_directory(build_dir, 'index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)