import typing
import collections
import datetime

def _validate_inventory_item(item_data: typing.Dict) -> typing.Dict:
    """
    Fonction interne utilitaire pour valider et standardiser un dictionnaire d'item brut.
    """
    if not isinstance(item_data, dict):
        raise ValueError("Item data must be a dictionary.")

    required_keys = ['id', 'name', 'category', 'quantity', 'unit']
    for key in required_keys:
        if key not in item_data:
            raise ValueError(f"Missing required key in item data: {key}")

    if not isinstance(item_data['id'], str) or not item_data['id']:
        raise ValueError("Item 'id' must be a non-empty string.")
    if not isinstance(item_data['name'], str) or not item_data['name']:
        raise ValueError("Item 'name' must be a non-empty string.")
    if not isinstance(item_data['category'], str) or not item_data['category']:
        raise ValueError("Item 'category' must be a non-empty string.")
    if not isinstance(item_data['quantity'], (int, float)) or item_data['quantity'] <= 0:
        raise ValueError("Item 'quantity' must be a positive number.")
    if not isinstance(item_data['unit'], str) or not item_data['unit']:
        raise ValueError("Item 'unit' must be a non-empty string.")

    standardized_item = {
        'id': item_data['id'],
        'name': item_data['name'],
        'category': item_data['category'],
        'quantity': float(item_data['quantity']),
        'unit': item_data['unit'],
        'nutritional_info': item_data.get('nutritional_info', {}),
        'allergens': item_data.get('allergens', []),
        'expiry_date': item_data.get('expiry_date')
    }

    if standardized_item['expiry_date'] is not None and not isinstance(standardized_item['expiry_date'], datetime.datetime):
        raise ValueError("Item 'expiry_date' must be a datetime object or None.")

    if not isinstance(standardized_item['nutritional_info'], dict):
        raise ValueError("Item 'nutritional_info' must be a dictionary.")
    if not isinstance(standardized_item['allergens'], list):
        raise ValueError("Item 'allergens' must be a list.")

    return standardized_item

def load_inventory(raw_inventory_list: typing.List[typing.Dict]) -> typing.Dict[str, typing.Dict]:
    """
    Charge et standardise une liste d'items bruts en un inventaire utilisable.
    """
    inventory: typing.Dict[str, typing.Dict] = {}
    for item_data in raw_inventory_list:
        validated_item = _validate_inventory_item(item_data)
        item_id = validated_item['id']
        if item_id in inventory:
            # Agrégation simple par ID pour ce plan
            inventory[item_id]['quantity'] += validated_item['quantity']
        else:
            inventory[item_id] = validated_item
    return inventory

