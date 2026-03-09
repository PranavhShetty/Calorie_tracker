"""
Saved meals library management
Handles checking for saved meals and creating new ones
"""

import db
import llm


# ═══════════════════════════════════════════════════════════════════
# PARSE FOOD INPUT (Check saved meals first, then LLM)
# ═══════════════════════════════════════════════════════════════════

def parse_food_input(food_description: str):
    """
    Main function to parse user's food input
    
    Flow:
    1. Check if any saved meals are mentioned
    2. For saved meals → use stored macros
    3. For unknown foods → send to LLM
    4. Return combined list of all food items
    
    Args:
        food_description: What user ate (e.g., "mum's dal rice and 2 rotis")
    
    Returns:
        List of food items with macros, or None if cancelled
    """
    
    print(f"\n🔍 Analyzing: '{food_description}'")
    
    # Step 1: Check for saved meals
    saved_items = []
    remaining_description = food_description
    
    all_saved_meals = db.get_all_saved_meals()
    
    for saved_meal in all_saved_meals:
        label = saved_meal['label'].lower()
        aliases = [alias.lower() for alias in saved_meal.get('aliases', [])]
        all_names = [label] + aliases
        
        # Check if any name appears in user's input
        for name in all_names:
            if name in food_description.lower():
                # Found a saved meal!
                saved_items.append({
                    'food_name': saved_meal['label'],
                    'calories': saved_meal['calories'],
                    'protein': saved_meal['protein'],
                    'carbs': saved_meal['carbs'],
                    'fats': saved_meal['fats'],
                    'notes': f"From saved meals",
                    'is_saved_meal': True
                })
                
                # Remove this from description so LLM doesn't process it again
                remaining_description = remaining_description.lower().replace(name, "").strip()
                
                print(f"✓ Found saved meal: '{saved_meal['label']}'")
                break  # Found this meal, move to next
    
    # Step 2: Send remaining foods to LLM (if any)
    llm_items = []
    
    if remaining_description and remaining_description not in [',', 'and', '']:
        print(f"📤 Sending to LLM: '{remaining_description}'")
        llm_items = llm.calculate_food_macros(remaining_description)
        
        if llm_items is None:
            print("❌ LLM failed to calculate macros")
            return None
        
        # Mark as not from saved meals
        for item in llm_items:
            item['is_saved_meal'] = False
    
    # Step 3: Combine saved + LLM items
    all_items = saved_items + llm_items
    
    if not all_items:
        print("❌ No food items found")
        return None
    
    # Step 4: Show to user and confirm
    confirmed_items = llm.confirm_food_items(all_items)
    
    return confirmed_items


# ═══════════════════════════════════════════════════════════════════
# SAVE MEAL TO LIBRARY
# ═══════════════════════════════════════════════════════════════════

def offer_to_save_meal(food_items: list):
    """
    After logging food, ask user if they want to save any items as custom meals
    
    Args:
        food_items: The items that were just logged
    """
    
    # Only offer to save items that came from LLM (not already saved)
    llm_items = [item for item in food_items if not item.get('is_saved_meal', False)]
    
    if not llm_items:
        return  # All items were already saved meals
    
    print(f"\n{'─'*60}")
    print("💾 Would you like to save any of these as a custom meal?")
    print("   (For meals you eat regularly with the same macros)")
    print(f"{'─'*60}\n")
    
    for i, item in enumerate(llm_items, 1):
        print(f"{i}. {item['food_name']} ({item['calories']:.0f} kcal)")
    
    print("\nEnter numbers to save (comma separated), or press Enter to skip")
    choice = input("→ ").strip()
    
    if not choice:
        return  # User skipped
    
    # Parse choices
    try:
        indices = [int(x.strip()) - 1 for x in choice.split(',')]
    except ValueError:
        print("❌ Invalid input")
        return
    
    # Save each selected item
    for idx in indices:
        if 0 <= idx < len(llm_items):
            item = llm_items[idx]
            save_single_meal(item)


