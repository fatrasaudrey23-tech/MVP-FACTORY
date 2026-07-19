import requests
import json
import datetime
import logging
import os
from typing import List, Dict, Any, Optional, Union

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- A. Fonctions internes (privées, préfixées par `_`) ---

def _fetch_raw_data(source_config: Dict[str, Any]) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Récupère les données brutes à partir d'une source configurée (ex: URL d'API).
    Gère les requêtes HTTP, les erreurs de connexion, les codes de statut.
    """
    source_type = source_config.get('type')
    url = source_config.get('url')
    headers = source_config.get('headers', {})
    params = source_config.get('params', {})
    method = source_config.get('method', 'GET').upper()

    if not url:
        logger.error("URL non spécifiée dans la configuration de la source: %s", source_config)
        return []

    logger.info("Tentative de récupération des données depuis: %s (Type: %s)", url, source_type)

    if source_type == 'api':
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                data = source_config.get('data', {})
                response = requests.post(url, headers=headers, params=params, json=data, timeout=10)
            else:
                logger.error("Méthode HTTP non supportée: %s pour URL: %s", method, url)
                return []

            response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP
            logger.info("Données récupérées avec succès depuis: %s", url)
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Délai d'attente expiré lors de la récupération des données de l'API: %s", url)
        except requests.exceptions.HTTPError as e:
            logger.error("Erreur HTTP lors de la récupération des données de l'API: %s - %s", url, e)
        except requests.exceptions.ConnectionError as e:
            logger.error("Erreur de connexion lors de la récupération des données de l'API: %s - %s", url, e)
        except requests.exceptions.RequestException as e:
            logger.error("Erreur générale lors de la requête API: %s - %s", url, e)
        except json.JSONDecodeError:
            logger.error("Impossible de décoder la réponse JSON de l'API: %s", url)
        except Exception as e:
            logger.error("Une erreur inattendue est survenue lors de la récupération des données: %s - %s", url, e)
        return []
    elif source_type == 'local_file':
        # Exemple simple pour un fichier local JSON
        try:
            with open(url, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info("Données récupérées avec succès depuis le fichier local: %s", url)
            return data
        except FileNotFoundError:
            logger.error("Fichier local non trouvé: %s", url)
        except json.JSONDecodeError:
            logger.error("Impossible de décoder le fichier JSON: %s", url)
        except Exception as e:
            logger.error("Erreur lors de la lecture du fichier local: %s - %s", url, e)
        return []
    else:
        logger.warning("Type de source non supporté ou non spécifié: %s pour URL: %s", source_type, url)
        return []


def _parse_raw_item(raw_item: Dict[str, Any], item_type: str) -> Dict[str, Any]:
    """
    Parse un élément brut (promotion ou circulaire) dans un format interne standardisé.
    """
    parsed_item: Dict[str, Any] = {
        "id": str(raw_item.get('id', raw_item.get('uuid', raw_item.get('code', 'unknown_' + str(hash(frozenset(raw_item.items()))))))),
        "type": item_type,
        "title": raw_item.get('title', 'Titre non disponible'),
        "description": raw_item.get('description', raw_item.get('details', 'Description non disponible')),
        "store": raw_item.get('store', raw_item.get('brand', 'Magasin inconnu')),
        "category": raw_item.get('category', 'Général'),
        "image_url": raw_item.get('image_url', raw_item.get('thumbnail', '')),
        "details_url": raw_item.get('details_url', raw_item.get('link', '')),
        "start_date": None,
        "end_date": None,
        "is_active": False,
        "original_price": None,
        "sale_price": None,
        "discount_percentage": None,
        "pages_data": None,
        "pdf_url": None,
    }

    # Date parsing
    now = datetime.datetime.now()
    start_date_str = raw_item.get('start_date', raw_item.get('valid_from'))
    end_date_str = raw_item.get('end_date', raw_item.get('valid_until'))

    if start_date_str:
        try:
            # Try parsing common formats. ISO 8601 is preferred.
            parsed_item['start_date'] = datetime.datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        except ValueError:
            logger.debug("Could not parse start_date '%s' for item %s", start_date_str, parsed_item['id'])
            pass # Keep as None

    if end_date_str:
        try:
            parsed_item['end_date'] = datetime.datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        except ValueError:
            logger.debug("Could not parse end_date '%s' for item %s", end_date_str, parsed_item['id'])
            pass # Keep as None

    # Calculate is_active
    if parsed_item['start_date'] and parsed_item['end_date']:
        parsed_item['is_active'] = (parsed_item['start_date'] <= now) and (now <= parsed_item['end_date'])
    elif parsed_item['start_date'] and not parsed_item['end_date']:
        parsed_item['is_active'] = (parsed_item['start_date'] <= now) # Active indefinitely from start
    elif not parsed_item['start_date'] and parsed_item['end_date']:
        parsed_item['is_active'] = (now <= parsed_item['end_date']) # Active until end_date

    # Specifics for 'promotion'
    if item_type == 'promotion':
        try:
            original_price = float(raw_item.get('original_price', raw_item.get('price_old')))
            parsed_item['original_price'] = original_price
        except (ValueError, TypeError):
            pass # Keep as None
        try:
            sale_price = float(raw_item.get('sale_price', raw_item.get('price_new', raw_item.get('discounted_price'))))
            parsed_item['sale_price'] = sale_price
        except (ValueError, TypeError):
            pass # Keep as None

        if parsed_item['original_price'] is not None and parsed_item['sale_price'] is not None \
                and parsed_item['original_price'] > 0:
            parsed_item['discount_percentage'] = round(
                ((parsed_item['original_price'] - parsed_item['sale_price']) / parsed_item['original_price']) * 100, 2
            )
        elif raw_item.get('discount_percentage') is not None:
            try:
                parsed_item['discount_percentage'] = float(raw_item['discount_percentage'])
            except (ValueError, TypeError):
                pass

    # Specifics for 'circulaire'
    elif item_type == 'circulaire':
        parsed_item['pages_data'] = raw_item.get('pages', [])
        parsed_item['pdf_url'] = raw_item.get('pdf_url', raw_item.get('brochure_url'))

    return parsed_item

# --- B. Fonctions publiques ---

def get_all_promotions_and_circulars(source_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Orchestre la récupération et le parsing de toutes les données de promotion et de circulaire
    à partir de différentes sources.
    """
    all_normalized_items: List[Dict[str, Any]] = []

    for config in source_configs:
        item_type = config.get('item_type')
        if not item_type:
            logger.warning("Configuration de source sans 'item_type' spécifié: %s. Ignorée.", config)
            continue

        logger.info("Traitement de la source pour le type '%s' (URL: %s)", item_type, config.get('url', 'N/A'))
        raw_data = _fetch_raw_data(config)

        if isinstance(raw_data, dict):
            # If the API returns a single object that might contain a list of items
            # This logic might need adjustment based on actual API responses.
            # Assuming a common pattern where a key like 'promotions' or 'circulars' holds the list.
            if item_type == 'promotion' and 'promotions' in raw_data:
                raw_data = raw_data['promotions']
            elif item_type == 'circulaire' and 'circulars' in raw_data:
                raw_data = raw_data['circulars']
            else:
                # If it's a single item, or a dict that doesn't fit the list pattern,
                # treat it as a list with one item if it's not already a list.
                raw_data = [raw_data] if isinstance(raw_data, dict) and raw_data else []

        if not isinstance(raw_data, list):
            logger.error("Les données brutes de la source %s ne sont pas une liste. Type reçu: %s. Ignorées.",
                         config.get('url', 'N/A'), type(raw_data))
            continue

        for raw_item in raw_data:
            try:
                normalized_item = _parse_raw_item(raw_item, item_type)
                all_normalized_items.append(normalized_item)
            except Exception as e:
                logger.error("Erreur lors du parsing d'un élément brut de type '%s': %s. Item: %s",
                             item_type, e, raw_item, exc_info=True)
    return all_normalized_items


