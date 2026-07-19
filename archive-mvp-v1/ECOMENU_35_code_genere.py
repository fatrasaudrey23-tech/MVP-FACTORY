import json
import os
from typing import List, Dict, Any

def load_recipes(file_path: str) -> List[Dict[str, Any]]:
    """
    Charge les données des recettes depuis un fichier spécifié.
    Gère les exceptions de fichier non trouvé ou de format invalide.
    """
    if not os.path.exists(file_path):
        print(f"Erreur: Le fichier '{file_path}' n'a pas été trouvé.")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            recipes_data = json.load(f)
            if not isinstance(recipes_data, list):
                print(f"Erreur: Le contenu du fichier '{file_path}' n'est pas une liste de recettes.")
                return []
            return recipes_data
    except json.JSONDecodeError:
        print(f"Erreur: Le fichier '{file_path}' contient un JSON invalide.")
        return []
    except Exception as e:
        print(f"Une erreur inattendue est survenue lors du chargement du fichier: {e}")
        return []

def filter_recipes_by_dietary_regimes(recipes: List[Dict[str, Any]], desired_regimes: List[str], match_all: bool = False) -> List[Dict[str, Any]]:
    """
    Filtre une liste de recettes en fonction des régimes alimentaires souhaités.
    """
    if not desired_regimes:
        return list(recipes) # Retourne toutes les recettes si aucun régime n'est spécifié

    filtered_recipes: List[Dict[str, Any]] = []
    desired_regimes_set = set(desired_regimes)

    for recipe in recipes:
        # S'assurer que la clé 'dietary_regimes' existe et est une liste
        if "dietary_regimes" not in recipe or not isinstance(recipe["dietary_regimes"], list):
            continue # Ignorer les recettes qui ne respectent pas la structure attendue

        recipe_regimes_set = set(recipe["dietary_regimes"])

        if match_all:
            # Vérifie si TOUS les régimes souhaités sont présents dans la recette
            if desired_regimes_set.issubset(recipe_regimes_set):
                filtered_recipes.append(recipe)
        else:
            # Vérifie si AU MOINS UN des régimes souhaités est présent dans la recette
            if not desired_regimes_set.isdisjoint(recipe_regimes_set):
                filtered_recipes.append(recipe)
    return filtered_recipes

def display_recipes(recipes: List[Dict[str, Any]]) -> None:
    """
    Affiche de manière lisible les recettes fournies.
    """
    if not recipes:
        print("Aucune recette à afficher.")
        return

    print("\n--- Recettes ---")
    for i, recipe in enumerate(recipes):
        recipe_name = recipe.get("name", f"Recette {i+1} (Nom inconnu)")
        dietary_regimes = recipe.get("dietary_regimes", [])
        print(f"  - {recipe_name}")
        print(f"    Régimes: {', '.join(dietary_regimes) if dietary_regimes else 'Aucun'}")
    print("----------------")

def main() -> None:
    """
    Fonction principale pour orchestrer le chargement, le filtrage et l'affichage des recettes.
    """
    data_dir = "data"
    recipes_file_path = os.path.join(data_dir, "recipes.json")

    # --- Préparation du fichier de données d'exemple ---
    # Créer le répertoire 'data' s'il n'existe pas
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Dossier '{data_dir}' créé.")

    # Définir des données de recettes d'exemple
    example_recipes_data = [
        {"name": "Salade Quinoa Vegan", "ingredients": ["quinoa", "légumes"], "dietary_regimes": ["vegan", "sans_gluten"]},
        {"name": "Curry de Légumes Indien", "ingredients": ["légumes", "épices"], "dietary_regimes": ["végétarien", "vegan"]},
        {"name": "Pâtes Carbonara", "ingredients": ["pâtes", "œufs", "lardons"], "dietary_regimes": ["omnivore"]},
        {"name": "Soupe de Lentilles", "ingredients": ["lentilles", "carottes"], "dietary_regimes": ["végétarien", "sans_gluten"]},
        {"name": "Gâteau au Chocolat", "ingredients": ["chocolat", "farine", "œufs"], "dietary_regimes": ["végétarien"]},
        {"name": "Tofu Scramble", "ingredients": ["tofu", "légumes"], "dietary_regimes": ["vegan", "sans_gluten", "sans_lactose"]},
        {"name": "Poulet Rôti", "ingredients": ["poulet", "pommes de terre"], "dietary_regimes": ["omnivore", "sans_gluten"]}
    ]

    # Écrire les données d'exemple dans le fichier JSON
    try:
        with open(recipes_file_path, 'w', encoding='utf-8') as f:
            json.dump(example_recipes_data, f, indent=4, ensure_ascii=False)
        print(f"Fichier '{recipes_file_path}' créé/mis à jour avec des données d'exemple.")
    except Exception as e:
        print(f"Erreur lors de la création/mise à jour du fichier de recettes d'exemple: {e}")
        return
    # --- Fin de la préparation ---

    print(f"Chargement des recettes depuis '{recipes_file_path}'...")
    all_recipes = load_recipes(recipes_file_path)

    if not all_recipes:
        print("Aucune recette chargée. Arrêt du programme.")
        return

    print("\nToutes les recettes disponibles :")
    display_recipes(all_recipes)

    # --- Scénario de test 1: Filtrage "au moins un" (match_all=False) ---
    print("\n--- Test 1: Filtrage 'vegan' ou 'sans_gluten' (match_all=False) ---")
    desired_regimes_1 = ["vegan", "sans_gluten"]
    filtered_1 = filter_recipes_by_dietary_regimes(all_recipes, desired_regimes_1, match_all=False)
    display_recipes(filtered_1)

    # --- Scénario de test 2: Filtrage "tous" (match_all=True) ---
    print("\n--- Test 2: Filtrage 'vegan' ET 'sans_gluten' (match_all=True) ---")
    desired_regimes_2 = ["vegan", "sans_gluten"]
    filtered_2 = filter_recipes_by_dietary_regimes(all_recipes, desired_regimes_2, match_all=True)
    display_recipes(filtered_2)

    # --- Scénario de test 3: Filtrage avec un seul régime ---
    print("\n--- Test 3: Filtrage 'végétarien' (match_all=False, un seul régime) ---")
    desired_regimes_3 = ["végétarien"]
    filtered_3 = filter_recipes_by_dietary_regimes(all_recipes, desired_regimes_3, match_all=False)
    display_recipes(filtered_3)

    # --- Scénario de test 4: Filtrage sans résultat ---
    print("\n--- Test 4: Filtrage 'keto' (aucun résultat attendu) ---")
    desired_regimes_4 = ["keto"]
    filtered_4 = filter_recipes_by_dietary_regimes(all_recipes, desired_regimes_4, match_all=False)
    display_recipes(filtered_4)

    # --- Scénario de test 5: Filtrage avec un régime non existant mais un autre oui ---
    print("\n--- Test 5: Filtrage 'halal' ou 'omnivore' (match_all=False) ---")
    desired_regimes_5 = ["halal", "omnivore"]
    filtered_5 = filter_recipes_by_dietary_regimes(all_recipes, desired_regimes_5, match_all=False)
    display_recipes(filtered_5)

    # --- Scénario de test 6: Filtrage "tous" avec 3 régimes ---
    print("\n--- Test 6: Filtrage 'vegan' ET 'sans_gluten' ET 'sans_lactose' (match_all=True) ---")
    desired_regimes_6 = ["vegan", "sans_gluten", "sans_lactose"]
    filtered_6 = filter_recipes_by_dietary_regimes(all_recipes, desired_regimes_6, match_all=True)
    display_recipes(filtered_6)


if __name__ == "__main__":
    main()