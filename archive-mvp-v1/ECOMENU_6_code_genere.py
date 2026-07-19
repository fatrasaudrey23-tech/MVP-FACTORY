import logging
from typing import List, Dict, Optional, Any

# Placeholder pour le connecteur de base de données ou le client API
# À remplacer par l'implémentation réelle (ex: SQLAlchemy Session, requests.Session)
class DBConnector:
    def fetch_all_retailers(self) -> List[Dict[str, Any]]:
        """Simule la récupération de toutes les enseignes depuis la base de données/API."""
        logging.info("Fetching all retailers from data source.")
        # Implémentation réelle : requêtes SQL ou appels API
        # Exemple de données simulées pour le test
        return [
            {"id": "carrefour", "name": "Carrefour", "logo_url": "http://example.com/carrefour.png", "is_active": True, "description": "Supermarché Carrefour"},
            {"id": "auchan", "name": "Auchan", "logo_url": "http://example.com/auchan.png", "is_active": True, "description": "Hypermarché Auchan"},
            {"id": "leclerc", "name": "Leclerc", "logo_url": "http://example.com/leclerc.png", "is_active": False, "description": "Centre Leclerc"},
            {"id": "intermarche", "name": "Intermarché", "logo_url": "http://example.com/intermarche.png", "is_active": True, "description": "Supermarché Intermarché"}
        ]

    def fetch_retailer_by_id(self, retailer_id: str) -> Optional[Dict[str, Any]]:
        """Simule la récupération d'une enseigne par ID."""
        logging.info(f"Fetching retailer {retailer_id} from data source.")
        # Implémentation réelle
        all_retailers = self.fetch_all_retailers() # Dans un vrai cas, ce serait une requête ciblée
        for retailer in all_retailers:
            if retailer.get("id") == retailer_id:
                return retailer
        return None

    def save_user_preferred_retailers(self, user_id: str, retailer_ids: List[str]) -> bool:
        """Simule la sauvegarde des préférences utilisateur."""
        logging.info(f"Saving preferences for user {user_id}: {retailer_ids}")
        # Implémentation réelle (ex: écriture en BDD)
        # Pour la simulation, on suppose toujours le succès
        return True

    def fetch_user_preferred_retailers(self, user_id: str) -> List[str]:
        """Simule la récupération des préférences utilisateur."""
        logging.info(f"Fetching preferences for user {user_id}")
        # Implémentation réelle (ex: lecture en BDD)
        # Pour la simulation, on retourne des données statiques/aléatoires
        if user_id == "user123":
            return ["carrefour", "auchan"]
        return []

