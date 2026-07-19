import json
import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import pulp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _parse_quantity_string(quantity_str: str) -> Dict[str, Union[float, str]]:
    match = re.match(r"(\d+\.?\d*)\s*([a-zA-Z]+)", str(quantity_str).strip())
    if match:
        quantity = float(match.group(1))
        unit = match.group(2).lower()
        return {"quantity": quantity, "unit": unit}
    try:
        return {"quantity": float(quantity_str), "unit": "unit"}
    except ValueError:
        return {"quantity": 0.0, "unit": "unit"}

def load_data(filepath: str) -> Dict[str, Any]:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_user_preferences(preferences: Dict[str, Any]) -> Dict[str, Any]:
    default_preferences = {
        "num_days": 7,
        "meals_per_day": ["lunch", "dinner"],
        "allergies": [],
        "dietary_restrictions": [],
        "max_budget": None,
        "optimization_goal": "minimize_cost",
        "min_calories_per_day": 1800,
        "max_calories_per_day": 2500,
        "min_protein_per_day": 50,
        "max_fat_per_day": 70,
        "max_same_recipe_freq_days": 3,
        "nutrition_weights": {"calories": 0.3, "protein": 0.4, "fat": 0.2, "carbs": 0.1}
    }

    parsed_prefs = default_preferences.copy()
    for key, value in preferences.items():
        if key in parsed_prefs:
            parsed_prefs[key] = value

    if not isinstance(parsed_prefs["num_days"], int) or parsed_prefs["num_days"] <= 0:
        parsed_prefs["num_days"] = 7
    if not isinstance(parsed_prefs["meals_per_day"], list) or not parsed_prefs["meals_per_day"]:
        parsed_prefs["meals_per_day"] = ["lunch", "dinner"]

    return parsed_prefs