def _validate_lunch_box_template(template_data: typing.Dict) -> typing.Dict:
    """
    Fonction interne utilitaire pour valider et standardiser un dictionnaire de modèle de Lunch Box brut.
    """
    if not isinstance(template_data, dict):
        raise ValueError("Template data must be a dictionary.")

    if 'name' not in template_data or not isinstance(template_data['name'], str) or not template_data['name']:
        raise ValueError("LunchBoxTemplate 'name' must be a non-empty string.")
    if 'components' not in template_data or not isinstance(template_data['components'], list):
        raise ValueError("LunchBoxTemplate 'components' must be a list.")

    standardized_template = {
        'name': template_data['name'],
        'components': [],
        'total_calories_range': template_data.get('total_calories_range'),
        'max_total_items': template_data.get('max_total_items')
    }

    if standardized_template['total_calories_range'] is not None:
        if not isinstance(standardized_template['total_calories_range'], dict) or \
           'min' not in standardized_template['total_calories_range'] or \
           'max' not in standardized_template['total_calories_range'] or \
           not isinstance(standardized_template['total_calories_range']['min'], (int, float)) or \
           not isinstance(standardized_template['total_calories_range']['max'], (int, float)) or \
           standardized_template['total_calories_range']['min'] < 0 or \
           standardized_template['total_calories_range']['max'] < standardized_template['total_calories_range']['min']:
            raise ValueError("Invalid 'total_calories_range' format.")

    if standardized_template['max_total_items'] is not None and \
       (not isinstance(standardized_template['max_total_items'], int) or standardized_template['max_total_items'] <= 0):
        raise ValueError("Invalid 'max_total_items' format, must be a positive integer.")

    for component_data in template_data['components']:
        if not isinstance(component_data, dict):
            raise ValueError("Each component in 'components' must be a dictionary.")
        if 'category' not in component_data or not isinstance(component_data['category'], str) or not component_data['category']:
            raise ValueError("Component 'category' must be a non-empty string.")
        if 'min_quantity' not in component_data or not isinstance(component_data['min_quantity'], (int, float)) or component_data['min_quantity'] < 0:
            raise ValueError("Component 'min_quantity' must be a non-negative number.")

        standardized_component = {
            'category': component_data['category'],
            'min_quantity': float(component_data['min_quantity']),
            'max_quantity': component_data.get('max_quantity'),
            'required': component_data.get('required', True),
            'allowed_item_ids': component_data.get('allowed_item_ids')
        }

        if standardized_component['max_quantity'] is not None and \
           (not isinstance(standardized_component['max_quantity'], (int, float)) or \
            standardized_component['max_quantity'] < standardized_component['min_quantity']):
            raise ValueError("Component 'max_quantity' must be a number >= 'min_quantity' or None.")
        if not isinstance(standardized_component['required'], bool):
            raise ValueError("Component 'required' must be a boolean.")
        if standardized_component['allowed_item_ids'] is not None and \
           not isinstance(standardized_component['allowed_item_ids'], list):
            raise ValueError("Component 'allowed_item_ids' must be a list of strings or None.")
        if standardized_component['allowed_item_ids'] is not None:
            for item_id in standardized_component['allowed_item_ids']:
                if not isinstance(item_id, str) or not item_id:
                    raise ValueError("Each item_id in 'allowed_item_ids' must be a non-empty string.")

        standardized_template['components'].append(standardized_component)

    return standardized_template

def define_lunch_box_templates(raw_templates_list: typing.List[typing.Dict]) -> typing.Dict[str, typing.Dict]:
    """
    Charge et standardise une liste de modèles de Lunch Box bruts.
    """
    templates: typing.Dict[str, typing.Dict] = {}
    for template_data in raw_templates_list:
        validated_template = _validate_lunch_box_template(template_data)
        templates[validated_template['name']] = validated_template
    return templates

def _check_component_availability(inventory: typing.Dict[str, typing.Dict], component_req: typing.Dict) -> typing.List[str]:
    """
    Identifie les IDs d'items dans l'inventaire qui pourraient satisfaire une exigence de composant.
    """
    potential_items_ids: typing.List[str] = []
    required_category = component_req['category']
    min_quantity_req = component_req['min_quantity']
    allowed_item_ids = component_req['allowed_item_ids']

    for item_id, item in inventory.items():
        if item['category'] == required_category and item['quantity'] >= min_quantity_req:
            if allowed_item_ids is None or item_id in allowed_item_ids:
                potential_items_ids.append(item_id)
    return potential_items_ids

