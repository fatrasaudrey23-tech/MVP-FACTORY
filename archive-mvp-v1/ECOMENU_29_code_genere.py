import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

# --- Helper functions (simulating external data sources or complex logic) ---

def _fetch_user_meal_plan(user_id: str) -> List[Dict[str, Any]]:
    """
    Fonction utilitaire interne chargée de la récupération des données brutes du plan de repas
    pour un utilisateur spécifique.

    Simule une requête HTTP (via `requests`) vers l'API backend ou une requête à la base de données.
    Pour cette implémentation standalone, des données fictives sont retournées.
    """
    print(f"DEBUG: Attempting to fetch meal plan for user_id: {user_id}")

    # Simuler une erreur de récupération de données
    if user_id == "error_fetch":
        raise requests.exceptions.RequestException("Simulated network error during meal plan fetch.")
    if user_id == "no_plan_user":
        print("DEBUG: No meal plan found for 'no_plan_user'. Returning empty list.")
        return []

    # Données de repas fictives pour la démonstration
    # Dans un scénario réel, ces données viendraient d'une API ou d'une base de données
    dummy_meal_plans = {
        "user123": [
            {"meal_id": "m001", "name": "Oatmeal with berries", "date": "2023-10-26", "type": "breakfast", "calories": 350},
            {"meal_id": "m002", "name": "Chicken salad", "date": "2023-10-26", "type": "lunch", "calories": 450},
            {"meal_id": "m003", "name": "Salmon with asparagus", "date": "2023-10-26", "type": "dinner", "calories": 600},
            {"meal_id": "m004", "name": "Scrambled eggs", "date": "2023-10-27", "type": "breakfast", "calories": 300},
            {"meal_id": "m005", "name": "Vegetable soup", "date": "2023-10-27", "type": "lunch", "calories": 300},
            {"meal_id": "m006", "name": "Pasta primavera", "date": "2023-10-27", "type": "dinner", "calories": 700},
        ],
        "user456": [
            {"meal_id": "m010", "name": "Yogurt with granola", "date": "2023-10-28", "type": "breakfast", "calories": 320},
            {"meal_id": "m011", "name": "Quinoa bowl", "date": "2023-10-28", "type": "lunch", "calories": 480},
        ]
    }

    meal_plan = dummy_meal_plans.get(user_id, [])
    print(f"DEBUG: Fetched {len(meal_plan)} meals for {user_id}.")
    return meal_plan

