"""
LLM integration layer using Groq API
Handles all LLM-related tasks: food parsing, macro calculation, workout estimation
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Default model to use
MODEL = "llama-3.3-70b-versatile"  # Fast and accurate for our use case


# ═══════════════════════════════════════════════════════════════════
# FOOD MACRO CALCULATION
# ═══════════════════════════════════════════════════════════════════

def calculate_food_macros(food_description: str, user_context: str = ""):
    """
    Send food description to LLM and get back macros for each item
    
    Args:
        food_description: What the user ate (e.g., "2 rotis, dal, chicken curry")
        user_context: Additional context like region, preferences (optional)
    
    Returns:
        List of dicts with food items and their macros
        Example: [
            {
                "food_name": "2 rotis (80g)",
                "calories": 160,
                "protein": 6,
                "carbs": 32,
                "fats": 2,
                "notes": "Whole wheat rotis"
            },
            ...
        ]
    """
    
    # Build the prompt for the LLM
    prompt = f"""You are an expert Indian nutritionist. Calculate macros for the following foods.

USER ATE: {food_description}

{f"CONTEXT: {user_context}" if user_context else ""}

IMPORTANT RULES:
1. Break down into individual food items
2. Use typical Indian portion sizes (katori, plate, bowl, piece, etc.)
3. If weight is mentioned, use that for calculation
4. Be realistic with estimates for home-cooked Indian food
5. Include brief notes about assumptions

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{{
  "items": [
    {{
      "food_name": "exact description",
      "calories": number,
      "protein": number,
      "carbs": number,
      "fats": number,
      "notes": "brief calculation note"
    }}
  ]
}}

REFERENCE VALUES (use these for calculations):
- Roti (40g): ~120 kcal, 4g protein, 24g carbs, 2g fats
- Rice (1 plate, 200g cooked): ~260 kcal, 5g protein, 58g carbs, 0.5g fats
- Dal (1 katori, 150ml): ~150 kcal, 9g protein, 20g carbs, 4g fats
- Chicken breast (100g cooked): ~165 kcal, 31g protein, 0g carbs, 3.6g fats
- Paneer (100g): ~265 kcal, 18g protein, 3g carbs, 20g fats
- Milk (100ml): ~60 kcal, 3.2g protein, 4.8g carbs, 3.3g fats
- Butter (5g): ~36 kcal, 0g protein, 0g carbs, 4g fats
- Ghee (5g): ~45 kcal, 0g protein, 0g carbs, 5g fats
"""

    try:
        # Call Groq API
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise nutrition calculator. Always return valid JSON only, no extra text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature = more consistent results
            max_tokens=1000
        )
        
        # Extract the response text
        response_text = response.choices[0].message.content.strip()
        
        # Clean up response (remove markdown fences if present)
        if response_text.startswith("```"):
            # Remove ```json and ``` markers
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        response_text = response_text.strip()
        
        # Parse JSON
        result = json.loads(response_text)
        
        # Validate structure
        if "items" not in result:
            raise ValueError("Invalid response structure: missing 'items' key")
        
        # Add validation for each item
        for item in result["items"]:
            required_keys = ["food_name", "calories", "protein", "carbs", "fats"]
            if not all(key in item for key in required_keys):
                raise ValueError(f"Invalid item structure: {item}")
            
            # Ensure numeric values
            item["calories"] = float(item["calories"])
            item["protein"] = float(item["protein"])
            item["carbs"] = float(item["carbs"])
            item["fats"] = float(item["fats"])
        
        return result["items"]
    
    except json.JSONDecodeError as e:
        print(f"❌ LLM returned invalid JSON: {e}")
        print(f"Response was: {response_text[:200]}")
        return None
    
    except Exception as e:
        print(f"❌ Error calling LLM: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# WORKOUT CALORIE CALCULATION
# ═══════════════════════════════════════════════════════════════════

def calculate_workout_calories(workout_description: str, user_weight: float = 70):
    """
    Estimate calories burned from workout description
    
    Args:
        workout_description: What workout was done (e.g., "gym - legs and shoulders, 10 min jog")
        user_weight: User's weight in kg (affects calorie burn)
    
    Returns:
        Dict with workout breakdown and total calories burned
        Example: {
            "total_calories": 350,
            "breakdown": [
                {"activity": "weight training (legs, shoulders)", "duration_min": 60, "calories": 250},
                {"activity": "jogging", "duration_min": 10, "calories": 100}
            ],
            "notes": "Estimates based on moderate-high intensity"
        }
    """
    
    prompt = f"""You are a fitness expert. Estimate calories burned for this workout.

