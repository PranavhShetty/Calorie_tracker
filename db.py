"""
Database layer using ChromaDB
Handles all data storage and retrieval for calorie tracking
"""

import chromadb
from chromadb.config import Settings
from datetime import datetime
import json

# Initialize ChromaDB client
client = chromadb.PersistentClient(path="./chroma_data")

# Create collections
profile_collection = client.get_or_create_collection("user_profile")
food_entries_collection = client.get_or_create_collection("food_entries")
daily_summary_collection = client.get_or_create_collection("daily_summary")
saved_meals_collection = client.get_or_create_collection("saved_meals")


# ═══════════════════════════════════════════════════════════════════
# PROFILE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def save_profile(name: str, bmr: float):
    """Save or update user profile with BMR"""
    profile_data = {
        "name": name,
        "bmr": bmr,
        "created_at": datetime.now().isoformat()
    }
    
    profile_collection.upsert(
        ids=["user_profile"],
        documents=[json.dumps(profile_data)],
        metadatas=[profile_data]
    )
    print(f"✓ Profile saved: {name}, BMR: {bmr} kcal/day")
    return profile_data


def get_profile():
    """Get user profile"""
    try:
        result = profile_collection.get(ids=["user_profile"])
        if result['metadatas']:
            return result['metadatas'][0]
        return None
    except:
        return None


# ═══════════════════════════════════════════════════════════════════
# FOOD ENTRIES FUNCTIONS (Individual items eaten each day)
# ═══════════════════════════════════════════════════════════════════

def add_food_entry(date: str, food_name: str, calories: float, 
                   protein: float, carbs: float, fats: float, 
                   meal_type: str = "meal", is_saved_meal: bool = False):
    """
    Add a single food item eaten on a specific date
    
    Args:
        date: Date in YYYY-MM-DD format
        food_name: Name/description of the food
        calories: Calorie count
        protein: Protein in grams
        carbs: Carbs in grams
        fats: Fats in grams
        meal_type: breakfast/lunch/dinner/snack
        is_saved_meal: True if this came from saved meals library
    """
    
    # Generate unique ID using date + timestamp
    entry_id = f"{date}_{datetime.now().strftime('%H%M%S%f')}"
    
    entry_data = {
        "date": date,
        "food_name": food_name,
        "calories": float(calories),
        "protein": float(protein),
        "carbs": float(carbs),
        "fats": float(fats),
        "meal_type": meal_type,
        "is_saved_meal": is_saved_meal,
        "logged_at": datetime.now().isoformat()
    }
    
    food_entries_collection.add(
        ids=[entry_id],
        documents=[food_name],
        metadatas=[entry_data]
    )
    
    return entry_data


def get_food_entries_for_date(date: str):
    """Get all food items eaten on a specific date"""
    all_entries = food_entries_collection.get()
    
    if not all_entries['metadatas']:
        return []
    
    # Filter by date
    entries = [
        entry for entry in all_entries['metadatas']
        if entry['date'] == date
    ]
    
    # Sort by logged time
    entries.sort(key=lambda x: x['logged_at'])
    
    return entries


# ═══════════════════════════════════════════════════════════════════
# DAILY SUMMARY FUNCTIONS (Final deficit/surplus for the day)
# ═══════════════════════════════════════════════════════════════════

