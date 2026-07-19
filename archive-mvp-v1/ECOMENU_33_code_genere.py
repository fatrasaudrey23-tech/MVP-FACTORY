import pandas as pd
import pulp
import json
import logging
import argparse
import sys
import os
import typing

# 1. Global Logger Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 2. Type Hints for Python 3.9 compatibility
DataFrame = pd.DataFrame
List = typing.List
Dict = typing.Dict
Tuple = typing.Tuple
Optional = typing.Optional
Union = typing.Union

# 3. Functions de Chargement et Préparation des Données

def load_configuration(config_filepath: str) -> Dict:
    """
    Charge la configuration générale de l'application depuis un fichier JSON.
    """
    try:
        with open(config_filepath, 'r') as f:
            config = json.load(f)
        logger.info(f"Configuration loaded successfully from {config_filepath}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_filepath}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in configuration file: {config_filepath}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading configuration: {e}")
        sys.exit(1)

def load_recipes_data(filepath: str) -> DataFrame:
    """
    Lit les données des recettes (ID, nom, ingrédients, informations nutritionnelles,
    temps de préparation, coût, etc.) depuis un fichier (CSV ou JSON) et les charge
    dans un DataFrame Pandas.
    """
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
            # Convert pipe-separated strings to lists
            if 'dietary_tags' in df.columns:
                df['dietary_tags'] = df['dietary_tags'].apply(lambda x: [tag.strip() for tag in str(x).split('|')] if pd.notna(x) else [])
            if 'ingredients' in df.columns:
                df['ingredients'] = df['ingredients'].apply(lambda x: [ing.strip() for ing in str(x).split('|')] if pd.notna(x) else [])
        elif filepath.endswith('.json'):
            with open(filepath, 'r') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
        else:
            logger.error(f"Unsupported file format for recipes: {filepath}. Please use .csv or .json.")
            sys.exit(1)

        # Basic validation of required columns
        required_columns = ['recipe_id', 'name', 'calories', 'protein_g', 'fat_g', 'carbs_g', 'cost', 'prep_time_min', 'dietary_tags', 'ingredients']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns in recipes data: {', '.join(missing_columns)}")
            sys.exit(1)

        # Ensure numeric types
        numeric_cols = ['calories', 'protein_g', 'fat_g', 'carbs_g', 'cost', 'prep_time_min']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=numeric_cols, inplace=True) # Drop rows with invalid numeric values

        df.set_index('recipe_id', inplace=True)
        logger.info(f"Recipes data loaded successfully from {filepath}. {len(df)} recipes available.")
        return df
    except FileNotFoundError:
        logger.error(f"Recipes data file not found: {filepath}")
        sys.exit(1)
    except (json.JSONDecodeError, pd.errors.EmptyDataError, KeyError) as e:
        logger.error(f"Error processing recipes data from {filepath}: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading recipes data: {e}")
        sys.exit(1)

def load_user_preferences(filepath: str) -> Dict:
    """
    Charge les préférences et contraintes spécifiques de l'utilisateur.
    """
    try:
        with open(filepath, 'r') as f:
            preferences = json.load(f)

        # Validate and set default preferences
        default_prefs = {
            'daily_meals': 3,
            'planning_days': 7,
            'max_weekly_calories': 14000, 'min_weekly_calories': 10500, # Example for 1500-2000 cal/day
            'max_weekly_protein': 1050, 'min_weekly_protein': 525, # Example for 75-150g protein/day
            'max_weekly_fat': 700, 'min_weekly_fat': 350, # Example for 50-100g fat/day
            'max_weekly_carbs': 1400, 'min_weekly_carbs': 700, # Example for 100-200g carbs/day
            'max_weekly_cost': 100.0,
            'max_weekly_prep_time': 420, # 7 hours
            'dietary_restrictions': [],
            'allergies': [],
            'ingredients_to_avoid': []
        }
        for key, default_val in default_prefs.items():
            if key not in preferences:
                preferences[key] = default_val
                logger.warning(f"User preference '{key}' not found, using default value: {default_val}")
            # Ensure lists are lists
            if key in ['dietary_restrictions', 'allergies', 'ingredients_to_avoid'] and not isinstance(preferences[key], list):
                preferences[key] = []
                logger.warning(f"User preference '{key}' invalid, resetting to empty list.")
        
        logger.info(f"User preferences loaded successfully from {filepath}.")
        return preferences
    except FileNotFoundError:
        logger.error(f"User preferences file not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in user preferences file: {filepath}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading user preferences: {e}")
        sys.exit(1)

