import datetime
import json
import uuid
from collections import defaultdict, Counter
from typing import List, Dict, Optional, Any

# --------------------------------------------------------------------------------
# 3.6. Module de Persistance des Données (DataManager)
# --------------------------------------------------------------------------------
class DataManager:
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self._data: Dict[str, Any] = self._load_data()

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    def _load_data(self) -> Dict[str, Any]:
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Initialize with empty structures if file doesn't exist
            return {
                'ingredients': [],
                'recipes': [],
                'lunch_boxes': [],
                'sales_history': []
            }
        except json.JSONDecodeError:
            print(f"Warning: Corrupt JSON file at {self.filepath}. Initializing with empty data.")
            return {
                'ingredients': [],
                'recipes': [],
                'lunch_boxes': [],
                'sales_history': []
            }

    def sauvegarder_donnees(self) -> None:
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=4)


# --------------------------------------------------------------------------------
# 3.2. Module de Gestion des Ingrédients (IngredientManager)
# --------------------------------------------------------------------------------
class IngredientManager:
    def __init__(self, data_manager: DataManager) -> None:
        self._data_manager = data_manager
        self._ingredients = data_manager.data['ingredients']

    def ajouter_ingredient(self, nom: str, quantite: float, unite: str, date_peremption_str: str, cout_unitaire: float, fournisseur: Optional[str] = None) -> str:
        ingredient_id = uuid.uuid4().hex
        new_ingredient = {
            'id': ingredient_id,
            'nom': nom,
            'quantite_stock': quantite,
            'unite_mesure': unite,
            'date_peremption': date_peremption_str,
            'cout_unitaire': cout_unitaire,
            'fournisseur': fournisseur
        }
        self._ingredients.append(new_ingredient)
        self._data_manager.sauvegarder_donnees()
        return ingredient_id

    def mettre_a_jour_quantite_ingredient(self, ingredient_id: str, changement_quantite: float) -> bool:
        for ingredient in self._ingredients:
            if ingredient['id'] == ingredient_id:
                if ingredient['quantite_stock'] + changement_quantite >= 0:
                    ingredient['quantite_stock'] += changement_quantite
                    self._data_manager.sauvegarder_donnees()
                    return True
                else:
                    print(f"Erreur: Quantité insuffisante pour l'ingrédient {ingredient['nom']} ({ingredient_id}).")
                    return False
        return False

    def get_details_ingredient(self, ingredient_id: str) -> Optional[Dict[str, Any]]:
        for ingredient in self._ingredients:
            if ingredient['id'] == ingredient_id:
                return ingredient
        return None

    def lister_ingredients_proches_peremption(self, jours_avant_peremption: int) -> List[Dict[str, Any]]:
        today = datetime.datetime.now()
        close_to_expiry = []
        for ingredient in self._ingredients:
            try:
                peremption_date = datetime.datetime.strptime(ingredient['date_peremption'], '%Y-%m-%d')
                if 0 <= (peremption_date - today).days <= jours_avant_peremption:
                    close_to_expiry.append(ingredient)
            except ValueError:
                print(f"Warning: Date de péremption invalide pour l'ingrédient {ingredient['nom']}: {ingredient['date_peremption']}")
        return close_to_expiry

    def supprimer_ingredient(self, ingredient_id: str) -> bool:
        initial_len = len(self._ingredients)
        self._ingredients[:] = [i for i in self._ingredients if i['id'] != ingredient_id]
        if len(self._ingredients) < initial_len:
            self._data_manager.sauvegarder_donnees()
            return True
        return False


# --------------------------------------------------------------------------------
# 3.3. Module de Gestion des Recettes (RecipeManager)
# --------------------------------------------------------------------------------
class RecipeManager:
    def __init__(self, data_manager: DataManager) -> None:
        self._data_manager = data_manager
        self._recipes = data_manager.data['recipes']

    def ajouter_recette(self, nom: str, ingredients_requis: List[Dict[str, Any]], etapes_preparation: List[str], rendement: int) -> str:
        recette_id = uuid.uuid4().hex
        new_recipe = {
            'id': recette_id,
            'nom': nom,
            'ingredients_requis': ingredients_requis,
            'etapes_preparation': etapes_preparation,
            'rendement': rendement
        }
        self._recipes.append(new_recipe)
        self._data_manager.sauvegarder_donnees()
        return recette_id

    def mettre_a_jour_recette(self, recette_id: str, nouveaux_ingredients_requis: Optional[List[Dict[str, Any]]] = None, nouvelles_etapes: Optional[List[str]] = None, nouveau_rendement: Optional[int] = None) -> bool:
        for recipe in self._recipes:
            if recipe['id'] == recette_id:
                if nouveaux_ingredients_requis is not None:
                    recipe['ingredients_requis'] = nouveaux_ingredients_requis
                if nouvelles_etapes is not None:
                    recipe['etapes_preparation'] = nouvelles_etapes
                if nouveau_rendement is not None:
                    recipe['rendement'] = nouveau_rendement
                self._data_manager.sauvegarder_donnees()
                return True
        return False

    def get_details_recette(self, recette_id: str) -> Optional[Dict[str, Any]]:
        for recipe in self._recipes:
            if recipe['id'] == recette_id:
                return recipe
        return None

    def lister_toutes_les_recettes(self) -> List[Dict[str, Any]]:
        return list(self._recipes)