def calculate_and_save_daily_summary(date: str, workout_description: str = "", 
                                      calories_burned: float = 0, notes: str = ""):
    """
    Calculate totals from food entries and save daily summary
    
    Args:
        date: Date in YYYY-MM-DD format
        workout_description: What workout was done
        calories_burned: Calories burned from workout (calculated by LLM)
        notes: Any additional notes for the day
    """
    
    # Get profile for BMR
    profile = get_profile()
    if not profile:
        raise Exception("❌ No profile found. Run setup first.")
    
    bmr = profile['bmr']
    
    # Get all food entries for this date
    food_entries = get_food_entries_for_date(date)
    
    if not food_entries:
        print(f"⚠️  No food logged for {date}")
        return None
    
    # Calculate totals from all food entries
    total_calories_in = sum(entry['calories'] for entry in food_entries)
    total_protein = sum(entry['protein'] for entry in food_entries)
    total_carbs = sum(entry['carbs'] for entry in food_entries)
    total_fats = sum(entry['fats'] for entry in food_entries)
    
    # Calculate deficit/surplus
    total_burned = bmr + calories_burned
    deficit = total_burned - total_calories_in
    
    summary_data = {
        "date": date,
        "total_calories_in": round(total_calories_in, 1),
        "total_protein": round(total_protein, 1),
        "total_carbs": round(total_carbs, 1),
        "total_fats": round(total_fats, 1),
        "workout_description": workout_description,
        "calories_burned": float(calories_burned),
        "bmr": float(bmr),
        "total_burned": round(total_burned, 1),
        "deficit": round(deficit, 1),
        "notes": notes,
        "num_food_items": len(food_entries),
        "logged_at": datetime.now().isoformat()
    }
    
    daily_summary_collection.upsert(
        ids=[f"summary_{date}"],
        documents=[json.dumps(summary_data)],
        metadatas=[summary_data]
    )
    
    return summary_data


def get_daily_summary(date: str):
    """Get summary for a specific date"""
    try:
        result = daily_summary_collection.get(ids=[f"summary_{date}"])
        if result['metadatas']:
            return result['metadatas'][0]
        return None
    except:
        return None


def get_summaries_between_dates(start_date: str, end_date: str):
    """Get all daily summaries between two dates for weekly/monthly reports"""
    all_summaries = daily_summary_collection.get()
    
    if not all_summaries['metadatas']:
        return []
    
    # Filter by date range
    filtered = [
        summary for summary in all_summaries['metadatas']
        if start_date <= summary['date'] <= end_date
    ]
    
    # Sort by date
    filtered.sort(key=lambda x: x['date'])
    return filtered


# ═══════════════════════════════════════════════════════════════════
# SAVED MEALS LIBRARY (User's custom labeled meals)
# ═══════════════════════════════════════════════════════════════════

def save_custom_meal(label: str, calories: float, protein: float, carbs: float, 
                     fats: float, description: str = "", aliases: list = None):
    """
    Save a custom meal with user-defined label to the library
    Only called when user explicitly wants to save a meal
    
    Args:
        label: User's custom name (e.g., "Mum's dal rice", "Gym day breakfast")
        calories: Total calories
        protein: Protein in grams
        carbs: Carbs in grams
        fats: Fats in grams
        description: What's actually in the meal (optional)
        aliases: Other names user might use (e.g., ["mom's dal rice", "dal chawal"])
    """
    if aliases is None:
        aliases = []
    
    # Add the label to searchable names
    all_names = [label.lower()] + [alias.lower() for alias in aliases]
    
    meal_data = {
        "label": label,
        "calories": float(calories),
        "protein": float(protein),
        "carbs": float(carbs),
        "fats": float(fats),
        "description": description,
        "aliases": aliases,
        "created_at": datetime.now().isoformat()
    }
    
    # Use label as ID (lowercase, replace spaces with underscores)
    meal_id = label.lower().replace(" ", "_").replace("'", "")
    
    saved_meals_collection.upsert(
        ids=[meal_id],
        documents=[" ".join(all_names)],  # Searchable text
        metadatas=[meal_data]
    )
    
    print(f"✓ Saved meal: '{label}' to your library")
    return meal_data


def search_saved_meal(query: str):
    """
    Search for a saved meal by label or alias
    Returns None if not found
    """
    try:
        results = saved_meals_collection.query(
            query_texts=[query.lower()],
            n_results=1
        )
        
        if results['metadatas'] and results['metadatas'][0]:
            return results['metadatas'][0][0]
        return None
    except:
        return None


def get_all_saved_meals():
    """Get all saved meals from library"""
    all_meals = saved_meals_collection.get()
    if all_meals['metadatas']:
        # Sort by creation date
        meals = all_meals['metadatas']
        meals.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return meals
    return []


