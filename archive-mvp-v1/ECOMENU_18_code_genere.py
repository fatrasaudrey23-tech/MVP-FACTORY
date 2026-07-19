import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

import requests
from supabase import create_client, Client

# --- Configuration du logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constantes (ajustables selon le schéma réel) ---
SUPABASE_PROMOTIONS_TABLE = "promotions"
EXTERNAL_DATE_FORMAT = "%Y-%m-%d" # Exemple: "2023-01-01"

def initialiser_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    """
    Initialise et retourne une instance du client Supabase en utilisant les informations d'authentification fournies.
    """
    try:
        client: Client = create_client(supabase_url, supabase_key)
        logger.info("Client Supabase initialisé avec succès.")
        return client
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du client Supabase : {e}")
        raise

def recuperer_promotions_source(source_api_url: str, source_api_key: Optional[str] = None) -> List[Dict]:
    """
    Récupère la liste des promotions depuis la source externe désignée (ex: API tierce, fichier CSV, etc.).
    """
    headers = {"Content-Type": "application/json"}
    if source_api_key:
        headers["Authorization"] = f"Bearer {source_api_key}"

    try:
        logger.info(f"Tentative de récupération des promotions depuis : {source_api_url}")
        response = requests.get(source_api_url, headers=headers, timeout=10)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP (4xx ou 5xx)
        promotions_data = response.json()
        logger.info(f"Récupération de {len(promotions_data)} promotions depuis la source externe.")
        return promotions_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur réseau ou HTTP lors de la récupération des promotions source : {e}")
        return []
    except ValueError as e:
        logger.error(f"Erreur de parsing JSON de la réponse source : {e}")
        return []

def formater_promotion_pour_supabase(promotion_data: Dict) -> Dict:
    """
    Transforme un dictionnaire de données de promotion brutes (issues de la source) en un format compatible avec
    le schéma de la table `promotions` dans Supabase.
    """
    formatted_promo: Dict[str, Any] = {}
    try:
        # Mappage des champs de la source vers les colonnes de la table Supabase
        # id_externe est crucial pour l'upsert
        formatted_promo['id_externe'] = str(promotion_data.get('id') or promotion_data.get('external_id'))
        formatted_promo['nom'] = promotion_data.get('name') or promotion_data.get('title')
        formatted_promo['description'] = promotion_data.get('description') or promotion_data.get('details')
        formatted_promo['type_remise'] = promotion_data.get('discountType') or promotion_data.get('type')
        
        # S'assurer que la valeur est numérique (float)
        try:
            formatted_promo['valeur'] = float(promotion_data.get('discountValue', 0))
        except (ValueError, TypeError):
            formatted_promo['valeur'] = 0.0
            logger.warning(f"Valeur de remise invalide pour la promotion {formatted_promo.get('id_externe')}. Défaut à 0.0.")

        # Conversion des dates en format ISO 8601 pour Supabase (TIMESTAMPTZ)
        start_date_str = promotion_data.get('startDate') or promotion_data.get('date_debut')
        end_date_str = promotion_data.get('endDate') or promotion_data.get('date_fin')

        if start_date_str:
            try:
                dt_start = datetime.fromisoformat(start_date_str)
                formatted_promo['date_debut'] = dt_start.isoformat()
            except ValueError:
                try:
                    dt_start = datetime.strptime(start_date_str, EXTERNAL_DATE_FORMAT)
                    formatted_promo['date_debut'] = dt_start.isoformat()
                except ValueError:
                    logger.warning(f"Impossible de parser la date de début '{start_date_str}' pour la promotion {formatted_promo.get('id_externe')}. Valeur ignorée.")
                    formatted_promo['date_debut'] = None
        else:
            formatted_promo['date_debut'] = None

        if end_date_str:
            try:
                dt_end = datetime.fromisoformat(end_date_str)
                # Si la date de fin est juste une date (YYYY-MM-DD), la définir à la fin de la journée
                if len(end_date_str) == 10: # YYYY-MM-DD
                    dt_end = dt_end.replace(hour=23, minute=59, second=59, microsecond=999999)
                formatted_promo['date_fin'] = dt_end.isoformat()
            except ValueError:
                try:
                    dt_end = datetime.strptime(end_date_str, EXTERNAL_DATE_FORMAT)
                    dt_end = dt_end.replace(hour=23, minute=59, second=59, microsecond=999999) # Fin de journée
                    formatted_promo['date_fin'] = dt_end.isoformat()
                except ValueError:
                    logger.warning(f"Impossible de parser la date de fin '{end_date_str}' pour la promotion {formatted_promo.get('id_externe')}. Valeur ignorée.")
                    formatted_promo['date_fin'] = None
        else:
            formatted_promo['date_fin'] = None

        # Gérer le statut actif
        formatted_promo['actif'] = bool(promotion_data.get('isActive', True)) # Par défaut à True si non spécifié

        # Vérifications essentielles
        if not formatted_promo.get('id_externe'):
            logger.error(f"Promotion source sans 'id' ou 'external_id' : {promotion_data}. Impossible de la formater et de la synchroniser.")
            return {}
        if not formatted_promo.get('nom'):
            logger.warning(f"Promotion {formatted_promo['id_externe']} sans 'nom'.")

    except Exception as e:
        logger.error(f"Erreur inattendue lors du formatage de la promotion {promotion_data.get('id')}: {e}")
        return {}
    return formatted_promo