WORKOUT: {workout_description}
USER WEIGHT: {user_weight} kg

IMPORTANT RULES:
1. Break down into individual activities
2. Estimate duration if not specified (be realistic)
3. Use MET values for calculation (Metabolic Equivalent of Task)
4. Adjust for user weight
5. Be conservative with estimates (better to underestimate than overestimate)

Return ONLY valid JSON in this exact format (no markdown):
{{
  "total_calories": number,
  "breakdown": [
    {{
      "activity": "activity name",
      "duration_min": number,
      "calories": number
    }}
  ],
  "notes": "brief note about intensity assumptions"
}}

REFERENCE MET VALUES (use these):
- Weight training (moderate): 3.5 METs
- Weight training (vigorous): 6 METs
- Running/Jogging (8 km/h): 8 METs
- Running fast (12 km/h): 12 METs
- Cycling (moderate): 6 METs
- Cycling (vigorous): 10 METs
- Walking (5 km/h): 3.5 METs
- Swimming (moderate): 6 METs
- Yoga: 3 METs
- HIIT: 8 METs

FORMULA: Calories = (MET × weight_kg × duration_hours)
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise fitness calculator. Always return valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean markdown fences
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        response_text = response_text.strip()
        
        # Parse JSON
        result = json.loads(response_text)
        
        # Validate structure
        required_keys = ["total_calories", "breakdown"]
        if not all(key in result for key in required_keys):
            raise ValueError("Invalid response structure")
        
        # Ensure numeric values
        result["total_calories"] = float(result["total_calories"])
        for item in result["breakdown"]:
            item["calories"] = float(item["calories"])
            item["duration_min"] = int(item["duration_min"])
        
        return result
    
    except json.JSONDecodeError as e:
        print(f"❌ LLM returned invalid JSON: {e}")
        print(f"Response was: {response_text[:200]}")
        return None
    
    except Exception as e:
        print(f"❌ Error calculating workout calories: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# MACRO VALIDATION
# ═══════════════════════════════════════════════════════════════════

def transcribe_audio(audio_bytes: bytes, filename: str = 'audio.webm'):
    """Transcribe audio using Groq Whisper"""
    try:
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model='whisper-large-v3-turbo',
            language='en',
        )
        return transcription.text
    except Exception as e:
        print(f'❌ Error transcribing audio: {e}')
        return None


def validate_macros(calories: float, protein: float, carbs: float, fats: float):
    """
    Validate that macros roughly add up to calories
    Macros: 1g protein = 4 kcal, 1g carbs = 4 kcal, 1g fat = 9 kcal
    
    Returns:
        (is_valid: bool, calculated_calories: float, difference: float)
    """
    calculated_calories = (protein * 4) + (carbs * 4) + (fats * 9)
    difference = abs(calories - calculated_calories)
    
    # Allow 10% margin of error
    is_valid = difference <= (calories * 0.1)
    
    return is_valid, calculated_calories, difference


def check_macro_consistency(food_items: list):
    """
    Check if LLM-calculated macros are reasonable
    Prints warnings if something looks off
    """
    for item in food_items:
        is_valid, calc_cals, diff = validate_macros(
            item['calories'],
            item['protein'],
            item['carbs'],
            item['fats']
        )
        
        if not is_valid:
            print(f"⚠️  Warning: Macros for '{item['food_name']}' don't match calories")
            print(f"   Stated: {item['calories']} kcal")
            print(f"   Calculated from macros: {calc_cals:.0f} kcal")
            print(f"   Difference: {diff:.0f} kcal")


