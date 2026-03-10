"""
Flask Web Application for CalorieTracker
"""

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
import meals
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

@app.route('/')
def index():
    """Home page - shows today's summary + weekly/monthly deficit + unlogged days alert"""
    
    profile = db.get_profile()
    
    if not profile:
        # No profile, redirect to setup
        return redirect(url_for('setup'))
    
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    summary = db.get_daily_summary(today_str)
    food_entries = db.get_food_entries_for_date(today_str)
    
    # Weekly data
    start_of_week = today - timedelta(days=today.weekday())
    weekly_summaries = db.get_summaries_between_dates(
        start_of_week.strftime("%Y-%m-%d"),
        today_str
    )
    weekly_deficit = sum(s['deficit'] for s in weekly_summaries) if weekly_summaries else 0
    
    # Monthly data
    start_of_month = today.replace(day=1)
    monthly_summaries = db.get_summaries_between_dates(
        start_of_month.strftime("%Y-%m-%d"),
        today_str
    )
    monthly_deficit = sum(s['deficit'] for s in monthly_summaries) if monthly_summaries else 0
    
    # Check for unlogged days this week (excluding future days)
    unlogged_days = []
    for i in range(today.weekday() + 1):  # Only check up to today
        check_day = start_of_week + timedelta(days=i)
        check_day_str = check_day.strftime("%Y-%m-%d")
        day_summary = db.get_daily_summary(check_day_str)
        if not day_summary:
            unlogged_days.append({
                'date': check_day_str,
                'day_name': check_day.strftime("%A")
            })
    
    return render_template('index.html', 
                         profile=profile,
                         summary=summary,
                         food_entries=food_entries,
                         today=today_str,
                         weekly_deficit=weekly_deficit,
                         weekly_days=len(weekly_summaries),
                         monthly_deficit=monthly_deficit,
                         monthly_days=len(monthly_summaries),
                         unlogged_days=unlogged_days)


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

    week_days = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        summary      = db.get_daily_summary(user_id, day_str)
        food_entries = db.get_food_entries_for_date(user_id, day_str)
        week_days.append({
            'date':       day_str,
            'day_name':   day.strftime("%A"),
            'day_short':  day.strftime("%a"),
            'is_today':   day.date() == today.date(),
            'is_future':  day.date() > today.date(),
            'summary':    summary,
            'food_count': len(food_entries) if food_entries else 0,
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
# SETUP
# ═══════════════════════════════════════════════════════════════════

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Setup page for first-time users"""
    
    if request.method == 'POST':
        name = request.form.get('name', 'User')
        bmr = float(request.form.get('bmr'))
        
        db.save_profile(name, bmr)
        
        return redirect(url_for('index'))
    
    return render_template('setup.html')


    # ═══════════════════════════════════════════════════════════════════
# SETTINGS / EDIT PROFILE
# ═══════════════════════════════════════════════════════════════════

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page to update profile (BMR, name)"""
    
    profile = db.get_profile()
    if not profile:
        return redirect(url_for('setup'))
    
    if request.method == 'POST':
        name = request.form.get('name', profile['name'])
        bmr = float(request.form.get('bmr'))
        
        db.save_profile(name, bmr)
        
        return redirect(url_for('index'))
    
    return render_template('settings.html', profile=profile)


# ═══════════════════════════════════════════════════════════════════
# LOG FOOD
# ═══════════════════════════════════════════════════════════════════

@app.route('/log', methods=['GET', 'POST'])
def log_food():
    """Log food page"""
    
    profile = db.get_profile()
    if not profile:
        return redirect(url_for('setup'))
    
    if request.method == 'POST':
        # This will be handled by AJAX
        pass
    
    return render_template('log.html', profile=profile)


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

# ═══════════════════════════════════════════════════════════════════
# STATUS / TODAY
# ═══════════════════════════════════════════════════════════════════

@app.route('/status')
def status():
    """Today's status page"""
    
    profile = db.get_profile()
    if not profile:
        return redirect(url_for('setup'))
    
    today = datetime.now().strftime("%Y-%m-%d")
    summary = db.get_daily_summary(today)
    food_entries = db.get_food_entries_for_date(today)
    
    return render_template('status.html',
                         profile=profile,
                         summary=summary,
                         food_entries=food_entries,
                         today=today)


# ═══════════════════════════════════════════════════════════════════
# REPORTS (WEEKLY/MONTHLY)
# ═══════════════════════════════════════════════════════════════════

@app.route('/reports')
def reports():
    """Reports page - weekly and monthly"""
    
    profile = db.get_profile()
    if not profile:
        return redirect(url_for('setup'))
    
    today = datetime.now()
    
    # Weekly
    start_of_week = today - timedelta(days=today.weekday())
    weekly_summaries = db.get_summaries_between_dates(
        start_of_week.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d")
    )
    
    # Monthly
    start_of_month = today.replace(day=1)
    monthly_summaries = db.get_summaries_between_dates(
        start_of_month.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d")
    )
    
    # Calculate totals
    weekly_total = sum(s['deficit'] for s in weekly_summaries)
    monthly_total = sum(s['deficit'] for s in monthly_summaries)
    
    return render_template('reports.html',
                         profile=profile,
                         weekly_summaries=weekly_summaries,
                         monthly_summaries=monthly_summaries,
                         weekly_total=weekly_total,
                         monthly_total=monthly_total)



# ═══════════════════════════════════════════════════════════════════
# THIS WEEK VIEW
# ═══════════════════════════════════════════════════════════════════

@app.route('/week')
def week_view():
    """This week view - shows all 7 days with edit option for missed days"""
    
    profile = db.get_profile()
    if not profile:
        return redirect(url_for('setup'))
    
    today = datetime.now()
    
    # Get start of week (Monday)
    start_of_week = today - timedelta(days=today.weekday())
    
    # Generate all 7 days of the week
    week_days = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        
        # Get summary for this day
        summary = db.get_daily_summary(day_str)
        
        # Get food entries count
        food_entries = db.get_food_entries_for_date(day_str)
        
        week_days.append({
            'date': day_str,
            'day_name': day.strftime("%A"),
            'day_short': day.strftime("%a"),
            'is_today': day.date() == today.date(),
            'is_future': day.date() > today.date(),
            'summary': summary,
            'food_count': len(food_entries) if food_entries else 0,
            'logged': summary is not None
        })
    
    # Calculate week totals
    total_deficit = sum(day['summary']['deficit'] for day in week_days if day['summary'])
    days_logged = sum(1 for day in week_days if day['logged'])
    
    return render_template('week.html',
                         profile=profile,
                         week_days=week_days,
                         total_deficit=total_deficit,
                         days_logged=days_logged,
                         start_of_week=start_of_week.strftime("%Y-%m-%d"),
                         end_of_week=(start_of_week + timedelta(days=6)).strftime("%Y-%m-%d"))


@app.route('/log-day/<date>', methods=['GET'])
def log_specific_day(date):
    """Log food for a specific past day"""
    
    profile = db.get_profile()
    if not profile:
        return redirect(url_for('setup'))
    
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return redirect(url_for('week_view'))
    
    return render_template('log_day.html', profile=profile, log_date=date)


@app.route('/api/save-specific-day-log', methods=['POST'])
def api_save_specific_day_log():
    user_id = session['user']['sub']
    data = request.get_json()
    log_date            = data.get('log_date')
    food_items          = data.get('food_items', [])
    workout_description = data.get('workout_description', '')
    calories_burned     = float(data.get('calories_burned', 0))
    notes               = data.get('notes', '')

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

@app.route('/meals')
def saved_meals_page():
    """Saved meals library page"""
    
    profile = db.get_profile()
    if not profile:
        return redirect(url_for('setup'))
    
    all_meals = db.get_all_saved_meals()
    
    return render_template('meals.html',
                         profile=profile,
                         meals=all_meals)


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


# ═══════════════════════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# SERVE REACT BUILD (production)
# ═══════════════════════════════════════════════════════════════════

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    build_dir = os.path.join(os.path.dirname(__file__), 'frontend', 'build')
    file_path  = os.path.join(build_dir, path)
    if path and os.path.exists(file_path):
        return send_from_directory(build_dir, path)
    return send_from_directory(build_dir, 'index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)