def _format_meal_plan_for_display(raw_meal_plan_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fonction utilitaire interne pour transformer les données brutes du plan de repas en un format
    structuré et facilement consommable par l'interface utilisateur.
    """
    print(f"DEBUG: Formatting {len(raw_meal_plan_data)} raw meal entries.")
    formatted_plan: Dict[str, Any] = {
        "meals_by_date": {},
        "summary": {"total_calories_planned": 0}
    }
    total_calories = 0

    for meal in raw_meal_plan_data:
        meal_date_str = meal.get("date")
        meal_type = meal.get("type", "unknown").lower()
        calories = meal.get("calories", 0)

        if not meal_date_str:
            print(f"WARNING: Meal entry missing 'date' field: {meal}")
            continue

        if meal_date_str not in formatted_plan["meals_by_date"]:
            formatted_plan["meals_by_date"][meal_date_str] = {
                "breakfast": [],
                "lunch": [],
                "dinner": [],
                "snack": [],
                "other": [],
                "daily_calories": 0
            }

        target_list = formatted_plan["meals_by_date"][meal_date_str].get(meal_type, formatted_plan["meals_by_date"][meal_date_str]["other"])
        target_list.append(meal)
        formatted_plan["meals_by_date"][meal_date_str]["daily_calories"] += calories
        total_calories += calories

    formatted_plan["summary"]["total_calories_planned"] = total_calories
    print(f"DEBUG: Formatting complete. Total planned calories: {total_calories}")
    return formatted_plan

# --- Main controller function ---

def initialize_meal_planner_screen(user_id: str) -> Dict[str, Any]:
    """
    Fonction principale et point d'entrée pour l'initialisation de l'écran du planificateur de repas.
    Elle orchestre la récupération des données spécifiques à l'utilisateur et leur formatage
    pour une présentation optimale sur l'interface utilisateur.
    """
    if not user_id or not isinstance(user_id, str):
        raise ValueError("User ID must be a non-empty string.")

    print(f"INFO: Initializing meal planner screen for user: {user_id}")

    try:
        raw_meal_plan = _fetch_user_meal_plan(user_id)
        formatted_meal_plan = _format_meal_plan_for_display(raw_meal_plan)

        # Simuler des préférences utilisateur ou d'autres données nécessaires à l'UI
        user_preferences = {
            "display_units": "metric",
            "theme": "light",
            "notification_enabled": True
        }

        screen_data = {
            "user_id": user_id,
            "meal_plan_data": formatted_meal_plan,
            "user_preferences": user_preferences,
            "status": "success",
            "message": "Meal planner data loaded successfully."
        }
        print(f"INFO: Meal planner screen data prepared for user: {user_id}")
        return screen_data

    except ValueError as ve:
        print(f"ERROR: Validation error for user {user_id}: {ve}")
        return {
            "user_id": user_id,
            "meal_plan_data": {},
            "user_preferences": {},
            "status": "error",
            "message": str(ve)
        }
    except requests.exceptions.RequestException as re:
        print(f"ERROR: Failed to fetch meal plan for user {user_id} due to network/API error: {re}")
        return {
            "user_id": user_id,
            "meal_plan_data": {},
            "user_preferences": {},
            "status": "error",
            "message": "Could not retrieve meal plan. Please try again later."
        }
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while initializing meal planner for user {user_id}: {e}")
        return {
            "user_id": user_id,
            "meal_plan_data": {},
            "user_preferences": {},
            "status": "error",
            "message": "An unexpected error occurred."
        }

# --- Example Usage (for standalone testing) ---
if __name__ == "__main__":
    print("--- Testing initialize_meal_planner_screen ---")

    # Test Case 1: Valid user with meal plan
    print("\n--- Test Case 1: Valid user (user123) ---")
    try:
        screen_data_user123 = initialize_meal_planner_screen("user123")
        print("Result for user123:")
        print(json.dumps(screen_data_user123, indent=2))
    except Exception as e:
        print(f"Test Case 1 failed: {e}")

    # Test Case 2: Valid user with a different meal plan
    print("\n--- Test Case 2: Valid user (user456) ---")
    try:
        screen_data_user456 = initialize_meal_planner_screen("user456")
        print("Result for user456:")
        print(json.dumps(screen_data_user456, indent=2))
    except Exception as e:
        print(f"Test Case 2 failed: {e}")

    # Test Case 3: User with no meal plan
    print("\n--- Test Case 3: User with no plan (no_plan_user) ---")
    try:
        screen_data_no_plan = initialize_meal_planner_screen("no_plan_user")
        print("Result for no_plan_user:")
        print(json.dumps(screen_data_no_plan, indent=2))
    except Exception as e:
        print(f"Test Case 3 failed: {e}")

    # Test Case 4: Invalid user ID (empty string)
    print("\n--- Test Case 4: Invalid user ID (empty string) ---")
    try:
        screen_data_invalid = initialize_meal_planner_screen("")
        print("Result for empty user ID:")
        print(json.dumps(screen_data_invalid, indent=2))
    except Exception as e:
        print(f"Test Case 4 failed (caught expected exception): {e}")

    # Test Case 5: Simulate fetch error
    print("\n--- Test Case 5: Simulate fetch error (error_fetch) ---")
    try:
        screen_data_error_fetch = initialize_meal_planner_screen("error_fetch")
        print("Result for error_fetch:")
        print(json.dumps(screen_data_error_fetch, indent=2))
    except Exception as e:
        print(f"Test Case 5 failed (caught expected exception): {e}")

    # Test Case 6: User ID not found in dummy data (should return empty plan)
    print("\n--- Test Case 6: User ID not found (unknown_user) ---")
    try:
        screen_data_unknown = initialize_meal_planner_screen("unknown_user")
        print("Result for unknown_user:")
        print(json.dumps(screen_data_unknown, indent=2))
    except Exception as e:
        print(f"Test Case 6 failed: {e}")