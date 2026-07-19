from typing import List, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel

# 3.1. Modèle de Données (Pydantic Model)
class Enseigne(BaseModel):
    """
    Représente la structure des données d'une enseigne.
    """
    id: str
    nom: str
    description: Optional[str]
    logo_url: Optional[str]
    active: bool

# 3.2. Interface de Dépôt (Abstract Base Class)
class IEnseigneRepository(ABC):
    """
    Définit le contrat pour l'accès aux données des enseignes.
    """
    @abstractmethod
    def get_all_enseignes(self) -> List[Enseigne]:
        """
        Récupère toutes les enseignes disponibles.
        """
        pass

    @abstractmethod
    def get_enseigne_by_id(self, enseigne_id: str) -> Optional[Enseigne]:
        """
        Récupère une enseigne spécifique par son identifiant.
        """
        pass

    @abstractmethod
    def get_enseignes_by_ids(self, enseigne_ids: List[str]) -> List[Enseigne]:
        """
        Récupère plusieurs enseignes par une liste d'identifiants.
        """
        pass

# 3.3. Implémentation du Dépôt (Exemple - pour les tests ou une source simple)
class InMemoryEnseigneRepository(IEnseigneRepository):
    """
    Une implémentation concrète simple pour le développement ou les tests,
    utilisant une liste en mémoire comme source de données.
    """
    def __init__(self, initial_enseignes: Optional[List[Enseigne]] = None):
        self._enseignes: List[Enseigne] = initial_enseignes if initial_enseignes is not None else []

    def get_all_enseignes(self) -> List[Enseigne]:
        """
        Retourne la liste des enseignes stockées en mémoire.
        """
        return list(self._enseignes)

    def get_enseigne_by_id(self, enseigne_id: str) -> Optional[Enseigne]:
        """
        Recherche et retourne l'enseigne correspondante dans la liste en mémoire.
        """
        for enseigne in self._enseignes:
            if enseigne.id == enseigne_id:
                return enseigne
        return None

    def get_enseignes_by_ids(self, enseigne_ids: List[str]) -> List[Enseigne]:
        """
        Filtre les enseignes en mémoire par les IDs fournis.
        """
        found_enseignes = []
        # Using a set for faster lookup of requested IDs if enseigne_ids is large
        requested_ids_set = set(enseigne_ids)
        for enseigne in self._enseignes:
            if enseigne.id in requested_ids_set:
                found_enseignes.append(enseigne)
        return found_enseignes

# 3.4. Service Métier
class EnseigneSelectionService:
    """
    Contient la logique métier pour la sélection des enseignes.
    """
    def __init__(self, repository: IEnseigneRepository):
        self._repository: IEnseigneRepository = repository

    def list_available_enseignes(self) -> List[Enseigne]:
        """
        Récupère et retourne toutes les enseignes actives et disponibles pour la sélection.
        """
        all_enseignes = self._repository.get_all_enseignes()
        return [enseigne for enseigne in all_enseignes if enseigne.active]

    def validate_and_get_selected_enseignes(self, selected_enseigne_ids: List[str]) -> List[Enseigne]:
        """
        Valide une liste d'identifiants d'enseignes sélectionnés par l'utilisateur.
        """
        if not selected_enseigne_ids:
            return []

        # Retrieve all enseignes that match the provided IDs, regardless of their active status initially
        found_enseignes_list = self._repository.get_enseignes_by_ids(selected_enseigne_ids)
        found_enseignes_map = {e.id: e for e in found_enseignes_list}

        not_found_ids = []
        inactive_ids = []
        valid_selected_enseignes = []

        # Iterate through the user's selected IDs to maintain order and check validity
        for enseigne_id in selected_enseigne_ids:
            enseigne = found_enseignes_map.get(enseigne_id)
            if enseigne is None:
                not_found_ids.append(enseigne_id)
            elif not enseigne.active:
                inactive_ids.append(enseigne_id)
            else:
                valid_selected_enseignes.append(enseigne)

        error_messages = []
        if not_found_ids:
            error_messages.append(f"Les enseignes avec les IDs suivants n'existent pas ou sont introuvables : {', '.join(sorted(set(not_found_ids)))}")
        if inactive_ids:
            error_messages.append(f"Les enseignes avec les IDs suivants ne sont pas actives : {', '.join(sorted(set(inactive_ids)))}")

        if error_messages:
            raise ValueError("\n".join(error_messages))

        return valid_selected_enseignes