def filter_and_sort_display_data(
    data_list: List[Dict[str, Any]],
    filters: Optional[Dict[str, Any]] = None,
    sort_config: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Applique des filtres et un tri à une liste d'éléments normalisés.
    """
    filtered_data = list(data_list) # Create a shallow copy to not modify the original list

    # Apply filters
    if filters:
        logger.info("Application des filtres: %s", filters)
        for key, value in filters.items():
            # Special handling for boolean filters like 'is_active'
            if isinstance(value, bool) and key in ['is_active']:
                filtered_data = [item for item in filtered_data if item.get(key) == value]
            # General case for string/numeric filters
            else:
                filtered_data = [item for item in filtered_data if str(item.get(key, '')).lower() == str(value).lower()]
        logger.info("%d éléments après filtrage.", len(filtered_data))

    # Apply sorting
    if sort_config:
        sort_key = sort_config.get('key')
        sort_order = sort_config.get('order', 'asc').lower()
        if sort_key:
            logger.info("Application du tri par '%s' en ordre '%s'", sort_key, sort_order)
            reverse_sort = (sort_order == 'desc')
            try:
                # Handle potential None values in sort_key for consistent sorting
                # None values will be placed at the beginning (asc) or end (desc)
                filtered_data.sort(key=lambda x: x.get(sort_key, '' if isinstance(x.get(sort_key), str) else float('-inf') if sort_key in ['start_date', 'end_date', 'original_price', 'sale_price'] else None),
                                   reverse=reverse_sort)
            except TypeError as e:
                logger.error("Erreur lors du tri par la clé '%s': %s. Assurez-vous que les types sont comparables.", sort_key, e)
        else:
            logger.warning("Clé de tri non spécifiée dans sort_config: %s", sort_config)

    return filtered_data


def serialize_data_for_api(data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convertit les objets datetime et autres types non JSON-sérialisables en un format
    adapté pour une réponse API (ex: chaînes ISO 8601).
    """
    serialized_list: List[Dict[str, Any]] = []
    for item in data_list:
        serialized_item = {}
        for key, value in item.items():
            if isinstance(value, datetime.datetime):
                serialized_item[key] = value.isoformat()
            elif isinstance(value, (float, int, str, bool, type(None))):
                serialized_item[key] = value
            elif isinstance(value, list):
                # Recursively serialize lists if they contain complex objects
                serialized_item[key] = [
                    v.isoformat() if isinstance(v, datetime.datetime) else v
                    for v in value
                ]
            elif isinstance(value, dict):
                # Simple dicts are kept as is, assuming no nested datetime objects needing serialization
                # For deeper serialization, a recursive function would be needed.
                # For this plan, assuming top-level datetime and simple nested lists/dicts.
                serialized_item[key] = value
            else:
                # Fallback for other non-serializable types, convert to string
                logger.warning("Type non standard trouvé pour la clé '%s': %s. Converti en chaîne.", key, type(value))
                serialized_item[key] = str(value)
        serialized_list.append(serialized_item)
    return serialized_list