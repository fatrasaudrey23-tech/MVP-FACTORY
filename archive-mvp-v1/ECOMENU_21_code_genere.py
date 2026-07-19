import json
import random
import collections
import typing
import re

# --- Dummy Data ---
_DUMMY_RECIPES = [
    {
        "id": "R001",
        "name": "Oatmeal with Berries",
        "ingredients": [
            {"name": "Oats", "quantity": "50g"},
            {"name": "Milk", "quantity": "200ml"},
            {"name": "Mixed Berries", "quantity": "100g"}
        ],
        "dietary_tags": ["vegetarian", "gluten-free"],
        "allergens": ["dairy"],
        "meal_types": ["breakfast"],
        "prep_time_min": 5,
        "cook_time_min": 5,
        "servings": 1,
        "suitable_for_lunchbox": False
    },
    {
        "id": "R002",
        "name": "Chicken Salad Sandwich",
        "ingredients": [
            {"name": "Cooked Chicken Breast", "quantity": "150g"},
            {"name": "Mayonnaise", "quantity": "2 tbsp"},
            {"name": "Celery", "quantity": "1 stalk"},
            {"name": "Bread", "quantity": "2 slices"},
            {"name": "Lettuce", "quantity": "1 leaf"}
        ],
        "dietary_tags": ["high-protein"],
        "allergens": ["gluten", "eggs"],
        "meal_types": ["lunch"],
        "prep_time_min": 10,
        "cook_time_min": 0,
        "servings": 1,
        "suitable_for_lunchbox": True
    },
    {
        "id": "R003",
        "name": "Vegetable Stir-fry",
        "ingredients": [
            {"name": "Broccoli", "quantity": "200g"},
            {"name": "Carrots", "quantity": "150g"},
            {"name": "Bell Pepper", "quantity": "1 unit"},
            {"name": "Soy Sauce", "quantity": "3 tbsp"},
            {"name": "Rice", "quantity": "150g"},
            {"name": "Chicken Breast", "quantity": "200g"}
        ],
        "dietary_tags": ["high-fiber"],
        "allergens": ["soy"],
        "meal_types": ["dinner"],
        "prep_time_min": 15,
        "cook_time_min": 20,
        "servings": 2,
        "suitable_for_lunchbox": True
    },
    {
        "id": "R004",
        "name": "Lentil Soup",
        "ingredients": [
            {"name": "Red Lentils", "quantity": "200g"},
            {"name": "Onion", "quantity": "1 unit"},
            {"name": "Carrots", "quantity": "2 units"},
            {"name": "Vegetable Broth", "quantity": "1L"}
        ],
        "dietary_tags": ["vegetarian", "vegan", "gluten-free"],
        "allergens": [],
        "meal_types": ["lunch", "dinner"],
        "prep_time_min": 15,
        "cook_time_min": 30,
        "servings": 4,
        "suitable_for_lunchbox": True
    },
    {
        "id": "R005",
        "name": "Scrambled Eggs with Toast",
        "ingredients": [
            {"name": "Eggs", "quantity": "2 units"},
            {"name": "Milk", "quantity": "30ml"},
            {"name": "Bread", "quantity": "1 slice"},
            {"name": "Butter", "quantity": "10g"}
        ],
        "dietary_tags": ["vegetarian"],
        "allergens": ["eggs", "dairy", "gluten"],
        "meal_types": ["breakfast"],
        "prep_time_min": 3,
        "cook_time_min": 7,
        "servings": 1,
        "suitable_for_lunchbox": False
    },
    {
        "id": "R006",
        "name": "Salmon with Roasted Vegetables",
        "ingredients": [
            {"name": "Salmon Fillet", "quantity": "150g"},
            {"name": "Asparagus", "quantity": "100g"},
            {"name": "Sweet Potato", "quantity": "200g"},
            {"name": "Olive Oil", "quantity": "1 tbsp"}
        ],
        "dietary_tags": ["high-protein", "gluten-free"],
        "allergens": ["fish"],
        "meal_types": ["dinner"],
        "prep_time_min": 10,
        "cook_time_min": 25,
        "servings": 1,
        "suitable_for_lunchbox": True
    },
    {
        "id": "R007",
        "name": "Yogurt with Granola",
        "ingredients": [
            {"name": "Greek Yogurt", "quantity": "150g"},
            {"name": "Granola", "quantity": "50g"},
            {"name": "Honey", "quantity": "1 tbsp"}
        ],
        "dietary_tags": ["vegetarian"],
        "allergens": ["dairy", "nuts"],
        "meal_types": ["breakfast"],
        "prep_time_min": 2,
        "cook_time_min": 0,
        "servings": 1,
        "suitable_for_lunchbox": False
    },
    {
        "id": "R008",
        "name": "Pasta with Tomato Sauce",
        "ingredients": [
            {"name": "Pasta", "quantity": "100g"},
            {"name": "Canned Tomatoes", "quantity": "200g"},
            {"name": "Garlic", "quantity": "2 cloves"},
            {"name": "Olive Oil", "quantity": "1 tbsp"}
        ],
        "dietary_tags": ["vegetarian", "vegan"],
        "allergens": ["gluten"],
        "meal_types": ["dinner"],
        "prep_time_min": 10,
        "cook_time_min": 20,
        "servings": 2,
        "suitable_for_lunchbox": True
    }
]

