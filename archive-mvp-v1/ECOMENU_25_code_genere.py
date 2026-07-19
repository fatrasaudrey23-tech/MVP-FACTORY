import json
from typing import Dict, List, Optional, Union, Any

class MockDBConnector:
    """
    Connecteur de base de données simulé pour des fins de démonstration.
    Stocke les profils en mémoire.
    """
    def __init__(self):
        self._profiles: Dict[str, Dict[str, Any]] = {}

    def insert_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insère un nouveau profil.
        Lève une ValueError si le user_id existe déjà.
        """
        if user_id in self._profiles:
            raise ValueError(f"Profile for user_id {user_id} already exists.")
        self._profiles[user_id] = profile_data.copy()
        return self._profiles[user_id]

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un profil par user_id.
        Retourne None si non trouvé.
        """
        return self._profiles.get(user_id)

    def update_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Met à jour un profil existant.
        Retourne None si le user_id n'existe pas.
        """
        if user_id not in self._profiles:
            return None
        self._profiles[user_id].update(profile_data)
        return self._profiles[user_id]

    def delete_profile(self, user_id: str) -> bool:
        """
        Supprime un profil.
        Retourne True si supprimé, False sinon.
        """
        if user_id in self._profiles:
            del self._profiles[user_id]
            return True
        return False


class HouseholdProfileService:
    """
    Service de gestion des profils de foyer.
    Gère la création, la lecture et la mise à jour des données de profil.
    """

    def __init__(self, db_connector: Any):
        """
        Initialise le service avec un connecteur de base de données.
        Le db_connector doit fournir les méthodes nécessaires pour la persistance
        (ex: insert_profile, get_profile, update_profile).
        """
        self.db_connector = db_connector

    def _validate_profile_data(self, data: Dict[str, Any], is_creation: bool = False) -> None:
        """
        Valide les données d'un profil de foyer.
        Lève une exception ValueError si les données sont invalides.
        """
        if is_creation:
            required_fields = ['number_of_people', 'budget'] # dietary_regimes has a default
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: '{field}' for creation.")

        if 'number_of_people' in data:
            num_people = data['number_of_people']
            if not isinstance(num_people, int) or num_people <= 0:
                raise ValueError("number_of_people must be a positive integer.")

        if 'budget' in data:
            budget_val = data['budget']
            if not isinstance(budget_val, (float, int)) or budget_val <= 0:
                raise ValueError("budget must be a positive number (float or integer).")

        if 'dietary_regimes' in data:
            regimes = data['dietary_regimes']
            if not isinstance(regimes, list):
                raise ValueError("dietary_regimes must be a list.")
            for regime in regimes:
                if not isinstance(regime, str):
                    raise ValueError("Each item in dietary_regimes must be a string.")

    def _serialize_regimes(self, regimes: List[str]) -> str:
        """
        Convertit une liste de régimes en une chaîne JSON pour le stockage en base de données.
        """
        return json.dumps(regimes)

    def _deserialize_regimes(self, regimes_str: str) -> List[str]:
        """
        Convertit une chaîne JSON de régimes en une liste de chaînes de caractères.
        Gère les chaînes vides ou invalides en retournant une liste vide ou en levant une erreur.
        """
        if not regimes_str:
            return []
        try:
            deserialized = json.loads(regimes_str)
            if not isinstance(deserialized, list):
                raise ValueError("Deserialized regimes must be a list.")
            for item in deserialized:
                if not isinstance(item, str):
                    raise ValueError("Each item in deserialized dietary_regimes must be a string.")
            return deserialized
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON string for dietary_regimes.")

    def create_household_profile(
        self,
        user_id: str,
        number_of_people: int,
        budget: Union[float, int],
        dietary_regimes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Crée un nouveau profil de foyer pour un utilisateur donné.
        Retourne le profil créé.
        """
        if dietary_regimes is None:
            dietary_regimes = []

        profile_data_for_validation = {
            'number_of_people': number_of_people,
            'budget': budget,
            'dietary_regimes': dietary_regimes
        }

        self._validate_profile_data(profile_data_for_validation, is_creation=True)

        serialized_regimes = self._serialize_regimes(dietary_regimes)
        
        db_profile_data = {
            'number_of_people': number_of_people,
            'budget': budget,
            'dietary_regimes': serialized_regimes
        }

        created_db_profile = self.db_connector.insert_profile(user_id, db_profile_data)
        
        return {
            'user_id': user_id,
            'number_of_people': created_db_profile['number_of_people'],
            'budget': created_db_profile['budget'],
            'dietary_regimes': self._deserialize_regimes(created_db_profile['dietary_regimes'])
        }

    def get_household_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le profil de foyer d'un utilisateur donné.
        Retourne le profil sous forme de dictionnaire ou None si non trouvé.
        """
        db_profile = self.db_connector.get_profile(user_id)
        if db_profile is None:
            return None
        
        return {
            'user_id': user_id,
            'number_of_people': db_profile['number_of_people'],
            'budget': db_profile['budget'],
            'dietary_regimes': self._deserialize_regimes(db_profile['dietary_regimes'])
        }

    def update_household_profile(
        self,
        user_id: str,
        number_of_people: Optional[int] = None,
        budget: Optional[Union[float, int]] = None,
        dietary_regimes: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Met à jour les informations d'un profil de foyer existant.
        Retourne le profil mis à jour ou None si le profil n'existe pas.
        Les champs non fournis ne seront pas modifiés.
        """
        existing_profile = self.get_household_profile(user_id)
        if existing_profile is None:
            return None
        
        updated_data_for_validation: Dict[str, Any] = {}
        db_update_data: Dict[str, Any] = {}

        if number_of_people is not None:
            updated_data_for_validation['number_of_people'] = number_of_people
            db_update_data['number_of_people'] = number_of_people
        if budget is not None:
            updated_data_for_validation['budget'] = budget
            db_update_data['budget'] = budget
        if dietary_regimes is not None:
            updated_data_for_validation['dietary_regimes'] = dietary_regimes
            db_update_data['dietary_regimes'] = self._serialize_regimes(dietary_regimes)

        if not updated_data_for_validation:
            return existing_profile # No changes requested, return current profile

        self._validate_profile_data(updated_data_for_validation, is_creation=False)

        updated_db_profile = self.db_connector.update_profile(user_id, db_update_data)

        if updated_db_profile is None:
            return None # Should not happen if existence was checked

        return {
            'user_id': user_id,
            'number_of_people': updated_db_profile['number_of_people'],
            'budget': updated_db_profile['budget'],
            'dietary_regimes': self._deserialize_regimes(updated_db_profile['dietary_regimes'])
        }