# Configuration du logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class RetailerSelectionService:
    """
    Service pour la gestion des enseignes de distribution et la sélection par les utilisateurs.
    """

    def __init__(self, db_connector: DBConnector):
        """
        Initialise le service avec un connecteur de base de données/API.
        """
        self.db_connector = db_connector
        logger.info("RetailerSelectionService initialized.")

    def _get_all_raw_retailers(self) -> List[Dict[str, Any]]:
        """
        Fonction interne pour récupérer toutes les données brutes des enseignes.
        Gère la source de données (DB, API externe).

        Returns:
            List[Dict[str, Any]]: Liste des enseignes avec tous leurs attributs bruts.
        """
        try:
            retailers_data = self.db_connector.fetch_all_retailers()
            logger.debug(f"Successfully fetched {len(retailers_data)} raw retailers.")
            return retailers_data
        except Exception as e:
            logger.error(f"Error fetching raw retailers: {e}", exc_info=True)
            return []

    def get_all_available_retailers(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Récupère la liste de toutes les enseignes de distribution disponibles.

        Args:
            active_only (bool): Si True, ne retourne que les enseignes actives.

        Returns:
            List[Dict[str, Any]]: Une liste de dictionnaires, chaque dictionnaire représentant une enseigne
                                  avec des informations clés (id, nom, logo_url, etc.).
                                  Ex: [{"id": "carrefour", "name": "Carrefour", "logo_url": "..."}, ...]
        """
        logger.info(f"Retrieving all available retailers (active_only={active_only}).")
        raw_retailers = self._get_all_raw_retailers()
        
        processed_retailers = []
        for retailer in raw_retailers:
            # Assurez-vous que 'id' est présent pour éviter KeyError avant d'ajouter
            if 'id' not in retailer:
                logger.warning(f"Skipping retailer with missing 'id': {retailer}")
                continue

            if not active_only or retailer.get('is_active', False):
                # Filtrer et formater les données pour l'exposition publique
                processed_retailers.append({
                    "id": retailer.get('id'),
                    "name": retailer.get('name'),
                    "logo_url": retailer.get('logo_url'),
                    "description": retailer.get('description'),
                    # Ajouter d'autres champs pertinents pour la sélection
                })
        
        logger.info(f"Found {len(processed_retailers)} available retailers.")
        return processed_retailers

    def get_retailer_details_by_id(self, retailer_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les détails complets d'une enseigne spécifique par son ID.

        Args:
            retailer_id (str): L'identifiant unique de l'enseigne.

        Returns:
            Optional[Dict[str, Any]]: Un dictionnaire contenant les détails de l'enseigne,
                                     ou None si l'enseigne n'est pas trouvée.
        """
        logger.info(f"Retrieving details for retailer ID: {retailer_id}.")
        try:
            retailer_data = self.db_connector.fetch_retailer_by_id(retailer_id)
            if retailer_data:
                logger.debug(f"Retailer {retailer_id} found.")
                # Retourner potentiellement un sous-ensemble ou un format spécifique
                return retailer_data
            else:
                logger.warning(f"Retailer with ID {retailer_id} not found.")
                return None
        except Exception as e:
            logger.error(f"Error fetching retailer {retailer_id} details: {e}", exc_info=True)
            return None

    def set_user_preferred_retailers(self, user_id: str, retailer_ids: List[str]) -> bool:
        """
        Définit la liste des enseignes préférées pour un utilisateur donné.
        Cette fonction devrait valider les retailer_ids avant de les sauvegarder.

        Args:
            user_id (str): L'identifiant unique de l'utilisateur.
            retailer_ids (List[str]): Une liste des identifiants des enseignes sélectionnées.

        Returns:
            bool: True si la sauvegarde a réussi, False sinon.
        """
        logger.info(f"Attempting to set preferred retailers for user {user_id}: {retailer_ids}.")
        
        # 1. Validation des IDs d'enseignes
        valid_retailer_ids = []
        # get_all_available_retailers filtre déjà les non-actifs si active_only=True
        all_available_retailers = self.get_all_available_retailers(active_only=True)
        available_retailer_ids = {r['id'] for r in all_available_retailers if 'id' in r}

        for r_id in retailer_ids:
            if r_id in available_retailer_ids:
                valid_retailer_ids.append(r_id)
            else:
                logger.warning(f"Invalid or inactive retailer ID '{r_id}' provided for user {user_id}. Skipping.")

        if not valid_retailer_ids:
            logger.warning(f"No valid retailers provided for user {user_id}. Preferences not saved.")
            return False

        # 2. Sauvegarde des préférences
        try:
            success = self.db_connector.save_user_preferred_retailers(user_id, valid_retailer_ids)
            if success:
                logger.info(f"Successfully set {len(valid_retailer_ids)} preferred retailers for user {user_id}.")
            else:
                logger.error(f"Failed to save preferred retailers for user {user_id}.")
            return success
        except Exception as e:
            logger.error(f"Error saving user {user_id} preferred retailers: {e}", exc_info=True)
            return False

    def get_user_preferred_retailers(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Récupère la liste des enseignes préférées par un utilisateur, avec leurs détails.

        Args:
            user_id (str): L'identifiant unique de l'utilisateur.

        Returns:
            List[Dict[str, Any]]: Une liste de dictionnaires, chaque dictionnaire représentant une enseigne
                                  préférée avec des informations clés. Retourne une liste vide si aucune préférence.
        """
        logger.info(f"Retrieving preferred retailers for user {user_id}.")
        try:
            preferred_ids = self.db_connector.fetch_user_preferred_retailers(user_id)
            preferred_retailers_details = []
            for r_id in preferred_ids:
                retailer_details = self.get_retailer_details_by_id(r_id)
                if retailer_details:
                    # On peut choisir de retourner uniquement certains champs ici aussi
                    preferred_retailers_details.append({
                        "id": retailer_details.get('id'),
                        "name": retailer_details.get('name'),
                        "logo_url": retailer_details.get('logo_url'),
                        # ... autres champs pertinents
                    })
                else:
                    logger.warning(f"Preferred retailer ID '{r_id}' for user {user_id} not found or inactive. Skipping.")
            logger.info(f"Found {len(preferred_retailers_details)} preferred retailers for user {user_id}.")
            return preferred_retailers_details
        except Exception as e:
            logger.error(f"Error retrieving user {user_id} preferred retailers: {e}", exc_info=True)
            return []