_DUMMY_USER_PREFERENCES = {
    "user_id": "user123",
    "dietary_restrictions": ["vegetarian"],
    "allergies": ["nuts", "gluten"],
    "disliked_ingredients": ["celery"],
    "max_prep_time_min": 20,
    "max_cook_time_min": 40,
    "allow_lunchbox_from_dinner": True
}

# --- 1. Gestion des données (Recettes et Préférences) ---

def load_recipes(filepath: str) -> typing.List[typing.Dict]:
    """
    Charge la base de données des recettes à partir d'un fichier (ex: JSON).
    Si le fichier n'existe pas, utilise des données factices.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Recipe file '{filepath}' not found. Using dummy recipes.")
        return _DUMMY_RECIPES
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{filepath}'. Using dummy recipes.")
        return _DUMMY_RECIPES

def load_user_preferences(user_id: str) -> typing.Dict:
    """
    Charge les préférences spécifiques d'un utilisateur (restrictions alimentaires, allergies,
    ingrédients préférés/détestés, temps de cuisson max, etc.).
    Pour cet exemple, retourne des préférences factices.
    """
    print(f"Loading preferences for user '{user_id}'. Using dummy preferences.")
    return _DUMMY_USER_PREFERENCES

# --- 2. Filtrage et Sélection des Recettes ---

def filter_recipes(recipes: typing.List[typing.Dict], preferences: typing.Dict) -> typing.List[typing.Dict]:
    """
    Filtre la liste complète des recettes en fonction des préférences de l'utilisateur.
    """
    filtered = []
    for recipe in recipes:
        # Check dietary restrictions
        if preferences.get("dietary_restrictions"):
            if not all(tag in recipe.get("dietary_tags", []) for tag in preferences["dietary_restrictions"]):
                continue

        # Check allergies
        if preferences.get("allergies"):
            if any(allergen in recipe.get("allergens", []) for allergen in preferences["allergies"]):
                continue

        # Check disliked ingredients
        if preferences.get("disliked_ingredients"):
            recipe_ingredients = [ing["name"].lower() for ing in recipe.get("ingredients", [])]
            if any(disliked.lower() in recipe_ingredients for disliked in preferences["disliked_ingredients"]):
                continue

        # Check max prep time
        if preferences.get("max_prep_time_min") is not None:
            if recipe.get("prep_time_min", 0) > preferences["max_prep_time_min"]:
                continue

        # Check max cook time
        if preferences.get("max_cook_time_min") is not None:
            if recipe.get("cook_time_min", 0) > preferences["max_cook_time_min"]:
                continue

        filtered.append(recipe)
    return filtered

def select_recipe(available_recipes: typing.List[typing.Dict], meal_type: str, 
                  excluded_recipes_ids: typing.Optional[typing.Set[str]] = None) -> typing.Optional[typing.Dict]:
    """
    Sélectionne une recette aléatoirement parmi les recettes disponibles pour un type de repas donné,
    en évitant les recettes déjà sélectionnées pour la période proche.
    """
    if excluded_recipes_ids is None:
        excluded_recipes_ids = set()

    eligible_recipes = [
        r for r in available_recipes
        if meal_type in r.get("meal_types", []) and r["id"] not in excluded_recipes_ids
    ]

    if not eligible_recipes:
        return None

    return random.choice(eligible_recipes)

# --- 3. Logique de Planification des Repas ---

def plan_lunchbox(dinner_recipe: typing.Dict, preferences: typing.Dict) -> typing.Optional[typing.Dict]:
    """
    Détermine si une recette de dîner est adaptée pour une lunch box le lendemain,
    en fonction de ses propriétés et des préférences utilisateur.
    """
    if not preferences.get("allow_lunchbox_from_dinner"):
        return None

    if not dinner_recipe.get("suitable_for_lunchbox"):
        return None

    if dinner_recipe.get("servings", 1) < 2:
        return None

    return {
        "recipe": dinner_recipe,
        "is_lunchbox": True,
        "meal_type": "lunch"
    }

def generate_daily_plan(available_recipes: typing.List[typing.Dict], preferences: typing.Dict, 
                         previous_day_dinner: typing.Optional[typing.Dict] = None) -> typing.Dict:
    """
    Génère un plan de repas pour une seule journée (petit-déjeuner, déjeuner, dîner),
    en tenant compte de l'éventuelle lunch box du dîner précédent.
    """
    daily_plan = {}
    excluded_for_day_ids = set()

    # Breakfast
    breakfast_recipe = select_recipe(available_recipes, "breakfast", excluded_for_day_ids)
    if breakfast_recipe:
        daily_plan['breakfast'] = {'recipe': breakfast_recipe, 'is_lunchbox': False}
        excluded_for_day_ids.add(breakfast_recipe['id'])

    # Lunch
    lunch_recipe_info = None
    if previous_day_dinner:
        lunch_from_dinner = plan_lunchbox(previous_day_dinner, preferences)
        if lunch_from_dinner:
            lunch_recipe_info = lunch_from_dinner
    
    if not lunch_recipe_info:
        selected_lunch = select_recipe(available_recipes, "lunch", excluded_for_day_ids)
        if selected_lunch:
            lunch_recipe_info = {'recipe': selected_lunch, 'is_lunchbox': False}
            excluded_for_day_ids.add(selected_lunch['id'])
    
    if lunch_recipe_info:
        daily_plan['lunch'] = lunch_recipe_info

    # Dinner
    dinner_recipe = select_recipe(available_recipes, "dinner", excluded_for_day_ids)
    if dinner_recipe:
        daily_plan['dinner'] = {'recipe': dinner_recipe, 'is_lunchbox': False}
        excluded_for_day_ids.add(dinner_recipe['id'])

        # Plan next day's lunchbox if dinner is suitable
        lunch_next_day = plan_lunchbox(dinner_recipe, preferences)
        if lunch_next_day:
            daily_plan['lunch_next_day'] = lunch_next_day
    
    return daily_plan

def generate_full_meal_plan(num_days: int, recipes: typing.List[typing.Dict], preferences: typing.Dict) -> typing.List[typing.Dict]:
    """
    Orchestre la génération du plan de repas complet pour un nombre spécifié de jours.
    """
    full_plan = []
    filtered_recipes = filter_recipes(recipes, preferences)
    
    previous_day_dinner = None

    for day in range(num_days):
        print(f"Generating plan for Day {day + 1}...")
        day_plan = generate_daily_plan(filtered_recipes, preferences, previous_day_dinner)
        full_plan.append(day_plan)
        
        if 'dinner' in day_plan:
            previous_day_dinner = day_plan['dinner']['recipe']
        else:
            previous_day_dinner = None

    return full_plan

# --- 4. Utilitaires et Sortie ---

def _parse_quantity(quantity_str: str) -> typing.Tuple[typing.Optional[float], typing.Optional[str]]:
    """Helper to parse a quantity string into a number and a unit."""
    match = re.match(r"(\d+(\.\d+)?)\s*([a-zA-Z]+)?", quantity_str.strip())
    if match:
        value = float(match.group(1))
        unit = match.group(3) if match.group(3) else ""
        return value, unit.lower()
    return None, None

def calculate_shopping_list(full_meal_plan: typing.List[typing.Dict]) -> typing.Dict:
    """
    Génère une liste de courses consolidée à partir du plan de repas complet,
    en agrégeant les quantités d'ingrédients.
    """
    shopping_list_raw = collections.defaultdict(list)

    for day_plan in full_meal_plan:
        # FIX: The loop should only consider meals that require new ingredients.
        # 'lunch_next_day' is a reference to a dinner already planned/cooked, not a new shopping item.
        for meal_type in ['breakfast', 'lunch', 'dinner']:
            meal_info = day_plan.get(meal_type)
            # Only count ingredients if the meal is not a lunchbox (i.e., not leftovers)
            if meal_info and not meal_info.get('is_lunchbox', False):
                recipe = meal_info.get('recipe')
                if recipe and recipe.get('ingredients'):
                    for ingredient in recipe['ingredients']:
                        name = ingredient['name'].lower()
                        quantity = ingredient['quantity']
                        shopping_list_raw[name].append(quantity)
    
    final_shopping_list = {}
    for ingredient, quantities_list in shopping_list_raw.items():
        numerical_quantities = []
        units = set()
        all_parsable = True

        for q_str in quantities_list:
            value, unit = _parse_quantity(q_str)
            if value is not None:
                numerical_quantities.append(value)
                units.add(unit)
            else:
                all_parsable = False
                break
        
        if all_parsable and len(units) == 1:
            total_value = sum(numerical_quantities)
            unit_str = units.pop() if units else ""
            final_shopping_list[ingredient] = f"{total_value}{unit_str}"
        elif all_parsable and len(units) > 1:
            final_shopping_list[ingredient] = ", ".join(quantities_list)
        else:
            final_shopping_list[ingredient] = ", ".join(quantities_list)

    return final_shopping_list

def display_meal_plan(full_meal_plan: typing.List[typing.Dict]) -> str:
    """
    Formate le plan de repas complet en une chaîne de caractères lisible pour l'affichage.
    """
    output = []
    for i, day_plan in enumerate(full_meal_plan):
        output.append(f"\n--- Day {i+1} ---")
        
        for meal_type in ['breakfast', 'lunch', 'dinner']:
            meal_info = day_plan.get(meal_type)
            if meal_info:
                recipe = meal_info['recipe']
                is_lunchbox = meal_info.get('is_lunchbox', False)
                if is_lunchbox:
                    output.append(f"  {meal_type.capitalize()}: {recipe['name']} (Lunchbox - leftovers from previous dinner)")
                else:
                    output.append(f"  {meal_type.capitalize()}: {recipe['name']}")
            else:
                output.append(f"  {meal_type.capitalize()}: No meal planned")
        
        if 'lunch_next_day' in day_plan:
            lunch_next_day_info = day_plan['lunch_next_day']
            if lunch_next_day_info and lunch_next_day_info.get('is_lunchbox'):
                output.append(f"  --> Lunchbox for Day {i+2}: {lunch_next_day_info['recipe']['name']} (planned from this dinner)")
            
    return "\n".join(output)

if __name__ == "__main__":
    try:
        with open("recipes.json", "w", encoding='utf-8') as f:
            json.dump(_DUMMY_RECIPES, f, indent=4)
        with open("user_preferences.json", "w", encoding='utf-8') as f:
            json.dump(_DUMMY_USER_PREFERENCES, f, indent=4)
    except IOError as e:
        print(f"Could not write dummy data files: {e}. Proceeding with in-memory dummy data.")

    all_recipes = load_recipes("recipes.json")
    user_prefs = load_user_preferences("user_preferences.json")

    num_days_to_plan = 3
    print(f"\nGenerating meal plan for {num_days_to_plan} days...")
    meal_plan = generate_full_meal_plan(num_days_to_plan, all_recipes, user_prefs)

    print("\n--- Generated Meal Plan ---")
    print(display_meal_plan(meal_plan))

    print("\n--- Shopping List ---")
    shopping_list = calculate_shopping_list(meal_plan)
    for item, quantity in shopping_list.items():
        print(f"- {item.capitalize()}: {quantity}")