def recuperer_promotions_existantes(supabase_client: Client, table_name: str) -> Dict[str, Dict]:
    """
    Récupère toutes les promotions actuellement stockées dans la table Supabase spécifiée.
    """
    existing_promotions: Dict[str, Dict] = {}
    try:
        response = supabase_client.from_(table_name).select('*').execute()
        if response.data:
            for promo in response.data:
                if promo.get('id_externe'):
                    existing_promotions[promo['id_externe']] = promo
            logger.info(f"Récupération de {len(existing_promotions)} promotions existantes depuis Supabase.")
        else:
            logger.info("Aucune promotion existante trouvée dans Supabase.")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des promotions existantes de Supabase : {e}")
    return existing_promotions

def preparer_operations_synchronisation(
    promotions_source_formatees: List[Dict],
    promotions_existantes: Dict[str, Dict]
) -> Dict[str, List[Dict]]:
    """
    Compare les promotions de la source avec celles existantes dans Supabase et détermine les opérations
    (insertion, mise à jour, désactivation) nécessaires.
    """
    operations: Dict[str, List[Dict]] = {
        'inserer': [],
        'mettre_a_jour': [],
        'desactiver': []
    }

    # Créer un set des IDs externes des promotions existantes pour un suivi facile
    existing_external_ids = set(promotions_existantes.keys())

    for source_promo in promotions_source_formatees:
        external_id = source_promo.get('id_externe')
        if not external_id:
            logger.warning(f"Promotion source ignorée car elle n'a pas d'id_externe : {source_promo}")
            continue

        if external_id not in promotions_existantes:
            # Nouvelle promotion à insérer
            operations['inserer'].append(source_promo)
        else:
            # Promotion existante, vérifier si elle a changé
            existing_promo = promotions_existantes[external_id]
            
            # Comparer les champs pertinents. Exclure les champs auto-générés ou non pertinents pour la comparaison.
            fields_to_compare = [
                'nom', 'description', 'date_debut', 'date_fin',
                'type_remise', 'valeur', 'actif'
            ]
            
            changed = False
            for field in fields_to_compare:
                source_value = source_promo.get(field)
                existing_value = existing_promo.get(field)

                # Normaliser les dates pour la comparaison (enlever microsecondes, fuseaux horaires si nécessaire)
                if field in ['date_debut', 'date_fin'] and source_value is not None and existing_value is not None:
                    try:
                        dt_source = datetime.fromisoformat(source_value.replace('Z', '+00:00')) # Gérer 'Z' pour UTC
                        dt_existing = datetime.fromisoformat(existing_value.replace('Z', '+00:00'))
                        # Comparer sans les microsecondes pour éviter des différences insignifiantes
                        if dt_source.replace(microsecond=0) != dt_existing.replace(microsecond=0):
                            changed = True
                            break
                    except ValueError:
                        # Si les dates ne sont pas parsables, comparer comme des chaînes
                        if str(source_value) != str(existing_value):
                            changed = True
                            break
                elif source_value != existing_value:
                    changed = True
                    break
            
            if changed:
                operations['mettre_a_jour'].append(source_promo)

            # Retirer cet ID de l'ensemble des IDs existants pour marquer qu'il a été traité
            existing_external_ids.discard(external_id)

    # Les IDs restants dans existing_external_ids ne sont plus dans la source et devraient être désactivés
    for external_id_to_deactivate in existing_external_ids:
        # On n'ajoute que l'id_externe, car seul ce champ est nécessaire pour la clause WHERE de la désactivation
        operations['desactiver'].append({'id_externe': external_id_to_deactivate})

    logger.info(f"Opérations de synchronisation préparées : "
                f"Insertions: {len(operations['inserer'])}, "
                f"Mises à jour: {len(operations['mettre_a_jour'])}, "
                f"Désactivations: {len(operations['desactiver'])}")
    return operations