# ═══════════════════════════════════════════════════════════════════
# INTERACTIVE CONFIRMATION
# ═══════════════════════════════════════════════════════════════════

def confirm_food_items(food_items: list):
    """
    Show calculated macros to user and let them confirm or edit
    
    Returns:
        List of confirmed/edited food items
    """
    print(f"\n{'='*60}")
    print("🍽️  LLM CALCULATED MACROS:")
    print(f"{'='*60}\n")
    
    for i, item in enumerate(food_items, 1):
        print(f"{i}. {item['food_name']}")
        print(f"   Calories: {item['calories']:.0f} | Protein: {item['protein']:.1f}g | Carbs: {item['carbs']:.1f}g | Fats: {item['fats']:.1f}g")
        if item.get('notes'):
            print(f"   Note: {item['notes']}")
        print()
    
    # Check macro consistency
    check_macro_consistency(food_items)
    
    total_cals = sum(item['calories'] for item in food_items)
    total_protein = sum(item['protein'] for item in food_items)
    total_carbs = sum(item['carbs'] for item in food_items)
    total_fats = sum(item['fats'] for item in food_items)
    
    print(f"{'─'*60}")
    print(f"TOTAL: {total_cals:.0f} kcal | P: {total_protein:.1f}g | C: {total_carbs:.1f}g | F: {total_fats:.1f}g")
    print(f"{'='*60}\n")
    
    while True:
        choice = input("Looks good? (y/n/edit): ").strip().lower()
        
        if choice == 'y':
            return food_items
        
        elif choice == 'n':
            print("❌ Cancelled. Food not logged.")
            return None
        
        elif choice == 'edit':
            print("\nWhich item to edit? (enter number, or 'done' to finish)")
            item_num = input("→ ").strip()
            
            if item_num.lower() == 'done':
                return food_items
            
            try:
                idx = int(item_num) - 1
                if 0 <= idx < len(food_items):
                    item = food_items[idx]
                    print(f"\nEditing: {item['food_name']}")
                    
                    new_cal = input(f"Calories [{item['calories']:.0f}]: ").strip()
                    new_pro = input(f"Protein [{item['protein']:.1f}g]: ").strip()
                    new_carb = input(f"Carbs [{item['carbs']:.1f}g]: ").strip()
                    new_fat = input(f"Fats [{item['fats']:.1f}g]: ").strip()
                    
                    if new_cal: item['calories'] = float(new_cal)
                    if new_pro: item['protein'] = float(new_pro)
                    if new_carb: item['carbs'] = float(new_carb)
                    if new_fat: item['fats'] = float(new_fat)
                    
                    print(f"✓ Updated {item['food_name']}")
                else:
                    print("❌ Invalid number")
            except ValueError:
                print("❌ Invalid input")
        
        else:
            print("Please enter 'y', 'n', or 'edit'")


def confirm_workout(workout_data: dict):
    """
    Show workout calorie estimate and let user confirm or edit
    
    Returns:
        Final calories burned (float) or None if cancelled
    """
    print(f"\n{'='*60}")
    print("🏋️  WORKOUT CALORIES CALCULATED:")
    print(f"{'='*60}\n")
    
    for activity in workout_data['breakdown']:
        print(f"• {activity['activity']}")
        print(f"  Duration: {activity['duration_min']} min | Calories: {activity['calories']:.0f}")
    
    print(f"\n{'─'*60}")
    print(f"TOTAL BURNED: {workout_data['total_calories']:.0f} kcal")
    if workout_data.get('notes'):
        print(f"Note: {workout_data['notes']}")
    print(f"{'='*60}\n")
    
    while True:
        choice = input("Looks good? (y/n/edit): ").strip().lower()
        
        if choice == 'y':
            return workout_data['total_calories']
        
        elif choice == 'n':
            print("Using 0 calories burned.")
            return 0
        
        elif choice == 'edit':
            new_total = input(f"Enter correct total calories burned: ").strip()
            try:
                return float(new_total)
            except ValueError:
                print("❌ Invalid number")
        
        else:
            print("Please enter 'y', 'n', or 'edit'")