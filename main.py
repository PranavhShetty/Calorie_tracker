"""
CalorieTracker - Main CLI Application
LLM-powered calorie and macro tracking for Indian foods
"""

import sys
import db
import llm
import meals
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════════
# SETUP COMMAND
# ═══════════════════════════════════════════════════════════════════

def cmd_setup():
    """First-time setup - save user profile with BMR"""
    
    print(f"\n{'='*70}")
    print("🥗 CALORIE TRACKER - FIRST TIME SETUP")
    print(f"{'='*70}\n")
    
    name = input("Your name: ").strip() or "User"
    
    print(f"""
{'─'*70}
BMR (Basal Metabolic Rate) is the calories your body burns at rest.

Calculate it here: https://www.calculator.net/bmr-calculator.html

Example: 
- 70kg, 175cm, 30yr male = ~1750 kcal/day
- 60kg, 160cm, 25yr female = ~1400 kcal/day
{'─'*70}
""")
    
    while True:
        try:
            bmr = float(input("Enter your BMR (calories/day): ").strip())
            if bmr > 0:
                break
            print("❌ BMR must be positive")
        except ValueError:
            print("❌ Please enter a number")
    
    # Save profile
    db.save_profile(name, bmr)
    
    print(f"\n{'='*70}")
    print(f"✓ Setup complete! Welcome, {name}.")
    print(f"  Your BMR: {bmr:.0f} kcal/day")
    print(f"{'='*70}\n")
    print("Next step: python main.py log  — to log your first day!\n")


# ═══════════════════════════════════════════════════════════════════
# LOG COMMAND
# ═══════════════════════════════════════════════════════════════════

def cmd_log():
    """Log today's food and activity"""
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n{'='*70}")
    print(f"📝 LOGGING FOR {today}")
    print(f"{'='*70}\n")
    
    # Check profile exists
    profile = db.get_profile()
    if not profile:
        print("❌ No profile found. Run: python main.py setup\n")
        return
    
    # ── FOOD LOGGING ──────────────────────────────────────────────────
    
    print("What did you eat today?")
    print("Describe naturally (e.g., '2 rotis with dal, chicken curry, apple')")
    print("Or mention saved meals (e.g., 'mum's dal rice')")
    print()
    
    food_input = input("→ ").strip()
    
    if not food_input:
        print("❌ No food entered\n")
        return
    
    # Parse food (checks saved meals + LLM)
    food_items = meals.parse_food_input(food_input)
    
    if not food_items:
        print("❌ Food logging cancelled\n")
        return
    
    # Save each food entry to database
    for item in food_items:
        db.add_food_entry(
            date=today,
            food_name=item['food_name'],
            calories=item['calories'],
            protein=item['protein'],
            carbs=item['carbs'],
            fats=item['fats'],
            meal_type="meal",
            is_saved_meal=item.get('is_saved_meal', False)
        )
    
    print(f"\n✓ Food logged for {today}")
    
    # Offer to save new meals
    meals.offer_to_save_meal(food_items)
    
    # ── WORKOUT LOGGING ───────────────────────────────────────────────
    
    print(f"\n{'─'*70}")
    print("Did you work out today?")
    print("Describe your workout (e.g., 'gym - legs 60min, 10min jog')")
    print("Or type 'no' if you didn't work out")
    print()
    
    workout_input = input("→ ").strip()
    
    calories_burned = 0
    workout_description = ""
    
    if workout_input.lower() not in ['no', 'n', '']:
        # Get user weight for more accurate calculation
        weight_input = input("\nYour current weight in kg (or press Enter for 70kg): ").strip()
        try:
            weight = float(weight_input) if weight_input else 70
        except ValueError:
            weight = 70
        
        # Calculate workout calories
        workout_data = llm.calculate_workout_calories(workout_input, weight)
        
        if workout_data:
            calories_burned = llm.confirm_workout(workout_data)
            workout_description = workout_input
        else:
            print("⚠️  LLM failed to calculate workout. Enter manually:")
            try:
                calories_burned = float(input("Calories burned: ").strip())
                workout_description = workout_input
            except ValueError:
                print("❌ Invalid input, using 0 calories burned")
                calories_burned = 0
    
    # ── NOTES (OPTIONAL) ──────────────────────────────────────────────
    
    notes = input("\nAny notes for today? (optional, press Enter to skip): ").strip()
    
    # ── SAVE DAILY SUMMARY ────────────────────────────────────────────
    
    summary = db.calculate_and_save_daily_summary(
        date=today,
        workout_description=workout_description,
        calories_burned=calories_burned,
        notes=notes
    )
    
    # ── SHOW SUMMARY ──────────────────────────────────────────────────
    
    db.print_daily_summary(today)


# ═══════════════════════════════════════════════════════════════════
# STATUS COMMAND
# ═══════════════════════════════════════════════════════════════════

def cmd_status():
    """View today's summary"""
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    summary = db.get_daily_summary(today)
    
    if not summary:
        print(f"\n⚠️  No data logged for today ({today})")
        print("Run: python main.py log\n")
        return
    
    # Show food entries
    entries = db.get_food_entries_for_date(today)
    
    print(f"\n{'='*70}")
    print(f"📋 TODAY'S FOOD - {today}")
    print(f"{'='*70}\n")
    
    for entry in entries:
        saved_tag = " [SAVED]" if entry.get('is_saved_meal') else ""
        print(f"• {entry['food_name']}{saved_tag}")
        print(f"  {entry['calories']:.0f} kcal | P: {entry['protein']:.1f}g | C: {entry['carbs']:.1f}g | F: {entry['fats']:.1f}g")
        print()
    
    # Show summary
    db.print_daily_summary(today)


# ═══════════════════════════════════════════════════════════════════
# WEEKLY REPORT
# ═══════════════════════════════════════════════════════════════════