def executer_operations_supabase(
    supabase_client: Client,
    table_name: str,
    operations: Dict[str, List[Dict]]
) -> Dict[str, int]:
    """
    Exécute les opérations d'insertion, de mise à jour et de désactivation/suppression dans la table Supabase.
    """
    results_count: Dict[str, int] = {
        'inserted': 0,
        'updated': 0,
        'deactivated': 0
    }

    # Opérations d'insertion et de mise à jour via upsert (si id_externe est UNIQUE)
    promos_to_upsert = operations['inserer'] + operations['mettre_a_jour']
    if promos_to_upsert:
        try:
            logger.info(f"Tentative d'upsert de {len(promos_to_upsert)} promotions.")
            # Supabase upsert insérera si 'id_externe' n'existe pas, mettra à jour si c'est le cas
            response = supabase_client.from_(table_name).upsert(promos_to_upsert, on_conflict='id_externe').execute()
            if response.data:
                # La réponse de l'upsert ne distingue pas directement les inserts des updates
                # Nous nous basons sur les listes préparées pour les compteurs
                results_count['inserted'] += len(operations['inserer'])
                results_count['updated'] += len(operations['mettre_a_jour'])
                logger.info(f"Upsert de {len(response.data)} promotions terminé.")
            else:
                logger.warning(f"Upsert a retourné une réponse vide pour {len(promos_to_upsert)} promotions.")
        except Exception as e:
            logger.error(f"Erreur lors de l'upsert des promotions : {e}")

    # Opérations de désactivation (mettre 'actif' à False)
    if operations['desactiver']:
        for promo_to_deactivate in operations['desactiver']:
            external_id = promo_to_deactivate.get('id_externe')
            if not external_id:
                logger.warning(f"Promotion à désactiver sans 'id_externe' ignorée : {promo_to_deactivate}")
                continue
            try:
                logger.debug(f"Désactivation de la promotion avec id_externe: {external_id}")
                response = supabase_client.from_(table_name).update({'actif': False}).eq('id_externe', external_id).execute()
                if response.data and len(response.data) > 0:
                    results_count['deactivated'] += 1
                else:
                    logger.warning(f"Aucune promotion désactivée pour id_externe: {external_id}. Peut-être déjà inactive ou non trouvée.")
            except Exception as e:
                logger.error(f"Erreur lors de la désactivation de la promotion {external_id}: {e}")
    
    logger.info(f"Opérations Supabase terminées. Insérées: {results_count['inserted']}, Mises à jour: {results_count['updated']}, Désactivées: {results_count['deactivated']}")
    return results_count

def executer_synchronisation_promotions(
    supabase_url: str,
    supabase_key: str,
    supabase_table_name: str,
    source_api_url: str,
    source_api_key: Optional[str] = None
) -> None:
    """
    Fonction principale orchestrant l'ensemble du processus de synchronisation des promotions.
    """
    logger.info("Début de la synchronisation des promotions.")
    try:
        # 1. Initialiser le client Supabase
        supabase_client = initialiser_supabase_client(supabase_url, supabase_key)

        # 2. Récupérer les promotions depuis la source externe
        promotions_source = recuperer_promotions_source(source_api_url, source_api_key)
        if not promotions_source:
            logger.warning("Aucune promotion récupérée de la source externe. Fin de la synchronisation.")
            return

        # 3. Formater les promotions pour Supabase
        # Filtrer les promotions qui n'ont pas pu être formatées (retournent {})
        promotions_source_formatees = [
            p for p_raw in promotions_source if (p := formater_promotion_pour_supabase(p_raw))
        ]
        if not promotions_source_formatees:
            logger.warning("Aucune promotion formatée avec succès. Fin de la synchronisation.")
            return
        
        # 4. Récupérer les promotions existantes dans Supabase
        promotions_existantes = recuperer_promotions_existantes(supabase_client, supabase_table_name)

        # 5. Préparer les opérations de synchronisation (insertions, mises à jour, désactivations)
        operations = preparer_operations_synchronisation(promotions_source_formatees, promotions_existantes)

        # 6. Exécuter les opérations dans Supabase
        results = executer_operations_supabase(supabase_client, supabase_table_name, operations)

        logger.info(f"Synchronisation des promotions terminée. Résumé : "
                    f"Insérées: {results['inserted']}, Mises à jour: {results['updated']}, "
                    f"Désactivées: {results['deactivated']}.")

    except Exception as e:
        logger.critical(f"Une erreur critique est survenue lors de la synchronisation des promotions : {e}", exc_info=True)
    finally:
        logger.info("Fin du processus de synchronisation des promotions.")

# --- Point d'entrée pour l'exécution du script ---
if __name__ == "__main__":
    # Charger les variables d'environnement
    # Assurez-vous que ces variables sont définies dans votre environnement d'exécution
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") # Utiliser la clé de rôle de service pour les opérations backend
    SOURCE_API_URL = os.getenv("PROMOTION_SOURCE_API_URL")
    SOURCE_API_KEY = os.getenv("PROMOTION_SOURCE_API_KEY") # Optionnel

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.critical("Les variables d'environnement SUPABASE_URL et SUPABASE_SERVICE_KEY doivent être définies.")
        exit(1)

    if not SOURCE_API_URL:
        logger.critical("La variable d'environnement PROMOTION_SOURCE_API_URL doit être définie.")
        exit(1)

    executer_synchronisation_promotions(
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_KEY,
        supabase_table_name=SUPABASE_PROMOTIONS_TABLE,
        source_api_url=SOURCE_API_URL,
        source_api_key=SOURCE_API_KEY
    )