import json
import random
from typing import List, Dict, Union, Optional
from collections import defaultdict
import re

# --- Placeholder Data Setup ---
DEFAULT_RECIPES_DATA = [
    {
        "id": "rec1",
        "name": "Salade de Pâtes Poulet Citron",
        "description": "Une salade fraîche et légère, parfaite pour le déjeuner.",
        "ingredients": [
            {"item": "Pâtes", "quantity": "200g"},
            {"item": "Blanc de poulet", "quantity": "150g"},
            {"item": "Tomates cerises", "quantity": "100g"},
            {"item": "Concombre", "quantity": "0.5 unit"},
            {"item": "Citron", "quantity": "1 unit"},
            {"item": "Huile d'olive", "quantity": "2 tbsp"},
            {"item": "Feta", "quantity": "50g"}
        ],
        "prep_time_minutes": 20,
        "tags": ["healthy", "quick", "lunch", "poulet"]
    },
    {
        "id": "rec2",
        "name": "Curry de Lentilles Corail",
        "description": "Un curry végétarien riche et savoureux.",
        "ingredients": [
            {"item": "Lentilles corail", "quantity": "150g"},
            {"item": "Lait de coco", "quantity": "200ml"},
            {"item": "Oignon", "quantity": "1 unit"},
            {"item": "Ail", "quantity": "2 cloves"},
            {"item": "Gingembre frais", "quantity": "10g"},
            {"item": "Épinards frais", "quantity": "150g"},
            {"item": "Pâte de curry", "quantity": "1 tbsp"}
        ],
        "prep_time_minutes": 30,
        "tags": ["vegetarian", "healthy", "dinner", "curry"]
    },
    {
        "id": "rec3",
        "name": "Wrap Falafel",
        "description": "Un wrap rapide et délicieux avec des falafels maison ou achetés.",
        "ingredients": [
            {"item": "Galettes de blé", "quantity": "2 units"},
            {"item": "Falafels", "quantity": "6 units"},
            {"item": "Houmous", "quantity": "50g"},
            {"item": "Salade verte", "quantity": "30g"},
            {"item": "Tomate", "quantity": "0.5 unit"},
            {"item": "Sauce blanche", "quantity": "2 tbsp"}
        ],
        "prep_time_minutes": 15,
        "tags": ["vegetarian", "quick", "lunch", "street food"]
    },
    {
        "id": "rec4",
        "name": "Soupe de Potimarron et Châtaignes",
        "description": "Une soupe réconfortante pour les jours froids.",
        "ingredients": [
            {"item": "Potimarron", "quantity": "500g"},
            {"item": "Châtaignes cuites", "quantity": "150g"},
            {"item": "Bouillon de légumes", "quantity": "500ml"},
            {"item": "Crème fraîche", "quantity": "50ml"},
            {"item": "Oignon", "quantity": "1 unit"}
        ],
        "prep_time_minutes": 40,
        "tags": ["vegetarian", "healthy", "dinner", "soup"]
    },
    {
        "id": "rec5",
        "name": "Poulet Basquaise Express",
        "description": "Un plat du sud-ouest revisité pour une préparation rapide.",
        "ingredients": [
            {"item": "Blanc de poulet", "quantity": "200g"},
            {"item": "Poivron rouge", "quantity": "1 unit"},
            {"item": "Tomates concassées", "quantity": "200g"},
            {"item": "Oignon", "quantity": "1 unit"},
            {"item": "Riz", "quantity": "150g"},
            {"item": "Piment d'Espelette", "quantity": "0.5 tsp"}
        ],
        "prep_time_minutes": 25,
        "tags": ["quick", "dinner", "poulet"]
    },
    {
        "id": "rec6",
        "name": "Salade Quinoa Avocat Mangue",
        "description": "Une salade exotique et nourrissante.",
        "ingredients": [
            {"item": "Quinoa", "quantity": "100g"},
            {"item": "Avocat", "quantity": "1 unit"},
            {"item": "Mangue", "quantity": "0.5 unit"},
            {"item": "Tomates cerises", "quantity": "80g"},
            {"item": "Coriandre fraîche", "quantity": "10g"},
            {"item": "Jus de citron vert", "quantity": "1 tbsp"}
        ],
        "prep_time_minutes": 20,
        "tags": ["vegetarian", "healthy", "quick", "lunch"]
    },
    {
        "id": "rec7",
        "name": "Pâtes au Pesto et Tomates Séchées",
        "description": "Un classique rapide et savoureux.",
        "ingredients": [
            {"item": "Pâtes", "quantity": "200g"},
            {"item": "Pesto", "quantity": "50g"},
            {"item": "Tomates séchées", "quantity": "30g"},
            {"item": "Parmesan", "quantity": "20g"}
        ],
        "prep_time_minutes": 15,
        "tags": ["vegetarian", "quick", "lunch", "dinner"]
    },
    {
        "id": "rec8",
        "name": "Omelette aux Champignons et Fromage",
        "description": "Simple, rapide et personnalisable.",
        "ingredients": [
            {"item": "Oeufs", "quantity": "3 units"},
            {"item": "Champignons de Paris", "quantity": "100g"},
            {"item": "Fromage râpé", "quantity": "30g"},
            {"item": "Beurre", "quantity": "10g"}
        ],
        "prep_time_minutes": 10,
        "tags": ["quick", "lunch", "dinner", "vegetarian"]
    }
]

