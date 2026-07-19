import json
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter
import random

# --- A. Fonctions de chargement et de préparation des données ---

def load_data(filepath: str) -> Dict:
    """
    Charge les données brutes (recettes, ingrédients ou contraintes) depuis un fichier JSON.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def prepare_recipes(raw_recipes_data: List[Dict], ingredients_map: Dict[str, Dict]) -> List[Dict]:
    """
    Traite la liste de recettes brutes pour y ajouter des informations dérivées
    (ex: calcul des valeurs nutritionnelles par recette à partir des ingrédients).
    """
    enriched_recipes = []
    for recipe in raw_recipes_data:
        total_calories = 0.0
        total_protein = 0.0
        all_allergens = set()
        
        for ingredient_item in recipe.get('ingredients', []):
            ing_id = ingredient_item.get('ingredient_id')
            quantity_grams = ingredient_item.get('quantity_grams', 0)
            
            ingredient_info = ingredients_map.get(ing_id)
            if ingredient_info:
                # Assuming nutritional values are per 100g
                total_calories += (ingredient_info.get('calories_per_100g', 0) / 100.0) * quantity_grams
                total_protein += (ingredient_info.get('protein_per_100g', 0) / 100.0) * quantity_grams
                all_allergens.update(ingredient_info.get('allergens', []))
        
        recipe['total_calories'] = round(total_calories, 2)
        recipe['total_protein'] = round(total_protein, 2)
        recipe['allergens'] = list(all_allergens)
        enriched_recipes.append(recipe)
    return enriched_recipes

def parse_constraints(raw_constraints_data: Dict) -> Dict[str, Any]:
    """
    Analyse et structure les définitions de contraintes pour faciliter leur application.
    Peut inclure la validation du format des contraintes.
    """
    # For this implementation, we assume raw_constraints_data is already well-structured
    # or requires minimal parsing. We'll add some default values if missing.
    
    constraints = defaultdict(lambda: None)
    constraints.update(raw_constraints_data)

    # Example of structuring/defaulting
    if 'daily_calories' not in constraints:
        constraints['daily_calories'] = {'min': 1500, 'max': 2500}
    if 'daily_protein_min' not in constraints:
        constraints['daily_protein_min'] = 50
    if 'avoid_allergens' not in constraints:
        constraints['avoid_allergens'] = []
    if 'meal_type_diversity' not in constraints:
        constraints['meal_type_diversity'] = {'max_same_type_per_week': {}}
    if 'max_recipe_repetition_per_week' not in constraints:
        constraints['max_recipe_repetition_per_week'] = 1 # A recipe can be used once per week by default
    if 'meal_slot_types' not in constraints:
        # Default mapping for meal slots to recipe types
        constraints['meal_slot_types'] = {
            'breakfast': ['breakfast'],
            'lunch': ['lunch'],
            'dinner': ['dinner']
        }

    return dict(constraints)

# --- B. Fonctions de vérification des contraintes ---

def _check_recipe_suitability(recipe: Dict, meal_slot_type: str, current_context: Dict[str, Any], constraints: Dict[str, Any]) -> bool:
    """
    Vérifie si une recette individuelle est appropriée pour un type de repas donné et un contexte spécifique.
    """
    # 1. Check meal slot compatibility
    allowed_recipe_types = constraints.get('meal_slot_types', {}).get(meal_slot_type, [])
    if recipe.get('type') not in allowed_recipe_types:
        # print(f"DEBUG: Recipe {recipe['name']} (type {recipe['type']}) not suitable for {meal_slot_type}")
        return False

    # 2. Check allergens
    avoid_allergens = set(constraints.get('avoid_allergens', []))
    recipe_allergens = set(recipe.get('allergens', []))
    if avoid_allergens.intersection(recipe_allergens):
        # print(f"DEBUG: Recipe {recipe['name']} contains allergens {recipe_allergens.intersection(avoid_allergens)}")
        return False

    # 3. Check preferences (example: include/exclude tags)
    # This is a placeholder for future complex preference rules
    # For now, no specific preference rules beyond basic tags are implemented.

    # 4. Check weekly repetition (if applicable, for the specific recipe)
    # This check is performed here to filter candidates early, but full weekly check is in _check_full_menu_constraints
    recipe_id = recipe['id']
    if current_context.get('recipe_counts_week', {}).get(recipe_id, 0) >= constraints.get('max_recipe_repetition_per_week', 1):
        # print(f"DEBUG: Recipe {recipe['name']} already used too many times this week.")
        return False

    return True

def _check_day_constraints(day_menu: List[Dict], current_context: Dict[str, Any], constraints: Dict[str, Any]) -> bool:
    """
    Vérifie si l'ensemble des repas d'une journée respecte les contraintes quotidiennes.
    """
    if not day_menu:
        return True # An empty day menu is trivially valid

    total_calories = sum(r['total_calories'] for r in day_menu)
    total_protein = sum(r['total_protein'] for r in day_menu)

    # 1. Daily calories
    daily_cal_min = constraints.get('daily_calories', {}).get('min', 0)
    daily_cal_max = constraints.get('daily_calories', {}).get('max', float('inf'))
    if not (daily_cal_min <= total_calories <= daily_cal_max):
        # print(f"DEBUG: Daily calories {total_calories} out of range [{daily_cal_min}, {daily_cal_max}]")
        return False

    # 2. Daily protein
    daily_protein_min = constraints.get('daily_protein_min', 0)
    if total_protein < daily_protein_min:
        # print(f"DEBUG: Daily protein {total_protein} below min {daily_protein_min}")
        return False

    # 3. Diversity of dishes for the day (e.g., no two main dishes of same type)
    # This is currently not explicitly in constraints, but could be added.
    # For now, let's assume no explicit daily diversity beyond meal slot types.

    return True

def _check_full_menu_constraints(full_menu: List[List[Dict]], constraints: Dict[str, Any]) -> bool:
    """
    Vérifie si le menu complet généré (sur plusieurs jours) respecte les contraintes hebdomadaires ou globales.
    """
    if not full_menu:
        return True

    all_recipes_in_menu = [recipe for day in full_menu for recipe in day]

    # 1. Weekly recipe repetition
    recipe_counts = Counter(r['id'] for r in all_recipes_in_menu)
    max_repetition = constraints.get('max_recipe_repetition_per_week', 1)
    if any(count > max_repetition for count in recipe_counts.values()):
        # print(f"DEBUG: Weekly recipe repetition constraint violated. Counts: {recipe_counts}")
        return False

    # 2. Meal type diversity (e.g., max X breakfasts per week)
    meal_type_diversity_limits = constraints.get('meal_type_diversity', {}).get('max_same_type_per_week', {})
    meal_type_counts = Counter(r['type'] for r in all_recipes_in_menu)
    for meal_type, limit in meal_type_diversity_limits.items():
        if meal_type_counts.get(meal_type, 0) > limit:
            # print(f"DEBUG: Weekly meal type diversity violated for {meal_type}. Count: {meal_type_counts[meal_type]}, Limit: {limit}")
            return False

    # 3. Global nutritional targets (e.g., total weekly calories/protein)
    # This is a placeholder; currently not explicitly defined in constraints.json example.
    # total_weekly_calories = sum(r['total_calories'] for r in all_recipes_in_menu)
    # total_weekly_protein = sum(r['total_protein'] for r in all_recipes_in_menu)
    # ... check against weekly targets ...

    return True

# --- C. Fonction principale de génération de menu ---

def generate_constrained_menu(
    all_recipes: List[Dict],
    all_ingredients: Dict[str, Dict], # Not directly used in current implementation, but kept for signature
    constraints: Dict[str, Any],
    num_days: int = 7,
    meal_slots: Optional[List[str]] = None
) -> Optional[List[List[Dict]]]:
    """
    Fonction principale qui orchestre la génération d'un menu complet en respectant les contraintes.
    Implémente un algorithme de backtracking.
    """
    if meal_slots is None:
        meal_slots = ['breakfast', 'lunch', 'dinner']

    # Map recipe IDs to full recipe dicts for quicker lookup
    recipes_by_id = {r['id']: r for r in all_recipes}

    # Helper function for recursive backtracking
    def _generate_menu_recursive(
        current_day_idx: int,
        current_meal_slot_idx: int,
        current_menu: List[List[Dict]],
        context: Dict[str, Any]
    ) -> Optional[List[List[Dict]]]:

        # Base case: All days and meal slots are filled
        if current_day_idx == num_days:
            # Final check of the full menu
            if _check_full_menu_constraints(current_menu, constraints):
                return current_menu
            else:
                return None

        # Determine current meal slot
        if current_meal_slot_idx == len(meal_slots):
            # End of day, move to next day
            # Perform a daily check before moving to the next day
            if not _check_day_constraints(current_menu[current_day_idx], context, constraints):
                return None # Day's menu violates constraints
            
            # Reset daily context for the new day
            next_day_context = {
                'recipe_counts_week': context['recipe_counts_week'], # Keep weekly counts
                'selected_recipes_week': context['selected_recipes_week'] # Keep weekly selected recipes
            }
            return _generate_menu_recursive(current_day_idx + 1, 0, current_menu + [[]], next_day_context)

        current_slot_type = meal_slots[current_meal_slot_idx]
        
        # Filter and shuffle recipes to try different combinations
        candidate_recipes = [
            recipe for recipe in all_recipes
            if _check_recipe_suitability(recipe, current_slot_type, context, constraints)
        ]
        random.shuffle(candidate_recipes) # Introduce some randomness

        for recipe in candidate_recipes:
            # Try to add this recipe
            
            # Create a deep copy of the current menu and context for backtracking
            next_menu = [list(day) for day in current_menu]
            next_menu[current_day_idx].append(recipe)
            
            next_context = {
                'recipe_counts_week': Counter(context['recipe_counts_week']),
                'selected_recipes_week': list(context['selected_recipes_week'])
            }
            next_context['recipe_counts_week'][recipe['id']] += 1
            next_context['selected_recipes_week'].append(recipe)

            # Recursive call for the next meal slot
            result = _generate_menu_recursive(
                current_day_idx,
                current_meal_slot_idx + 1,
                next_menu,
                next_context
            )
            if result is not None:
                return result # Found a valid menu

        return None # No recipe worked for this slot, backtrack

    # Initial call to the recursive helper
    initial_context: Dict[str, Any] = {
        'recipe_counts_week': Counter(),
        'selected_recipes_week': []
    }
    return _generate_menu_recursive(0, 0, [[]], initial_context)

# --- D. Fonctions utilitaires ---

def calculate_menu_summary(menu: List[List[Dict]], recipes_map: Dict[str, Dict], ingredients_map: Dict[str, Dict]) -> Dict:
    """
    Calcule un résumé global du menu généré (ex: coût total, bilan nutritionnel hebdomadaire).
    """
    total_calories_week = 0.0
    total_protein_week = 0.0
    all_ingredients_used = Counter()
    
    for day_menu in menu:
        for recipe in day_menu:
            total_calories_week += recipe.get('total_calories', 0)
            total_protein_week += recipe.get('total_protein', 0)
            
            for ing_item in recipe.get('ingredients', []):
                ing_id = ing_item['ingredient_id']
                quantity = ing_item['quantity_grams']
                all_ingredients_used[ing_id] += quantity
                
    # Convert ingredient IDs to names for summary
    ingredients_summary_by_name = {}
    for ing_id, quantity in all_ingredients_used.items():
        ing_name = ingredients_map.get(ing_id, {}).get('name', f"Unknown Ingredient ({ing_id})")
        ingredients_summary_by_name[ing_name] = round(quantity, 2)

    summary = {
        'total_calories_week': round(total_calories_week, 2),
        'total_protein_week': round(total_protein_week, 2),
        'ingredients_needed_grams': ingredients_summary_by_name,
        'num_recipes_per_day': [len(day) for day in menu],
        'num_days_generated': len(menu)
    }
    return summary

def display_menu(menu: List[List[Dict]]) -> None:
    """
    Affiche le menu généré de manière lisible dans la console.
    """
    if menu is None:
        print("Aucun menu valide n'a pu être généré avec les contraintes spécifiées.")
        return

    print("\n--- Menu Généré ---")
    for i, day_menu in enumerate(menu):
        print(f"\nJour {i + 1}:")
        if not day_menu:
            print("  (Aucun repas planifié)")
            continue
        for j, recipe in enumerate(day_menu):
            print(f"  {j + 1}. {recipe.get('name', 'Recette Inconnue')} ({recipe.get('type', 'N/A')})")
            print(f"     Calories: {recipe.get('total_calories', 'N/A')} kcal, Protéines: {recipe.get('total_protein', 'N/A')}g")
            if recipe.get('allergens'):
                print(f"     Allergènes: {', '.join(recipe['allergens'])}")
    print("\n-------------------\n")

# --- Main execution block (for demonstration) ---
if __name__ == "__main__":
    # Create dummy JSON files for demonstration
    # In a real scenario, these files would already exist.
    
    # recipes.json
    with open('recipes.json', 'w', encoding='utf-8') as f:
        json.dump([
            {"id": "rec1", "name": "Omelette", "type": "breakfast", "tags": ["egg", "protein"], "ingredients": [{"ingredient_id": "ing1", "quantity_grams": 100}, {"ingredient_id": "ing2", "quantity_grams": 50}]},
            {"id": "rec2", "name": "Salade Composée", "type": "lunch", "tags": ["vegetable", "light"], "ingredients": [{"ingredient_id": "ing3", "quantity_grams": 150}, {"ingredient_id": "ing4", "quantity_grams": 80}]},
            {"id": "rec3", "name": "Poulet Rôti et Légumes", "type": "dinner", "tags": ["meat", "protein"], "ingredients": [{"ingredient_id": "ing5", "quantity_grams": 200}, {"ingredient_id": "ing3", "quantity_grams": 100}]},
            {"id": "rec4", "name": "Yaourt aux fruits", "type": "breakfast", "tags": ["dairy", "fruit"], "ingredients": [{"ingredient_id": "ing6", "quantity_grams": 150}, {"ingredient_id": "ing7", "quantity_grams": 50}]},
            {"id": "rec5", "name": "Sandwich au Fromage", "type": "lunch", "tags": ["dairy", "bread"], "ingredients": [{"ingredient_id": "ing8", "quantity_grams": 100}, {"ingredient_id": "ing9", "quantity_grams": 50}]},
            {"id": "rec6", "name": "Pâtes Carbonara", "type": "dinner", "tags": ["pasta", "pork"], "ingredients": [{"ingredient_id": "ing10", "quantity_grams": 200}, {"ingredient_id": "ing11", "quantity_grams": 100}, {"ingredient_id": "ing1", "quantity_grams": 50}]},
            {"id": "rec7", "name": "Curry de Légumes", "type": "dinner", "tags": ["vegan", "spicy"], "ingredients": [{"ingredient_id": "ing3", "quantity_grams": 100}, {"ingredient_id": "ing4", "quantity_grams": 100}, {"ingredient_id": "ing12", "quantity_grams": 150}]},
            {"id": "rec8", "name": "Smoothie Vert", "type": "breakfast", "tags": ["vegan", "fruit"], "ingredients": [{"ingredient_id": "ing13", "quantity_grams": 150}, {"ingredient_id": "ing7", "quantity_grams": 50}]}
        ], f, indent=2)

    # ingredients.json
    with open('ingredients.json', 'w', encoding='utf-8') as f:
        json.dump({
            "ing1": {"name": "Oeuf", "calories_per_100g": 155, "protein_per_100g": 13, "allergens": ["egg"]},
            "ing2": {"name": "Lait", "calories_per_100g": 60, "protein_per_100g": 3, "allergens": ["dairy"]},
            "ing3": {"name": "Laitue", "calories_per_100g": 15, "protein_per_100g": 1, "allergens": []},
            "ing4": {"name": "Tomate", "calories_per_100g": 18, "protein_per_100g": 1, "allergens": []},
            "ing5": {"name": "Poulet", "calories_per_100g": 165, "protein_per_100g": 31, "allergens": []},
            "ing6": {"name": "Yaourt", "calories_per_100g": 60, "protein_per_100g": 10, "allergens": ["dairy"]},
            "ing7": {"name": "Fraise", "calories_per_100g": 32, "protein_per_100g": 0.7, "allergens": []},
            "ing8": {"name": "Pain", "calories_per_100g": 265, "protein_per_100g": 9, "allergens": ["gluten"]},
            "ing9": {"name": "Fromage", "calories_per_100g": 400, "protein_per_100g": 25, "allergens": ["dairy"]},
            "ing10": {"name": "Pâtes", "calories_per_100g": 131, "protein_per_100g": 5, "allergens": ["gluten"]},
            "ing11": {"name": "Lardons", "calories_per_100g": 350, "protein_per_100g": 15, "allergens": ["pork"]},
            "ing12": {"name": "Curry paste", "calories_per_100g": 100, "protein_per_100g": 2, "allergens": []},
            "ing13": {"name": "Épinard", "calories_per_100g": 23, "protein_per_100g": 3, "allergens": []}
        }, f, indent=2)

    # constraints.json
    with open('constraints.json', 'w', encoding='utf-8') as f:
        json.dump({
            "daily_calories": {"min": 1500, "max": 2200},
            "daily_protein_min": 70,
            "avoid_allergens": ["egg", "gluten"], # No omelette, no pasta, no sandwich
            "meal_type_diversity": {
                "max_same_type_per_week": {
                    "breakfast": 3, # Max 3 breakfasts of type 'breakfast'
                    "lunch": 3,     # Max 3 lunches of type 'lunch'
                    "dinner": 3     # Max 3 dinners of type 'dinner'
                }
            },
            "max_recipe_repetition_per_week": 1,
            "meal_slot_types": {
                "breakfast": ["breakfast"],
                "lunch": ["lunch"],
                "dinner": ["dinner"]
            }
        }, f, indent=2)

    print("Chargement des données...")
    raw_recipes = load_data('recipes.json')
    ingredients_data = load_data('ingredients.json')
    raw_constraints = load_data('constraints.json')

    print("Préparation des recettes...")
    enriched_recipes = prepare_recipes(raw_recipes, ingredients_data)
    
    # Create a map for recipes by ID for summary function
    recipes_map_by_id = {r['id']: r for r in enriched_recipes}

    print("Analyse des contraintes...")
    constraints_parsed = parse_constraints(raw_constraints)

    print("Génération du menu (3 jours, 3 repas par jour)...")
    num_days_to_generate = 3
    meal_slots_per_day = ['breakfast', 'lunch', 'dinner']
    
    generated_menu = generate_constrained_menu(
        all_recipes=enriched_recipes,
        all_ingredients=ingredients_data, # Passed as per signature, not directly used by generate_constrained_menu
        constraints=constraints_parsed,
        num_days=num_days_to_generate,
        meal_slots=meal_slots_per_day
    )

    display_menu(generated_menu)

    if generated_menu:
        print("\nCalcul du résumé du menu...")
        menu_summary = calculate_menu_summary(generated_menu, recipes_map_by_id, ingredients_data)
        print("\n--- Résumé du Menu ---")
        for key, value in menu_summary.items():
            if key == 'ingredients_needed_grams':
                print(f"  Ingrédients nécessaires (g):")
                for ing_name, quantity in value.items():
                    print(f"    - {ing_name}: {quantity}g")
            else:
                print(f"  {key.replace('_', ' ').capitalize()}: {value}")
        print("----------------------\n")
    else:
        print("La génération de menu a échoué.")