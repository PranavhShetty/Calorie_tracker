"""
Flask Web Application for CalorieTracker
"""

"""
Flask Web Application for CalorieTracker
"""

print("=" * 50)
print("STARTING APP.PY")
print("=" * 50)


from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS
import db
import llm
import meals
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
app.secret_key = os.urandom(24)  # For session management


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
    """API endpoint to save/update profile"""
    data = request.get_json()
    name = data.get('name')
    bmr = float(data.get('bmr'))
    
    db.save_profile(name, bmr)
    
    return jsonify({'success': True, 'profile': db.get_profile()})

@app.route('/api/profile', methods=['GET'])
def api_get_profile():
    """API endpoint to get user profile"""
    profile = db.get_profile()
    if profile:
        return jsonify(profile)
    return jsonify(None), 404


@app.route('/api/home-data', methods=['GET'])
def api_home_data():
    """API endpoint for home page data"""
    
    profile = db.get_profile()
    if not profile:
        return jsonify({'error': 'No profile'}), 404
    
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
    
    # Unlogged days
    unlogged_days = []
    for i in range(today.weekday() + 1):
        check_day = start_of_week + timedelta(days=i)
        check_day_str = check_day.strftime("%Y-%m-%d")
        day_summary = db.get_daily_summary(check_day_str)
        if not day_summary:
            unlogged_days.append({
                'date': check_day_str,
                'day_name': check_day.strftime("%A")
            })
    
    return jsonify({
        'summary': summary,
        'food_entries': food_entries,
        'weekly_deficit': weekly_deficit,
        'monthly_deficit': monthly_deficit,
        'unlogged_days': unlogged_days
    })

@app.route('/api/today-data', methods=['GET'])
def api_today_data():
    """API endpoint for today's detailed data"""
    
    profile = db.get_profile()
    if not profile:
        return jsonify({'error': 'No profile'}), 404
    
    today = datetime.now().strftime("%Y-%m-%d")
    summary = db.get_daily_summary(today)
    food_entries = db.get_food_entries_for_date(today)
    
    return jsonify({
        'summary': summary,
        'food_entries': food_entries
    })


@app.route('/api/week-data', methods=['GET'])
def api_week_data():
    """API endpoint for this week's data"""
    
    profile = db.get_profile()
    if not profile:
        return jsonify({'error': 'No profile'}), 404
    
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    
    # Generate all 7 days
    week_days = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        
        summary = db.get_daily_summary(day_str)
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
    
    # Calculate totals
    total_deficit = sum(day['summary']['deficit'] for day in week_days if day['summary'])
    days_logged = sum(1 for day in week_days if day['logged'])
    
    return jsonify({
        'week_days': week_days,
        'total_deficit': total_deficit,
        'days_logged': days_logged,
        'start_of_week': start_of_week.strftime("%Y-%m-%d"),
        'end_of_week': (start_of_week + timedelta(days=6)).strftime("%Y-%m-%d")
    })

@app.route('/api/reports-data', methods=['GET'])
def api_reports_data():
    """API endpoint for reports data"""
    
    profile = db.get_profile()
    if not profile:
        return jsonify({'error': 'No profile'}), 404
    
    today = datetime.now()
    
    # Weekly
    start_of_week = today - timedelta(days=today.weekday())
    weekly_summaries = db.get_summaries_between_dates(
        start_of_week.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d")
    )
    weekly_total = sum(s['deficit'] for s in weekly_summaries) if weekly_summaries else 0
    
    # Monthly
    start_of_month = today.replace(day=1)
    monthly_summaries = db.get_summaries_between_dates(
        start_of_month.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d")
    )
    monthly_total = sum(s['deficit'] for s in monthly_summaries) if monthly_summaries else 0
    
    return jsonify({
        'weekly_summaries': weekly_summaries,
        'monthly_summaries': monthly_summaries,
        'weekly_total': weekly_total,
        'monthly_total': monthly_total
    })

@app.route('/api/get-meals', methods=['GET'])
def api_get_meals():
    """API endpoint to get all saved meals"""
    meals = db.get_all_saved_meals()
    return jsonify({'meals': meals})



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
    """API endpoint to parse food description with LLM"""
    
    data = request.get_json()
    food_description = data.get('food_description', '')
    
    if not food_description:
        return jsonify({'error': 'No food description provided'}), 400
    
    # Check for saved meals first
    saved_items = []
    remaining_description = food_description
    
    all_saved_meals = db.get_all_saved_meals()
    
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
    """Save confirmed food items and workout to database"""
    
    data = request.get_json()
    food_items = data.get('food_items', [])
    workout_description = data.get('workout_description', '')
    calories_burned = float(data.get('calories_burned', 0))
    notes = data.get('notes', '')
    weight = data.get('weight')  # NEW: weight parameter
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # NEW: Save weight if provided
    if weight is not None:
        db.save_weight(today, float(weight))
    
    # Save each food entry
    for item in food_items:
        db.add_food_entry(
            date=today,
            food_name=item['food_name'],
            calories=item['calories'],
            protein=item['protein'],
            carbs=item['carbs'],
            fats=item['fats'],
            meal_type='meal',
            is_saved_meal=item.get('is_saved_meal', False)
        )
    
    # Calculate and save daily summary
    summary = db.calculate_and_save_daily_summary(
        date=today,
        workout_description=workout_description,
        calories_burned=calories_burned,
        notes=notes
    )
    
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


@app.route('/api/check-weight-today', methods=['GET'])
def api_check_weight_today():
    """Check if weight was logged today"""
    today = datetime.now().strftime("%Y-%m-%d")
    weight_entry = db.get_weight_for_date(today)
    
    return jsonify({'has_weight': weight_entry is not None})


@app.route('/api/weight-history', methods=['GET'])
def api_weight_history():
    """Get weight history for charts"""
    days = request.args.get('days', 30, type=int)
    
    today = datetime.now()
    start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    
    weights = db.get_weight_history(start_date, end_date)
    
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
    """Save food log for a specific date"""
    
    data = request.get_json()
    log_date = data.get('log_date')
    food_items = data.get('food_items', [])
    workout_description = data.get('workout_description', '')
    calories_burned = float(data.get('calories_burned', 0))
    notes = data.get('notes', '')
    
    # Save each food entry
    for item in food_items:
        db.add_food_entry(
            date=log_date,
            food_name=item['food_name'],
            calories=item['calories'],
            protein=item['protein'],
            carbs=item['carbs'],
            fats=item['fats'],
            meal_type='meal',
            is_saved_meal=item.get('is_saved_meal', False)
        )
    
    # Calculate and save daily summary
    summary = db.calculate_and_save_daily_summary(
        date=log_date,
        workout_description=workout_description,
        calories_burned=calories_burned,
        notes=notes
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
    """API to save a new custom meal"""
    
    data = request.get_json()
    
    db.save_custom_meal(
        label=data['label'],
        calories=float(data['calories']),
        protein=float(data['protein']),
        carbs=float(data['carbs']),
        fats=float(data['fats']),
        description=data.get('description', ''),
        aliases=data.get('aliases', [])
    )
    
    return jsonify({'success': True})


@app.route('/api/delete-meal', methods=['POST'])
def api_delete_meal():
    """API to delete a saved meal"""
    
    data = request.get_json()
    label = data.get('label')
    
    db.delete_saved_meal(label)
    
    return jsonify({'success': True})


# ═══════════════════════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)