DEFAULT_PREFERENCES_DATA = {
    "dietary_restrictions": [], # Example: "vegetarian", "vegan", "gluten-free"
    "disliked_ingredients": [], # Example: "champignons", "coriandre"
    "max_prep_time_minutes": 35,
    "preferred_tags": ["healthy", "quick"], # Example: "spicy", "comfort food"
    "min_diversity_days": 2 # Minimum days before a recipe can be repeated
}

RECIPES_FILE = "recipes.json"
USER_PREFERENCES_FILE = "user_preferences.json"

def _ensure_default_data_files():
    """Helper to ensure default JSON files exist for the script to run."""
    for filename, default_data in [
        (RECIPES_FILE, DEFAULT_RECIPES_DATA),
        (USER_PREFERENCES_FILE, DEFAULT_PREFERENCES_DATA)
    ]:
        try:
            with open(filename, 'x', encoding='utf-8') as f: # 'x' mode for exclusive creation
                json.dump(default_data, f, indent=4)
            print(f"Created default {filename}")
        except FileExistsError:
            pass # File already exists, do nothing
        except Exception as e:
            print(f"Error ensuring default {filename}: {e}")

def load_data(filepath: str) -> Union[Dict, List]:
    """
    Charge les données depuis un fichier JSON spécifié.
    Gère les exceptions en cas de fichier non trouvé ou de format JSON invalide.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: File not found at {filepath}. Returning default data.")
        if filepath == RECIPES_FILE:
            return DEFAULT_RECIPES_DATA
        elif filepath == USER_PREFERENCES_FILE:
            return DEFAULT_PREFERENCES_DATA
        return {} # Fallback for unknown files
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {filepath}. Returning empty data.")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred while loading {filepath}: {e}. Returning empty data.")
        return {}

def get_recipes() -> List[Dict]:
    """
    Charge et retourne la liste complète des recettes disponibles depuis un fichier prédéfini.
    """
    return load_data(RECIPES_FILE)

def get_user_preferences() -> Dict:
    """
    Charge et retourne les préférences de l'utilisateur depuis un fichier prédéfini.
    """
    return load_data(USER_PREFERENCES_FILE)

def filter_recipes(recipes: List[Dict], preferences: Dict) -> List[Dict]:
    """
    Filtre la liste des recettes en fonction des préférences de l'utilisateur.
    """
    filtered: List[Dict] = []
    dietary_restrictions = [r.lower() for r in preferences.get("dietary_restrictions", [])]
    disliked_ingredients = [i.lower() for i in preferences.get("disliked_ingredients", [])]
    max_prep_time = preferences.get("max_prep_time_minutes", float('inf'))
    preferred_tags = [t.lower() for t in preferences.get("preferred_tags", [])]

    for recipe in recipes:
        # Check dietary restrictions
        recipe_tags = [t.lower() for t in recipe.get("tags", [])]
        
        # If user has dietary_restrictions, all of them must be present in recipe tags.
        # E.g., if user wants "vegetarian" and "gluten-free", recipe must have both.
        is_restricted = False
        for restriction in dietary_restrictions:
            if restriction not in recipe_tags:
                is_restricted = True
                break
        if is_restricted:
            continue

        # Check disliked ingredients
        recipe_ingredients = [ing["item"].lower() for ing in recipe.get("ingredients", [])]
        if any(disliked in recipe_ingredients for disliked in disliked_ingredients):
            continue

        # Check max preparation time
        if recipe.get("prep_time_minutes", float('inf')) > max_prep_time:
            continue
        
        # Check for preferred tags: At least one preferred tag must be present if preferred_tags are defined.
        if preferred_tags and not any(tag in recipe_tags for tag in preferred_tags):
            continue

        filtered.append(recipe)
    return filtered

def select_meals(filtered_recipes: List[Dict], num_days: int) -> List[Dict]:
    """
    Sélectionne un ensemble de repas pour un nombre de jours donné à partir des recettes filtrées.
    Assure une diversité en évitant de proposer la même recette sur des jours consécutifs.
    """
    meal_plan: List[Dict] = []
    # Track recently used recipe IDs to ensure diversity
    recently_used_recipe_ids: List[str] = []
    min_diversity_days = get_user_preferences().get("min_diversity_days", 2)

    for day in range(num_days):
        eligible_for_today: List[Dict] = []
        for recipe in filtered_recipes:
            recipe_id = recipe.get("id", recipe.get("name", str(hash(json.dumps(recipe))))) # Fallback to name or hash
            if recipe_id not in recently_used_recipe_ids:
                eligible_for_today.append(recipe)

        if not eligible_for_today:
            # If no diverse recipes are left, allow repetition from the entire filtered set
            # This ensures we always try to provide a meal, even if not perfectly diverse.
            print(f"Warning: Not enough diverse recipes for day {day+1}. Allowing repetition.")
            eligible_for_today = filtered_recipes
            if not eligible_for_today: # Still no recipes at all?
                print("Error: No recipes available at all after initial filtering.")
                break # Cannot plan any more meals

        selected_meal = random.choice(eligible_for_today)
        meal_plan.append(selected_meal)

        # Update recently used recipes for diversity constraint
        recipe_id = selected_meal.get("id", selected_meal.get("name", str(hash(json.dumps(selected_meal)))))
        recently_used_recipe_ids.append(recipe_id)
        # Maintain a sliding window of `min_diversity_days`
        if len(recently_used_recipe_ids) > min_diversity_days - 1:
            recently_used_recipe_ids.pop(0)

    return meal_plan

def _parse_quantity(quantity_str: str) -> Optional[Dict[str, Union[float, str]]]:
    """
    Parses a quantity string (e.g., "200g", "1 unit", "2 tbsp") into a number and a unit.
    Returns None if parsing fails.
    """
    # Regex to capture a number (integer or float) and an optional unit
    match = re.match(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?", quantity_str.strip())
    if match:
        try:
            value = float(match.group(1))
            unit = (match.group(2) or "").lower() # Unit might be None
            return {"value": value, "unit": unit}
        except ValueError:
            pass
    return None

def generate_shopping_list(meal_plan: List[Dict]) -> Dict[str, str]:
    """
    Génère une liste de courses consolidée à partir du plan de repas sélectionné.
    Agrège les quantités pour les ingrédients qui apparaissent dans plusieurs recettes.
    """
    # Use defaultdict to store aggregated quantities.
    # Each item will have a list of parsed quantities, allowing for mixed units.
    aggregated_ingredients: Dict[str, List[Dict[str, Union[float, str]]]] = defaultdict(list)
    
    for meal in meal_plan:
        for ingredient in meal.get("ingredients", []):
            item_name = ingredient["item"]
            quantity_str = ingredient["quantity"]
            parsed_qty = _parse_quantity(quantity_str)

            if parsed_qty and parsed_qty["unit"]: # Only aggregate if we have a parsed number and unit
                found_match = False
                for existing_entry in aggregated_ingredients[item_name]:
                    if existing_entry["unit"] == parsed_qty["unit"]:
                        existing_entry["value"] = float(existing_entry["value"]) + parsed_qty["value"] # type: ignore
                        found_match = True
                        break
                if not found_match:
                    aggregated_ingredients[item_name].append(parsed_qty)
            else: # If parsing fails or no unit, add the original string
                # Check if it already exists as an unparsed string
                found_unparsed = False
                for existing_entry in aggregated_ingredients[item_name]:
                    if existing_entry.get("unit") == "unparsed":
                        # If multiple unparsed strings, concatenate them
                        existing_entry["value"] = f"{existing_entry['value']}, {quantity_str}" # type: ignore
                        found_unparsed = True
                        break
                if not found_unparsed:
                    aggregated_ingredients[item_name].append({"value": quantity_str, "unit": "unparsed"})


    final_shopping_list: Dict[str, str] = {}
    for item, quantities_list in aggregated_ingredients.items():
        parts: List[str] = []
        for qty_data in quantities_list:
            if qty_data["unit"] == "unparsed":
                parts.append(str(qty_data["value"]))
            else:
                # Format float to remove trailing .0 if it's an integer
                value_str = str(int(qty_data["value"])) if qty_data["value"] == int(qty_data["value"]) else str(qty_data["value"]) # type: ignore
                parts.append(f"{value_str}{qty_data['unit']}")
        final_shopping_list[item] = ", ".join(parts)

    return final_shopping_list


def display_meal_plan(meal_plan: List[Dict]) -> None:
    """
    Affiche le plan de repas de manière lisible pour l'utilisateur.
    """
    print("\n--- Votre Plan de Repas ---")
    if not meal_plan:
        print("Aucun repas n'a pu être planifié.")
        return

    for i, meal in enumerate(meal_plan):
        print(f"\nJour {i+1}: {meal.get('name', 'Repas inconnu')}")
        print(f"  Description: {meal.get('description', 'N/A')}")
        print(f"  Temps de préparation: {meal.get('prep_time_minutes', 'N/A')} minutes")
        ingredients = [f"{ing['item']} ({ing['quantity']})" for ing in meal.get('ingredients', [])]
        print(f"  Ingrédients principaux: {', '.join(ingredients)}")
        print(f"  Tags: {', '.join(meal.get('tags', []))}")

def main_planner(num_days: int) -> None:
    """
    Fonction principale orchestrant l'ensemble du processus de planification.
    """
    _ensure_default_data_files() # Ensure default data files exist for the first run

    print(f"Lancement de la planification des repas pour {num_days} jours...")

    all_recipes = get_recipes()
    if not all_recipes:
        print("Erreur: Aucune recette disponible pour la planification. Veuillez vérifier 'recipes.json'.")
        return

    user_preferences = get_user_preferences()
    if not user_preferences:
        print("Erreur: Impossible de charger les préférences utilisateur. Vérifiez 'user_preferences.json'.")
        return

    print("\nPréférences utilisateur chargées:")
    for key, value in user_preferences.items():
        print(f"  {key}: {value}")

    filtered_recipes = filter_recipes(all_recipes, user_preferences)
    if not filtered_recipes:
        print("\nAttention: Aucune recette ne correspond à vos préférences. Veuillez ajuster vos filtres.")
        return

    print(f"\n{len(filtered_recipes)} recettes éligibles après filtrage.")

    meal_plan = select_meals(filtered_recipes, num_days)
    if not meal_plan:
        print("\nImpossible de générer un plan de repas avec les recettes et préférences actuelles.")
        return

    display_meal_plan(meal_plan)

    shopping_list = generate_shopping_list(meal_plan)
    print("\n--- Votre Liste de Courses ---")
    if not shopping_list:
        print("La liste de courses est vide.")
    else:
        for item, quantity in shopping_list.items():
            print(f"- {item}: {quantity}")

if __name__ == "__main__":
    # Example usage: Plan meals for 5 days
    main_planner(num_days=5)