def delete_saved_meal(label: str):
    """Delete a meal from library"""
    meal_id = label.lower().replace(" ", "_").replace("'", "")
    try:
        saved_meals_collection.delete(ids=[meal_id])
        print(f"✓ Deleted '{label}' from your library")
        return True
    except:
        print(f"❌ Could not find '{label}' in library")
        return False


def update_saved_meal(label: str, calories: float = None, protein: float = None, 
                      carbs: float = None, fats: float = None):
    """Update macros for an existing saved meal"""
    meal = search_saved_meal(label)
    if not meal:
        print(f"❌ Meal '{label}' not found")
        return None
    
    # Update only provided values
    if calories is not None:
        meal['calories'] = float(calories)
    if protein is not None:
        meal['protein'] = float(protein)
    if carbs is not None:
        meal['carbs'] = float(carbs)
    if fats is not None:
        meal['fats'] = float(fats)
    
    # Re-save
    return save_custom_meal(
        label=meal['label'],
        calories=meal['calories'],
        protein=meal['protein'],
        carbs=meal['carbs'],
        fats=meal['fats'],
        description=meal.get('description', ''),
        aliases=meal.get('aliases', [])
    )


# ═══════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def print_daily_summary(date: str):
    """Pretty print daily summary"""
    summary = get_daily_summary(date)
    if not summary:
        print(f"No summary found for {date}")
        return
    
    print(f"\n{'='*50}")
    print(f"📊 Daily Summary for {date}")
    print(f"{'='*50}")
    print(f"Calories consumed:     {summary['total_calories_in']:>8.0f} kcal")
    print(f"  Protein:  {summary['total_protein']:>5.1f}g")
    print(f"  Carbs:    {summary['total_carbs']:>5.1f}g")
    print(f"  Fats:     {summary['total_fats']:>5.1f}g")
    print(f"\nBMR (resting):         {summary['bmr']:>8.0f} kcal")
    if summary['calories_burned'] > 0:
        print(f"Workout burn:          {summary['calories_burned']:>8.0f} kcal")
        print(f"  ({summary['workout_description']})")
    print(f"{'─'*50}")
    print(f"Total burned:          {summary['total_burned']:>8.0f} kcal")
    print(f"{'='*50}")
    
    if summary['deficit'] > 0:
        print(f"✓ DEFICIT:  {summary['deficit']:>8.0f} kcal  🔥")
    else:
        print(f"⚠️  SURPLUS: {abs(summary['deficit']):>8.0f} kcal")
    
    print(f"{'='*50}\n")
    
    if summary.get('notes'):
        print(f"Notes: {summary['notes']}\n")



def save_weight(date, weight):
    """Save weight entry for a specific date"""
    weight_collection = client.get_or_create_collection("weight_entries")
    
    weight_id = f"weight_{date}"
    
    weight_collection.upsert(
        ids=[weight_id],
        documents=[f"Weight entry for {date}"],
        metadatas=[{
            'date': date,
            'weight': weight,
            'logged_at': datetime.now().isoformat()
        }]
    )
    
    return {'date': date, 'weight': weight}


def get_weight_for_date(date):
    """Get weight entry for a specific date"""
    weight_collection = client.get_or_create_collection("weight_entries")
    
    try:
        result = weight_collection.get(ids=[f"weight_{date}"])
        if result and result['ids']:
            return result['metadatas'][0]
        return None
    except:
        return None


def get_weight_history(start_date, end_date):
    """Get all weight entries between two dates"""
    weight_collection = client.get_or_create_collection("weight_entries")
    
    try:
        all_results = weight_collection.get()
        
        if not all_results or not all_results['metadatas']:
            return []
        
        # Filter by date range
        weights = []
        for metadata in all_results['metadatas']:
            entry_date = metadata.get('date')
            if start_date <= entry_date <= end_date:
                weights.append(metadata)
        
        # Sort by date
        weights.sort(key=lambda x: x['date'])
        return weights
    except:
        return []