# --------------------------------------------------------------------------------
# 3.4. Module de Production et Vente des Lunch Boxes (LunchBoxProcessor)
# --------------------------------------------------------------------------------
class LunchBoxProcessor:
    def __init__(self, data_manager: DataManager, ingredient_manager: IngredientManager, recipe_manager: RecipeManager) -> None:
        self._data_manager = data_manager
        self._ingredient_manager = ingredient_manager
        self._recipe_manager = recipe_manager
        self._lunch_boxes = data_manager.data['lunch_boxes']
        self._sales_history = data_manager.data['sales_history']

    def verifier_disponibilite_ingredients_pour_recette(self, recette_id: str, quantite_lunch_boxes: int) -> bool:
        recipe = self._recipe_manager.get_details_recette(recette_id)
        if not recipe:
            print(f"Recette avec l'ID {recette_id} introuvable.")
            return False

        if recipe['rendement'] == 0:
            print(f"Erreur: Rendement de la recette {recipe['nom']} est de 0, impossible de produire.")
            return False

        batches_needed = (quantite_lunch_boxes + recipe['rendement'] - 1) // recipe['rendement']

        for req_ing in recipe['ingredients_requis']:
            ingredient_details = self._ingredient_manager.get_details_ingredient(req_ing['ingredient_id'])
            if not ingredient_details:
                print(f"Ingrédient requis {req_ing['ingredient_id']} pour la recette {recipe['nom']} introuvable.")
                return False
            
            required_quantity = req_ing['quantite'] * batches_needed
            if ingredient_details['quantite_stock'] < required_quantity:
                print(f"Stock insuffisant pour l'ingrédient {ingredient_details['nom']}. Requis: {required_quantity} {ingredient_details['unite_mesure']}, Disponible: {ingredient_details['quantite_stock']} {ingredient_details['unite_mesure']}")
                return False
        return True

    def preparer_lunch_boxes(self, recette_id: str, quantite: int, date_production_str: str) -> List[str]:
        if not self.verifier_disponibilite_ingredients_pour_recette(recette_id, quantite):
            return []

        recipe = self._recipe_manager.get_details_recette(recette_id)
        if not recipe:
            return []

        batches_needed = (quantite + recipe['rendement'] - 1) // recipe['rendement']

        for req_ing in recipe['ingredients_requis']:
            required_quantity = req_ing['quantite'] * batches_needed
            self._ingredient_manager.mettre_a_jour_quantite_ingredient(req_ing['ingredient_id'], -required_quantity)
        
        produced_lunch_box_ids = []
        production_date = datetime.datetime.strptime(date_production_str, '%Y-%m-%d')
        date_limite_vente = production_date + datetime.timedelta(days=2) 
        
        for _ in range(quantite):
            lunch_box_id = uuid.uuid4().hex
            new_lunch_box = {
                'id': lunch_box_id,
                'nom_recette': recipe['nom'],
                'recette_id': recette_id,
                'date_production': date_production_str,
                'date_limite_vente': date_limite_vente.strftime('%Y-%m-%d'),
                'statut': 'disponible',
                'date_statut_change': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'raison_gaspillage': None
            }
            self._lunch_boxes.append(new_lunch_box)
            produced_lunch_box_ids.append(lunch_box_id)
        
        self._data_manager.sauvegarder_donnees()
        return produced_lunch_box_ids

    def enregistrer_vente_lunch_box(self, lunch_box_id: str, date_vente_str: str) -> bool:
        for lb in self._lunch_boxes:
            if lb['id'] == lunch_box_id and lb['statut'] == 'disponible':
                lb['statut'] = 'vendue'
                lb['date_statut_change'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._sales_history.append({
                    'date': date_vente_str,
                    'recette_id': lb['recette_id'],
                    'lunch_box_id': lunch_box_id,
                    'nom_recette': lb['nom_recette']
                })
                self._data_manager.sauvegarder_donnees()
                return True
        return False

    def enregistrer_gaspillage_lunch_box(self, lunch_box_id: str, date_gaspillage_str: str, raison: str) -> bool:
        for lb in self._lunch_boxes:
            if lb['id'] == lunch_box_id and lb['statut'] == 'disponible':
                lb['statut'] = 'jetee'
                lb['date_statut_change'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                lb['raison_gaspillage'] = raison
                self._data_manager.sauvegarder_donnees()
                return True
        return False

    def get_lunch_boxes_disponibles(self) -> List[Dict[str, Any]]:
        return [lb for lb in self._lunch_boxes if lb['statut'] == 'disponible']

    def lister_lunch_boxes_proches_peremption(self, jours_avant_peremption: int) -> List[Dict[str, Any]]:
        today = datetime.datetime.now()
        close_to_expiry = []
        for lb in self._lunch_boxes:
            if lb['statut'] == 'disponible':
                try:
                    peremption_date = datetime.datetime.strptime(lb['date_limite_vente'], '%Y-%m-%d')
                    if 0 <= (peremption_date - today).days <= jours_avant_peremption:
                        close_to_expiry.append(lb)
                except ValueError:
                    print(f"Warning: Date limite de vente invalide pour la Lunch Box {lb['id']}: {lb['date_limite_vente']}")
        return close_to_expiry


# --------------------------------------------------------------------------------
# 3.5. Module Anti-Gaspi et Rapports (WasteManagementAndReporting)
# --------------------------------------------------------------------------------
class WasteManagementAndReporting:
    def __init__(self, data_manager: DataManager, ingredient_manager: IngredientManager, recipe_manager: RecipeManager, lunchbox_processor: LunchBoxProcessor) -> None:
        self._data_manager = data_manager
        self._ingredient_manager = ingredient_manager
        self._recipe_manager = recipe_manager
        self._lunchbox_processor = lunchbox_processor
        self._lunch_boxes = data_manager.data['lunch_boxes']
        self._ingredients = data_manager.data['ingredients']
        self._sales_history = data_manager.data['sales_history']

    def generer_rapport_gaspillage_ingredients(self, date_debut_str: str, date_fin_str: str) -> Dict[str, Any]:
        start_date = datetime.datetime.strptime(date_debut_str, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(date_fin_str, '%Y-%m-%d')
        
        wasted_ingredients_report: Dict[str, Any] = {'total_cost': 0.0, 'details': []}
        
        # Report on ingredients expired in stock within the period
        for ingredient in self._ingredients:
            try:
                peremption_date = datetime.datetime.strptime(ingredient['date_peremption'], '%Y-%m-%d')
                if start_date <= peremption_date <= end_date and ingredient['quantite_stock'] > 0:
                    cost = ingredient['quantite_stock'] * ingredient['cout_unitaire']
                    wasted_ingredients_report['details'].append({
                        'id': ingredient['id'],
                        'nom': ingredient['nom'],
                        'quantite_jetee': ingredient['quantite_stock'],
                        'unite': ingredient['unite_mesure'],
                        'cout_total': cost,
                        'raison': 'Expiré en stock'
                    })
                    wasted_ingredients_report['total_cost'] += cost
            except ValueError:
                pass
        
        # Report on ingredients used in wasted lunch boxes within the period
        for lb in self._lunch_boxes:
            try:
                lb_waste_date = datetime.datetime.strptime(lb['date_statut_change'].split(' ')[0], '%Y-%m-%d')
                if lb['statut'] == 'jetee' and start_date <= lb_waste_date <= end_date:
                    recipe = self._recipe_manager.get_details_recette(lb['recette_id'])
                    if recipe:
                        for req_ing in recipe['ingredients_requis']:
                            ingredient_details = self._ingredient_manager.get_details_ingredient(req_ing['ingredient_id'])
                            if ingredient_details:
                                qty_per_lb = req_ing['quantite'] / float(recipe['rendement'])
                                cost = qty_per_lb * ingredient_details['cout_unitaire']
                                
                                wasted_ingredients_report['details'].append({
                                    'id': ingredient_details['id'],
                                    'nom': ingredient_details['nom'],
                                    'quantite_jetee': qty_per_lb,
                                    'unite': ingredient_details['unite_mesure'],
                                    'cout_total': cost,
                                    'raison': f"Utilisé dans Lunch Box jetée ({lb['raison_gaspillage']})"
                                })
                                wasted_ingredients_report['total_cost'] += cost
            except (ValueError, KeyError):
                pass
        
        return wasted_ingredients_report


    def generer_rapport_gaspillage_lunch_boxes(self, date_debut_str: str, date_fin_str: str) -> Dict[str, Any]:
        start_date = datetime.datetime.strptime(date_debut_str, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(date_fin_str, '%Y-%m-%d')
        
        wasted_lunch_boxes = []
        total_wasted_count = 0
        
        for lb in self._lunch_boxes:
            if lb['statut'] == 'jetee':
                try:
                    waste_date = datetime.datetime.strptime(lb['date_statut_change'].split(' ')[0], '%Y-%m-%d')
                    if start_date <= waste_date <= end_date:
                        wasted_lunch_boxes.append(lb)
                        total_wasted_count += 1
                except ValueError:
                    print(f"Warning: Date de statut invalide pour la Lunch Box {lb['id']}: {lb['date_statut_change']}")
        
        POTENTIAL_VALUE_PER_LUNCHBOX = 5.0
        total_potential_cost = total_wasted_count * POTENTIAL_VALUE_PER_LUNCHBOX

        reason_counts = Counter(lb['raison_gaspillage'] for lb in wasted_lunch_boxes)

        return {
            'total_lunch_boxes_jetees': total_wasted_count,
            'cout_potentiel_total': total_potential_cost,
            'raisons_gaspillage': dict(reason_counts),
            'details': wasted_lunch_boxes
        }

    def suggerer_utilisation_ingredients_perissables(self) -> List[Dict[str, Any]]:
        suggestions = []
        ingredients_proches_peremption = self._ingredient_manager.lister_ingredients_proches_peremption(7)
        
        all_recipes = self._recipe_manager.lister_toutes_les_recettes()

        for ingredient in ingredients_proches_peremption:
            ingredient_suggestions = {
                'ingredient_id': ingredient['id'],
                'nom_ingredient': ingredient['nom'],
                'date_peremption': ingredient['date_peremption'],
                'quantite_disponible': ingredient['quantite_stock'],
                'recettes_suggerees': []
            }
            for recipe in all_recipes:
                for req_ing in recipe['ingredients_requis']:
                    if req_ing['ingredient_id'] == ingredient['id']:
                        if ingredient['quantite_stock'] >= req_ing['quantite']:
                            ingredient_suggestions['recettes_suggerees'].append({
                                'recette_id': recipe['id'],
                                'nom_recette': recipe['nom'],
                                'quantite_requise_par_rendement': req_ing['quantite'],
                                'rendement_recette': recipe['rendement']
                            })
            if ingredient_suggestions['recettes_suggerees']:
                suggestions.append(ingredient_suggestions)
        return suggestions

    def analyser_tendances_demande(self, historique_ventes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if historique_ventes is None:
            historique_ventes = self._sales_history

        monthly_sales: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        total_sales_per_recipe: Dict[str, int] = defaultdict(int)

        for sale in historique_ventes:
            try:
                sale_date = datetime.datetime.strptime(sale['date'], '%Y-%m-%d')
                month_year = sale_date.strftime('%Y-%m')
                recipe_name = sale.get('nom_recette', 'Unknown Recipe')
                
                monthly_sales[month_year][recipe_name] += 1
                total_sales_per_recipe[recipe_name] += 1
            except (ValueError, KeyError):
                pass

        average_monthly_sales: Dict[str, Dict[str, float]] = defaultdict(dict)
        for recipe_name, sales_count in total_sales_per_recipe.items():
            # Count unique months a recipe was sold
            num_months_sold = len(set(sale_date.strftime('%Y-%m') for sale in historique_ventes if sale.get('nom_recette') == recipe_name))
            
            if num_months_sold > 0:
                average_monthly_sales[recipe_name]['average_sales_per_month'] = sales_count / float(num_months_sold)
            else:
                average_monthly_sales[recipe_name]['average_sales_per_month'] = 0.0

        suggested_production = {}
        for recipe_name, data in average_monthly_sales.items():
            suggested_production[recipe_name] = int(data['average_sales_per_month'] * 1.1)

        return {
            'monthly_sales_breakdown': monthly_sales,
            'total_sales_per_recipe': total_sales_per_recipe,
            'average_monthly_sales_per_recipe': average_monthly_sales,
            'suggested_production_next_period': suggested_production
        }