def cmd_weekly():
    """Show this week's deficit report"""
    
    today = datetime.now()
    # Start of week (Monday)
    start_of_week = today - timedelta(days=today.weekday())
    
    start_date = start_of_week.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    
    summaries = db.get_summaries_between_dates(start_date, end_date)
    
    if not summaries:
        print(f"\n⚠️  No data for this week ({start_date} to {end_date})\n")
        return
    
    print(f"\n{'='*70}")
    print(f"📅 WEEKLY REPORT - {start_date} to {end_date}")
    print(f"{'='*70}\n")
    
    print(f"{'Date':<12} {'In':>8} {'Burned':>8} {'Deficit':>8}")
    print(f"{'─'*70}")
    
    total_deficit = 0
    days_in_deficit = 0
    
    for summary in summaries:
        deficit = summary['deficit']
        total_deficit += deficit
        
        if deficit > 0:
            days_in_deficit += 1
            color = "✓"
        else:
            color = "⚠"
        
        print(f"{summary['date']:<12} {summary['total_calories_in']:>7.0f}k {summary['total_burned']:>7.0f}k {color} {deficit:>6.0f}k")
    
    print(f"{'─'*70}")
    print(f"\n📊 SUMMARY:")
    print(f"  Days logged: {len(summaries)}")
    print(f"  Days in deficit: {days_in_deficit}/{len(summaries)}")
    print(f"  Total deficit: {total_deficit:+.0f} kcal")
    
    # Fat loss estimate
    if total_deficit > 0:
        fat_loss_kg = total_deficit / 7700
        fat_loss_lbs = total_deficit / 3500
        print(f"\n  Estimated fat loss: ~{fat_loss_kg:.2f} kg / ~{fat_loss_lbs:.2f} lbs 🔥")
    else:
        surplus = abs(total_deficit)
        fat_gain_kg = surplus / 7700
        print(f"\n  ⚠️  Caloric surplus: {surplus:.0f} kcal (~{fat_gain_kg:.2f} kg potential gain)")
    
    print()


# ═══════════════════════════════════════════════════════════════════
# MONTHLY REPORT
# ═══════════════════════════════════════════════════════════════════

def cmd_monthly():
    """Show this month's deficit report"""
    
    today = datetime.now()
    start_of_month = today.replace(day=1)
    
    start_date = start_of_month.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    
    summaries = db.get_summaries_between_dates(start_date, end_date)
    
    if not summaries:
        print(f"\n⚠️  No data for this month ({start_date} to {end_date})\n")
        return
    
    print(f"\n{'='*70}")
    print(f"📆 MONTHLY REPORT - {start_date} to {end_date}")
    print(f"{'='*70}\n")
    
    print(f"{'Date':<12} {'In':>8} {'Burned':>8} {'Deficit':>8}")
    print(f"{'─'*70}")
    
    total_deficit = 0
    days_in_deficit = 0
    
    for summary in summaries:
        deficit = summary['deficit']
        total_deficit += deficit
        
        if deficit > 0:
            days_in_deficit += 1
            color = "✓"
        else:
            color = "⚠"
        
        print(f"{summary['date']:<12} {summary['total_calories_in']:>7.0f}k {summary['total_burned']:>7.0f}k {color} {deficit:>6.0f}k")
    
    print(f"{'─'*70}")
    print(f"\n📊 SUMMARY:")
    print(f"  Days logged: {len(summaries)}")
    print(f"  Days in deficit: {days_in_deficit}/{len(summaries)}")
    print(f"  Total deficit: {total_deficit:+.0f} kcal")
    
    # Fat loss estimate
    if total_deficit > 0:
        fat_loss_kg = total_deficit / 7700
        fat_loss_lbs = total_deficit / 3500
        print(f"\n  Estimated fat loss: ~{fat_loss_kg:.2f} kg / ~{fat_loss_lbs:.2f} lbs 🔥")
    else:
        surplus = abs(total_deficit)
        fat_gain_kg = surplus / 7700
        print(f"\n  ⚠️  Caloric surplus: {surplus:.0f} kcal (~{fat_gain_kg:.2f} kg potential gain)")
    
    print()


# ═══════════════════════════════════════════════════════════════════
# MEALS LIBRARY COMMAND
# ═══════════════════════════════════════════════════════════════════

def cmd_meals():
    """View and manage saved meals library"""
    meals.manage_saved_meals()


# ═══════════════════════════════════════════════════════════════════
# HELP / MENU
# ═══════════════════════════════════════════════════════════════════

def cmd_help():
    """Show available commands"""
    
    print(f"""
{'='*70}
🥗 CALORIE TRACKER - LLM-Powered Macro Tracking for Indian Foods
{'='*70}

COMMANDS:

  setup      First-time setup (name, BMR)
  log        Log today's food and workout
  status     View today's summary
  weekly     This week's deficit report
  monthly    This month's deficit report
  meals      View/manage saved meals library
  help       Show this menu

EXAMPLES:

  python main.py setup
  python main.py log
  python main.py weekly

{'='*70}
""")


# ═══════════════════════════════════════════════════════════════════
# MAIN CLI ROUTER
# ═══════════════════════════════════════════════════════════════════

COMMANDS = {
    'setup': cmd_setup,
    'log': cmd_log,
    'status': cmd_status,
    'weekly': cmd_weekly,
    'monthly': cmd_monthly,
    'meals': cmd_meals,
    'help': cmd_help,
}


def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        cmd_help()
        return
    
    command = sys.argv[1].lower()
    
    if command in COMMANDS:
        COMMANDS[command]()
    else:
        print(f"\n❌ Unknown command: {command}\n")
        cmd_help()


if __name__ == "__main__":
    main()