def _assemble_single_lunch_box_attempt(current_inventory: typing.Dict[str, typing.Dict], template: typing.Dict) -> typing.Optional[typing.Tuple[typing.List[typing.Dict], typing.Dict[str, typing.Dict]]]:
    """
    Tente d'assembler une seule Lunch Box en utilisant un modèle donné et l'inventaire actuel.
    """
    assembled_items: typing.List[typing.Dict] = []
    temp_inventory = {item_id: dict(item) for item_id, item in current_inventory.items()} # Copie de l'inventaire pour la tentative

    total_calories = 0.0
    total_distinct_items = 0

    # Prioriser les composants requis
    sorted_components = sorted(template['components'], key=lambda x: not x.get('required', True))

    for component_req in sorted_components:
        potential_items_ids = _check_component_availability(temp_inventory, component_req)

        if not potential_items_ids:
            if component_req.get('required', True):
                return None # Composant requis non disponible
            else:
                continue # Composant non requis, on passe

        # Stratégie simple: prendre l'item disponible avec la plus grande quantité
        # Ou, si date de péremption, prioriser celle qui se périme le plus tôt (non implémenté pour ce plan)
        selected_item_id = None
        selected_item_quantity = 0.0

        for item_id in potential_items_ids:
            item = temp_inventory[item_id]
            if item['quantity'] >= component_req['min_quantity']:
                # Ici, on pourrait ajouter une logique de tri plus complexe
                # Pour l'instant, prenons le premier qui convient
                selected_item_id = item_id
                selected_item_quantity = component_req['min_quantity'] # Prendre la quantité minimale requise
                break

        if selected_item_id is None:
            if component_req.get('required', True):
                return None # Même si des items sont potentiels, aucun n'a la quantité suffisante
            else:
                continue

        # Ajouter l'item à la Lunch Box et mettre à jour l'inventaire temporaire
        item_to_add = dict(temp_inventory[selected_item_id]) # Copie de l'item
        item_to_add['quantity'] = selected_item_quantity
        assembled_items.append(item_to_add)

        temp_inventory[selected_item_id]['quantity'] -= selected_item_quantity
        if temp_inventory[selected_item_id]['quantity'] <= 0:
            del temp_inventory[selected_item_id]

        # Mettre à jour les totaux pour les contraintes globales
        if 'nutritional_info' in item_to_add and 'calories' in item_to_add['nutritional_info']:
            total_calories += item_to_add['nutritional_info']['calories'] * (selected_item_quantity / current_inventory[selected_item_id]['quantity']) # Approximation simple
        total_distinct_items += 1

    # Vérifier les contraintes globales
    if template['total_calories_range'] is not None:
        if total_calories < template['total_calories_range']['min'] or \
           total_calories > template['total_calories_range']['max']:
            return None # Calories hors plage

    if template['max_total_items'] is not None and total_distinct_items > template['max_total_items']:
        return None # Trop d'items distincts

    return assembled_items, temp_inventory

def optimize_lunch_boxes(raw_inventory: typing.List[typing.Dict], raw_templates: typing.List[typing.Dict], max_boxes: typing.Optional[int] = None) -> typing.Tuple[typing.List[typing.List[typing.Dict]], typing.Dict[str, typing.Dict]]:
    """
    Fonction principale de l'algorithme. Orchestre le processus d'assemblage des Lunch Box.
    """
    inventory = load_inventory(raw_inventory)
    templates = define_lunch_box_templates(raw_templates)

    assembled_lunch_boxes: typing.List[typing.List[typing.Dict]] = []
    remaining_inventory = dict(inventory) # Copie initiale de l'inventaire

    box_count = 0
    while True:
        if max_boxes is not None and box_count >= max_boxes:
            break

        successful_assembly_this_iteration = False
        # Stratégie simple: essayer les modèles dans l'ordre où ils sont définis
        for template_name, template in templates.items():
            result = _assemble_single_lunch_box_attempt(remaining_inventory, template)
            if result:
                assembled_box, updated_inventory = result
                assembled_lunch_boxes.append(assembled_box)
                remaining_inventory = updated_inventory # Mettre à jour l'inventaire
                box_count += 1
                successful_assembly_this_iteration = True
                break # Une boîte a été assemblée, on peut tenter d'en assembler une autre avec l'inventaire mis à jour

        if not successful_assembly_this_iteration:
            # Plus aucune Lunch Box ne peut être assemblée avec les modèles et l'inventaire actuels
            break

    return assembled_lunch_boxes, remaining_inventory