def prepare_optimization_data(recipes_df: DataFrame, preferences: Dict) -> Tuple[DataFrame, List[str]]:
    """
    Filtre et prépare l'ensemble des recettes en fonction des préférences initiales de l'utilisateur.
    """
    filtered_df = recipes_df.copy()

    # Apply dietary restrictions
    restrictions = [r.lower() for r in preferences.get('dietary_restrictions', [])]
    if restrictions:
        for restriction in restrictions:
            filtered_df = filtered_df[filtered_df['dietary_tags'].apply(lambda tags: restriction in [t.lower() for t in tags])]
        logger.info(f"Filtered by dietary restrictions ({', '.join(restrictions)}): {len(filtered_df)} recipes remaining.")

    # Apply allergies
    allergies = [a.lower() for a in preferences.get('allergies', [])]
    if allergies:
        filtered_df = filtered_df[filtered_df['ingredients'].apply(lambda ingredients: not any(a in [i.lower() for i in ingredients] for a in allergies))]
        logger.info(f"Filtered by allergies ({', '.join(allergies)}): {len(filtered_df)} recipes remaining.")

    # Apply ingredients to avoid
    ingredients_to_avoid = [i.lower() for i in preferences.get('ingredients_to_avoid', [])]
    if ingredients_to_avoid:
        filtered_df = filtered_df[filtered_df['ingredients'].apply(lambda ingredients: not any(i_avoid in [i.lower() for i in ingredients] for i_avoid in ingredients_to_avoid))]
        logger.info(f"Filtered by ingredients to avoid ({', '.join(ingredients_to_avoid)}): {len(filtered_df)} recipes remaining.")

    if filtered_df.empty:
        logger.error("No recipes match the specified user preferences after filtering.")
        sys.exit(1)

    recipe_ids = filtered_df.index.tolist()
    logger.info(f"Data prepared for optimization. {len(recipe_ids)} recipes available after filtering.")
    return filtered_df, recipe_ids

# 4. Fonctions d'Optimisation

def build_meal_plan_problem(filtered_recipes_df: DataFrame, preferences: Dict) -> pulp.LpProblem:
    """
    Construit le problème de programmation linéaire PuLP.
    """
    problem = pulp.LpProblem("Meal_Plan_Optimization", pulp.LpMinimize)

    recipe_ids = filtered_recipes_df.index.tolist()
    
    # Decision Variables: x_recipe[r_id] is 1 if recipe r_id is selected, 0 otherwise.
    # QA Correction: Each recipe can be selected only once.
    x_recipe = pulp.LpVariable.dicts("Recipe", recipe_ids, cat=pulp.LpBinary)

    # Objective Function: Minimize total cost
    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['cost'] * x_recipe[r_id] for r_id in recipe_ids), "Total Cost"

    # Constraints:

    # Total number of meals needed
    total_meals_needed = preferences['daily_meals'] * preferences['planning_days']
    problem += pulp.lpSum(x_recipe[r_id] for r_id in recipe_ids) == total_meals_needed, "Total Meals Constraint"

    # QA Correction: Nutritional constraints at the weekly level
    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['calories'] * x_recipe[r_id] for r_id in recipe_ids) >= preferences['min_weekly_calories'], "Min Weekly Calories"
    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['calories'] * x_recipe[r_id] for r_id in recipe_ids) <= preferences['max_weekly_calories'], "Max Weekly Calories"

    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['protein_g'] * x_recipe[r_id] for r_id in recipe_ids) >= preferences['min_weekly_protein'], "Min Weekly Protein"
    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['protein_g'] * x_recipe[r_id] for r_id in recipe_ids) <= preferences['max_weekly_protein'], "Max Weekly Protein"

    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['fat_g'] * x_recipe[r_id] for r_id in recipe_ids) >= preferences['min_weekly_fat'], "Min Weekly Fat"
    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['fat_g'] * x_recipe[r_id] for r_id in recipe_ids) <= preferences['max_weekly_fat'], "Max Weekly Fat"

    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['carbs_g'] * x_recipe[r_id] for r_id in recipe_ids) >= preferences['min_weekly_carbs'], "Min Weekly Carbs"
    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['carbs_g'] * x_recipe[r_id] for r_id in recipe_ids) <= preferences['max_weekly_carbs'], "Max Weekly Carbs"

    # Budget constraint
    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['cost'] * x_recipe[r_id] for r_id in recipe_ids) <= preferences['max_weekly_cost'], "Max Weekly Cost"

    # Preparation time constraint
    problem += pulp.lpSum(filtered_recipes_df.loc[r_id]['prep_time_min'] * x_recipe[r_id] for r_id in recipe_ids) <= preferences['max_weekly_prep_time'], "Max Weekly Prep Time"

    logger.info(f"PuLP problem built with {len(recipe_ids)} variables and {len(problem.constraints)} constraints.")
    return problem