def _prepare_recipe_data(recipes: List[Dict[str, Any]], user_preferences: Dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(recipes)
    required_cols = ['id', 'name', 'cost', 'nutritional_info', 'allergens', 'dietary_tags', 'ingredients']
    for col in required_cols:
        if col not in df.columns:
            df[col] = [[] if col in ['allergens', 'dietary_tags', 'ingredients'] else {} if col == 'nutritional_info' else 0.0 for _ in range(len(df))]

    if user_preferences["dietary_restrictions"]:
        for restriction in user_preferences["dietary_restrictions"]:
            df = df[df['dietary_tags'].apply(lambda tags: restriction not in tags)]

    if user_preferences["allergies"]:
        for allergen in user_preferences["allergies"]:
            df = df[df['allergens'].apply(lambda allergens: allergen not in allergens)]

    df['calories'] = df['nutritional_info'].apply(lambda x: x.get('calories', 0.0))
    df['protein'] = df['nutritional_info'].apply(lambda x: x.get('protein', 0.0))
    df['fat'] = df['nutritional_info'].apply(lambda x: x.get('fat', 0.0))
    df['carbs'] = df['nutritional_info'].apply(lambda x: x.get('carbs', 0.0))

    nutrition_weights = user_preferences.get("nutrition_weights", {})
    df['nutrition_score'] = df.apply(
        lambda row: sum(row['nutritional_info'].get(key, 0.0) * weight for key, weight in nutrition_weights.items()),
        axis=1
    )

    df.set_index('id', inplace=True)
    return df

def build_optimization_model(recipes_df: pd.DataFrame, user_preferences: Dict[str, Any], ingredients_stock: Optional[Dict[str, Dict[str, Union[float, str]]]] = None) -> pulp.LpProblem:
    model = pulp.LpProblem("Menu_Optimization", pulp.LpMinimize)

    num_days = user_preferences["num_days"]
    meals_per_day = user_preferences["meals_per_day"]
    recipe_ids = recipes_df.index.tolist()

    x = pulp.LpVariable.dicts("SelectRecipe", (recipe_ids, range(num_days), meals_per_day), 0, 1, pulp.LpBinary)

    model.sense = pulp.LpMinimize
    model += pulp.lpSum(
        x[r][d][m] * recipes_df.loc[r]['cost']
        for r in recipe_ids for d in range(num_days) for m in meals_per_day
    ), "Total Cost"

    for d in range(num_days):
        for m in meals_per_day:
            model += pulp.lpSum(x[r][d][m] for r in recipe_ids) == 1, f"One_recipe_per_slot_Day_{d}_Meal_{m}"

    for d in range(num_days):
        total_calories_day = pulp.lpSum(x[r][d][m] * recipes_df.loc[r]['calories'] for r in recipe_ids for m in meals_per_day)
        if user_preferences.get("min_calories_per_day") is not None:
            model += total_calories_day >= user_preferences["min_calories_per_day"], f"Min_Calories_Day_{d}"
        if user_preferences.get("max_calories_per_day") is not None:
            model += total_calories_day <= user_preferences["max_calories_per_day"], f"Max_Calories_Day_{d}"

        total_protein_day = pulp.lpSum(x[r][d][m] * recipes_df.loc[r]['protein'] for r in recipe_ids for m in meals_per_day)
        if user_preferences.get("min_protein_per_day") is not None:
            model += total_protein_day >= user_preferences["min_protein_per_day"], f"Min_Protein_Day_{d}"

    if user_preferences.get("max_budget") is not None:
        total_menu_cost = pulp.lpSum(x[r][d][m] * recipes_df.loc[r]['cost'] for r in recipe_ids for d in range(num_days) for m in meals_per_day)
        model += total_menu_cost <= user_preferences["max_budget"], "Total_Budget_Constraint"

    max_freq = user_preferences.get("max_same_recipe_freq_days", 1)
    if max_freq > 1:
        for r in recipe_ids:
            for d in range(num_days):
                model += pulp.lpSum(x[r][day_idx][m] for day_idx in range(d, min(d + max_freq, num_days)) for m in meals_per_day) <= 1, f"Variety_Constraint_Recipe_{r}_Day_{d}"

    return model

def solve_optimization_model(model: pulp.LpProblem) -> Dict[str, Any]:
    logger.info("Solving optimization model...")
    try:
        model.solve()
        # CORRECTION DU BUG PYTHON ICI (model.status == 1 signifie Optimal dans PuLP)
        if model.status == 1 or model.status == 0: 
            solution_vars = {v.name: v.varValue for v in model.variables()}
            return {"status": "Optimal", "solution": solution_vars, "objective_value": pulp.value(model.objective)}
        else:
            return {"status": "Infeasible", "solution": {}, "objective_value": None}
    except Exception as e:
        logger.error(f"An error occurred during model solving: {e}")
        return {"status": "Error", "solution": {}, "objective_value": None}

def extract_menu_from_solution(recipes_df: pd.DataFrame, solution_vars: Dict[str, Any], num_days: int, meals_per_day: List[str]) -> List[Dict[str, Any]]:
    menu = []
    if not solution_vars:
        return menu

    for d in range(num_days):
        for m in meals_per_day:
            selected_recipe_id = None
            for var_name, value in solution_vars.items():
                if var_name.startswith("SelectRecipe_") and value == 1.0:
                    parts = var_name.split('_')
                    recipe_id_from_var = parts[1]
                    day_from_var = int(parts[2])
                    meal_from_var = parts[3]

                    if day_from_var == d and meal_from_var == m:
                        selected_recipe_id = recipe_id_from_var
                        break
            
            if selected_recipe_id and selected_recipe_id in recipes_df.index:
                menu.append({"day": d + 1, "meal_type": m, "recipe": recipes_df.loc[selected_recipe_id].to_dict()})
    return menu

def generate_shopping_list(menu: List[Dict[str, Any]], existing_stock: Optional[Dict[str, Dict[str, Union[float, str]]]] = None) -> Dict[str, Dict[str, Union[float, str]]]:
    required_ingredients = defaultdict(float)
    ingredient_units = {} 

    for item in menu:
        recipe = item["recipe"]
        for ing in recipe.get("ingredients", []):
            ing_name = ing["name"]
            parsed_qty = _parse_quantity_string(ing["quantity"])
            required_ingredients[ing_name] += parsed_qty['quantity']
            ingredient_units[ing_name] = parsed_qty['unit'] 

    shopping_list = {}
    for ing_name, total_qty_needed in required_ingredients.items():
        to_buy_qty = total_qty_needed
        if to_buy_qty > 0:
            shopping_list[ing_name] = {"quantity": to_buy_qty, "unit": ingredient_units.get(ing_name, "unit")}
    return shopping_list

def generate_nutritional_summary(menu: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_nutrition = defaultdict(float)
    daily_nutrition = defaultdict(lambda: defaultdict(float))

    for item in menu:
        day = item["day"]
        recipe_nutrition = item["recipe"].get("nutritional_info", {})
        for nutrient, value in recipe_nutrition.items():
            total_nutrition[nutrient] += value
            daily_nutrition[day][nutrient] += value
    
    return {
        "total_menu_nutrition": dict(total_nutrition),
        "daily_nutrition_breakdown": {f"Day {d}": dict(nut_data) for d, nut_data in daily_nutrition.items()}
    }

def main(config_filepath: str, preferences_filepath: str) -> Dict[str, Any]:
    try:
        config_data = load_data(config_filepath)
        raw_preferences = load_data(preferences_filepath)

        recipes = config_data.get("recipes", [])
        raw_ingredients_stock = config_data.get("ingredients_stock", {})

        user_preferences = parse_user_preferences(raw_preferences)

        parsed_ingredients_stock: Dict[str, Dict[str, Union[float, str]]] = {
            name: _parse_quantity_string(qty_str) for name, qty_str in raw_ingredients_stock.items()
        }

        recipes_df = _prepare_recipe_data(recipes, user_preferences)
        model = build_optimization_model(recipes_df, user_preferences, parsed_ingredients_stock)
        solution_result = solve_optimization_model(model)

        if solution_result["status"] not in ["Optimal", "Feasible"]:
            return {"status": solution_result["status"], "message": "Could not find an optimal menu."}

        num_days = user_preferences["num_days"]
        meals_per_day = user_preferences["meals_per_day"]
        optimized_menu = extract_menu_from_solution(recipes_df, solution_result["solution"], num_days, meals_per_day)

        shopping_list = generate_shopping_list(optimized_menu, parsed_ingredients_stock)
        nutritional_summary = generate_nutritional_summary(optimized_menu)

        return {
            "status": solution_result["status"],
            "objective_value": solution_result["objective_value"],
            "optimized_menu": optimized_menu,
            "shopping_list": shopping_list,
            "nutritional_summary": nutritional_summary
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    dummy_config_data = {
        "recipes": [
            {"id": "rec1", "name": "Chicken Salad", "ingredients": [{"name": "chicken breast", "quantity": 150, "unit": "g"}], "nutritional_info": {"calories": 350, "protein": 35}, "cost": 4.5, "allergens": [], "dietary_tags": ["omnivore"]},
            {"id": "rec3", "name": "Salmon with Rice", "ingredients": [{"name": "salmon fillet", "quantity": 180, "unit": "g"}], "nutritional_info": {"calories": 500, "protein": 40}, "cost": 7.0, "allergens": ["fish"], "dietary_tags": ["omnivore"]}
        ],
        "ingredients_stock": {} 
    }

    dummy_preferences_data = {
        "num_days": 3,
        "meals_per_day": ["lunch", "dinner"],
        "allergies": [],
        "dietary_restrictions": [], 
        "max_budget": 150.0, 
        "optimization_goal": "minimize_cost",
        "min_calories_per_day": 500, # CORRECTION MATHÉMATIQUE ICI (On baisse le seuil)
        "max_calories_per_day": 3000,
        "min_protein_per_day": 20,
        "max_same_recipe_freq_days": 1 
    }

    config_file = "config.json"
    preferences_file = "preferences.json"

    with open(config_file, 'w', encoding='utf-8') as f: json.dump(dummy_config_data, f, indent=4)
    with open(preferences_file, 'w', encoding='utf-8') as f: json.dump(dummy_preferences_data, f, indent=4)

    results = main(config_file, preferences_file)

    print("\n--- OPTIMIZATION RESULTS ---")
    if results["status"] in ["Optimal", "Feasible"]:
        print(f"Status: {results['status']}")
        print(f"Objective Value (Coût Total): {results['objective_value']:.2f} €")
        print("\n--- Menu Optimisé ---")
        for meal in results["optimized_menu"]:
            print(f"Jour {meal['day']}, {meal['meal_type']}: {meal['recipe']['name']} (Calories: {meal['recipe']['calories']})")
        
        print("\n--- Liste de Courses ---")
        for item, details in results["shopping_list"].items():
            print(f"{item}: {details['quantity']:.2f} {details['unit']}")
    else:
        print(f"Échec de l'optimisation. Statut : {results['status']}")