def save_single_meal(food_item: dict):
    """
    Interactive process to save a single meal with custom label and aliases
    
    Args:
        food_item: The food item dict from LLM
    """
    
    print(f"\n{'='*60}")
    print(f"💾 SAVING MEAL: {food_item['food_name']}")
    print(f"{'='*60}")
    print(f"Calories: {food_item['calories']:.0f} | P: {food_item['protein']:.1f}g | C: {food_item['carbs']:.1f}g | F: {food_item['fats']:.1f}g")
    print(f"{'─'*60}\n")
    
    # Get custom label
    label = input("What label do you want to use for this meal?\n(e.g., 'Mum's dal rice', 'Gym breakfast')\n→ ").strip()
    
    if not label:
        print("❌ No label provided, not saving")
        return
    
    # Check if label already exists
    existing = db.search_saved_meal(label)
    if existing:
        print(f"⚠️  '{label}' already exists in your library")
        overwrite = input("Overwrite? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("❌ Not saving")
            return
    
    # Get aliases (optional)
    print("\nAny other names you might use for this? (comma separated, or press Enter to skip)")
    print("Example: 'mom's dal rice, dal chawal'")
    aliases_input = input("→ ").strip()
    
    aliases = []
    if aliases_input:
        aliases = [alias.strip() for alias in aliases_input.split(',')]
    
    # Get description (optional)
    description = input("\nOptional description of what's in it (press Enter to skip):\n→ ").strip()
    
    # Save to database
    db.save_custom_meal(
        label=label,
        calories=food_item['calories'],
        protein=food_item['protein'],
        carbs=food_item['carbs'],
        fats=food_item['fats'],
        description=description,
        aliases=aliases
    )
    
    print(f"\n✓ Saved! Next time you say '{label}', these macros will be used automatically.\n")


# ═══════════════════════════════════════════════════════════════════
# VIEW SAVED MEALS
# ═══════════════════════════════════════════════════════════════════

def view_saved_meals():
    """Display all saved meals in library"""
    
    meals = db.get_all_saved_meals()
    
    if not meals:
        print("\n📭 No saved meals yet. Log some food and save your favorites!\n")
        return
    
    print(f"\n{'='*70}")
    print(f"📚 YOUR SAVED MEALS LIBRARY ({len(meals)} meals)")
    print(f"{'='*70}\n")
    
    for i, meal in enumerate(meals, 1):
        print(f"{i}. {meal['label']}")
        print(f"   {meal['calories']:.0f} kcal | P: {meal['protein']:.1f}g | C: {meal['carbs']:.1f}g | F: {meal['fats']:.1f}g")
        
        if meal.get('aliases'):
            print(f"   Aliases: {', '.join(meal['aliases'])}")
        
        if meal.get('description'):
            print(f"   Description: {meal['description']}")
        
        print()


def manage_saved_meals():
    """Interactive menu to view, edit, or delete saved meals"""
    
    while True:
        view_saved_meals()
        
        meals = db.get_all_saved_meals()
        if not meals:
            return
        
        print("Options: [v]iew | [d]elete | [q]uit")
        choice = input("→ ").strip().lower()
        
        if choice == 'q':
            break
        
        elif choice == 'v':
            continue  # Just shows the list again
        
        elif choice == 'd':
            meal_num = input("Which meal to delete? (enter number): ").strip()
            try:
                idx = int(meal_num) - 1
                if 0 <= idx < len(meals):
                    meal = meals[idx]
                    confirm = input(f"Delete '{meal['label']}'? (y/n): ").strip().lower()
                    if confirm == 'y':
                        db.delete_saved_meal(meal['label'])
                else:
                    print("❌ Invalid number")
            except ValueError:
                print("❌ Invalid input")
        
        else:
            print("❌ Invalid choice")