def solve_meal_plan_problem(lp_problem: pulp.LpProblem) -> Dict:
    """
    Résout le problème d'optimisation PuLP défini.
    """
    logger.info("Solving the meal plan optimization problem...")
    lp_problem.solve()

    solution_status = pulp.LpStatus[lp_problem.status]
    logger.info(f"Solver status: {solution_status}")

    selected_recipe_ids = []
    if lp_problem.status == pulp.LpStatus.Optimal:
        for v in lp_problem.variables():
            if v.varValue == 1:
                # Variable names are like 'Recipe_R001', extract 'R001'
                selected_recipe_ids.append(v.name.replace('Recipe_', ''))
        logger.info(f"Optimal solution found. Total selected recipes: {len(selected_recipe_ids)}")
        logger.info(f"Optimal total cost: {pulp.value(lp_problem.objective):.2f}")
    else:
        logger.warning("No optimal solution found for the meal plan problem.")

    return {
        'status': solution_status,
        'selected_recipe_ids': selected_recipe_ids,
        'total_cost': pulp.value(lp_problem.objective) if lp_problem.status == pulp.LpStatus.Optimal else None
    }

# 5. Fonctions de Génération de Rapports et d'Orchestration

def generate_meal_plan_report(recipes_df: DataFrame, solution_vars: Dict, preferences: Dict) -> Dict:
    """
    Interprète la sortie du solveur et formate le plan de repas généré.
    """
    if solution_vars['status'] != 'Optimal' or not solution_vars['selected_recipe_ids']:
        return {'status': solution_vars['status'], 'message': 'Could not generate an optimal meal plan.'}

    selected_recipe_ids = solution_vars['selected_recipe_ids']
    selected_recipes_df = recipes_df.loc[selected_recipe_ids]

    meal_plan = {
        'planning_days': preferences['planning_days'],
        'daily_meals': preferences['daily_meals'],
        'plan_details': []
    }

    # Distribute recipes across days (simple sequential assignment)
    current_recipe_idx = 0
    for day in range(1, preferences['planning_days'] + 1):
        day_meals = []
        for meal_idx in range(preferences['daily_meals']):
            if current_recipe_idx < len(selected_recipes_df):
                recipe_data = selected_recipes_df.iloc[current_recipe_idx]
                day_meals.append({
                    'recipe_id': recipe_data.name,
                    'name': recipe_data['name'],
                    'calories': recipe_data['calories'],
                    'protein_g': recipe_data['protein_g'],
                    'fat_g': recipe_data['fat_g'],
                    'carbs_g': recipe_data['carbs_g'],
                    'cost': recipe_data['cost'],
                    'prep_time_min': recipe_data['prep_time_min']
                })
                current_recipe_idx += 1
            else:
                day_meals.append({'message': 'No more unique recipes available for this meal.'})
        meal_plan['plan_details'].append({'day': day, 'meals': day_meals})

    # Calculate summary nutrition
    total_calories = selected_recipes_df['calories'].sum()
    total_protein = selected_recipes_df['protein_g'].sum()
    total_fat = selected_recipes_df['fat_g'].sum()
    total_carbs = selected_recipes_df['carbs_g'].sum()
    total_cost = selected_recipes_df['cost'].sum()
    total_prep_time = selected_recipes_df['prep_time_min'].sum()

    meal_plan['summary'] = {
        'total_recipes_selected': len(selected_recipe_ids),
        'total_calories': round(total_calories, 2),
        'total_protein_g': round(total_protein, 2),
        'total_fat_g': round(total_fat, 2),
        'total_carbs_g': round(total_carbs, 2),
        'total_cost': round(total_cost, 2),
        'total_prep_time_min': round(total_prep_time, 2),
        'average_daily_calories': round(total_calories / preferences['planning_days'], 2) if preferences['planning_days'] > 0 else 0
    }
    logger.info("Meal plan report generated.")
    return meal_plan

def main() -> None:
    """
    Point d'entrée principal du script. Gère l'analyse des arguments en ligne de commande
    et orchestre l'ensemble du flux de travail.
    """
    parser = argparse.ArgumentParser(description="Generate optimized meal plans based on recipes and user preferences.")
    parser.add_argument('--config', type=str, default='config.json',
                        help="Path to the configuration file (JSON).")
    parser.add_argument('--recipes', type=str, default='recipes.csv',
                        help="Path to the recipes data file (CSV or JSON).")
    parser.add_argument('--preferences', type=str, default='preferences.json',
                        help="Path to the user preferences file (JSON).")
    parser.add_argument('--output', type=str, default='meal_plan.json',
                        help="Path to save the generated meal plan (JSON).")

    args = parser.parse_args()

    # 1. Load Configuration
    config = load_configuration(args.config)
    
    # Override paths if specified in config, otherwise use CLI args defaults
    recipes_filepath = args.recipes if args.recipes != parser.get_default('recipes') else config.get('recipes_data_path', args.recipes)
    preferences_filepath = args.preferences if args.preferences != parser.get_default('preferences') else config.get('user_preferences_path', args.preferences)
    output_filepath = args.output if args.output != parser.get_default('output') else config.get('output_meal_plan_path', args.output)

    logger.info(f"Using recipes file: {recipes_filepath}")
    logger.info(f"Using preferences file: {preferences_filepath}")
    logger.info(f"Output file: {output_filepath}")

    # 2. Load Data
    recipes_df = load_recipes_data(recipes_filepath)
    user_preferences = load_user_preferences(preferences_filepath)

    # Calculate total meals needed early to check feasibility
    total_meals_needed = user_preferences['daily_meals'] * user_preferences['planning_days']
    if total_meals_needed <= 0:
        logger.error("Total meals needed must be greater than zero. Check 'daily_meals' and 'planning_days' in preferences.")
        sys.exit(1)

    # 3. Prepare Optimization Data
    filtered_recipes_df, recipe_ids_for_optimization = prepare_optimization_data(recipes_df, user_preferences)
    
    # QA Correction: Check if enough unique recipes are available
    if len(recipe_ids_for_optimization) < total_meals_needed:
        logger.error(f"Not enough unique recipes ({len(recipe_ids_for_optimization)}) available after filtering to satisfy the required {total_meals_needed} meals.")
        sys.exit(1)

    # 4. Build and Solve Optimization Problem
    lp_problem = build_meal_plan_problem(filtered_recipes_df, user_preferences)
    solution = solve_meal_plan_problem(lp_problem)

    if solution['status'] != 'Optimal':
        logger.error("Failed to find an optimal meal plan. Please review constraints or preferences.")
        sys.exit(1)

    # 5. Generate Report
    meal_plan_report = generate_meal_plan_report(recipes_df, solution, user_preferences)

    # 6. Save Report
    try:
        with open(output_filepath, 'w') as f:
            json.dump(meal_plan_report, f, indent=4)
        logger.info(f"Meal plan successfully generated and saved to {output_filepath}")
    except Exception as e:
        logger.error(f"Error saving meal plan to {output_filepath}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()