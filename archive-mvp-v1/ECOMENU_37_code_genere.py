import dataclasses
import datetime
import json
import os
import uuid
import hashlib
from typing import Dict, List, Optional, Type

# --- Configuration ---
# Define the directory where user profiles will be stored
# Ensure this directory is created if it doesn't exist
PROFILE_STORAGE_DIR = "user_profiles"
HASH_SALT = "ecomenu_secret_salt_for_passwords" # In a real app, use a unique salt per user

# --- Helper Functions ---

def _hash_password(password: str) -> str:
    """Hashes a password using SHA256 with a fixed salt."""
    salted_password = (password + HASH_SALT).encode('utf-8')
    return hashlib.sha256(salted_password).hexdigest()

def _get_profile_storage_path(user_id: str) -> str:
    """
    Determines the full file path for a given user's profile.
    Ensures the storage directory exists.
    """
    os.makedirs(PROFILE_STORAGE_DIR, exist_ok=True)
    return os.path.join(PROFILE_STORAGE_DIR, f"{user_id}.json")

# --- Modélisation du Profil Utilisateur ---

@dataclasses.dataclass
class UserProfile:
    """
    Définit la structure des données d'un profil utilisateur.
    """
    user_id: str
    username: str
    email: str
    password_hash: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    shipping_address: Optional[Dict[str, str]] = None
    billing_address: Optional[Dict[str, str]] = None
    registration_date: datetime.datetime = dataclasses.field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    last_login: Optional[datetime.datetime] = None
    is_active: bool = True
    roles: List[str] = dataclasses.field(default_factory=lambda: ['customer'])

    def to_dict(self) -> Dict[str, str]:
        """Convertit l'objet UserProfile en un dictionnaire pour la sérialisation JSON."""
        data = dataclasses.asdict(self)
        # Convert datetime objects to ISO format strings for JSON
        if data['registration_date']:
            data['registration_date'] = data['registration_date'].isoformat()
        if data['last_login']:
            data['last_login'] = data['last_login'].isoformat()
        return data

    @classmethod
    def from_dict(cls: Type['UserProfile'], data: Dict[str, str]) -> 'UserProfile':
        """Crée un objet UserProfile à partir d'un dictionnaire (désérialisation JSON)."""
        # Convert ISO format strings back to datetime objects
        if 'registration_date' in data and data['registration_date']:
            data['registration_date'] = datetime.datetime.fromisoformat(data['registration_date'])
        if 'last_login' in data and data['last_login']:
            data['last_login'] = datetime.datetime.fromisoformat(data['last_login'])
        return cls(**data)

# --- Fonctions de Gestion de la Persistance (Stockage Fichier JSON) ---

def create_user_profile(
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    **kwargs: Dict[str, str]
) -> UserProfile:
    """
    Crée une nouvelle instance de UserProfile avec un ID unique, hache le mot de passe,
    et initialise les champs par défaut.
    """
    user_id = uuid.uuid4().hex
    password_hash = _hash_password(password)
    registration_date = datetime.datetime.now(datetime.timezone.utc)

    profile = UserProfile(
        user_id=user_id,
        username=username,
        email=email,
        password_hash=password_hash,
        first_name=first_name,
        last_name=last_name,
        registration_date=registration_date,
        # Default values are handled by dataclass, but kwargs can override/set optionals
        phone_number=kwargs.get('phone_number'),
        shipping_address=kwargs.get('shipping_address'),
        billing_address=kwargs.get('billing_address'),
        is_active=kwargs.get('is_active', True),
        roles=kwargs.get('roles', ['customer'])
    )
    return profile

def save_user_profile(profile: UserProfile) -> None:
    """
    Sauvegarde un objet UserProfile dans le système de fichiers sous forme de fichier JSON.
    """
    file_path = _get_profile_storage_path(profile.user_id)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profile.to_dict(), f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving profile {profile.user_id}: {e}")

def load_user_profile(user_id: str) -> Optional[UserProfile]:
    """
    Charge un profil utilisateur à partir de son fichier JSON.
    """
    file_path = _get_profile_storage_path(user_id)
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return UserProfile.from_dict(data)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading profile {user_id}: {e}")
        return None

def update_user_profile(user_id: str, **kwargs: Dict[str, str]) -> Optional[UserProfile]:
    """
    Met à jour un ou plusieurs attributs d'un profil utilisateur existant.
    """
    profile = load_user_profile(user_id)
    if profile is None:
        return None

    for key, value in kwargs.items():
        if key == 'password':
            # Special handling for password: hash it
            setattr(profile, 'password_hash', _hash_password(value))
        elif hasattr(profile, key):
            # Update other attributes
            setattr(profile, key, value)
        else:
            print(f"Warning: Attribute '{key}' not found in UserProfile for update.")

    # Update last_login if applicable or force it here for any update
    # For now, let's assume last_login is updated only on actual login.
    # If a field like 'last_updated' was present, it would be set here.

    save_user_profile(profile)
    return profile

def delete_user_profile(user_id: str) -> bool:
    """
    Supprime un profil utilisateur et son fichier associé.
    """
    file_path = _get_profile_storage_path(user_id)
    if not os.path.exists(file_path):
        return False
    try:
        os.remove(file_path)
        return True
    except OSError as e:
        print(f"Error deleting profile {user_id}: {e}")
        return False

def list_all_user_profiles() -> List[UserProfile]:
    """
    Récupère tous les profils utilisateurs stockés dans le répertoire.
    """
    profiles: List[UserProfile] = []
    if not os.path.exists(PROFILE_STORAGE_DIR):
        return profiles

    for filename in os.listdir(PROFILE_STORAGE_DIR):
        if filename.endswith(".json"):
            user_id = filename.replace(".json", "")
            profile = load_user_profile(user_id)
            if profile:
                profiles.append(profile)
    return profiles

# --- Exemple d'utilisation (pour la validation du script) ---
# Vous pouvez décommenter le bloc ci-dessous pour tester les fonctions.
# if __name__ == "__main__":
#     print("--- Démarrage de la démo de gestion des profils utilisateurs ---")

#     # 1. Créer un nouveau profil
#     print("\n1. Création d'un nouveau profil utilisateur...")
#     new_user = create_user_profile(
#         username="john_doe",
#         email="john.doe@example.com",
#         password="securepassword123",
#         first_name="John",
#         last_name="Doe",
#         phone_number="123-456-7890",
#         shipping_address={"street": "123 Main St", "city": "Anytown", "zip": "12345"}
#     )
#     save_user_profile(new_user)
#     print(f"Profil créé et sauvegardé pour {new_user.username} (ID: {new_user.user_id})")
#     print(f"Détails: {new_user.to_dict()}")

#     # 2. Charger un profil
#     print("\n2. Chargement du profil de John Doe...")
#     loaded_user = load_user_profile(new_user.user_id)
#     if loaded_user:
#         print(f"Profil chargé: {loaded_user.username}, Email: {loaded_user.email}")
#         print(f"Hash du mot de passe: {loaded_user.password_hash}")
#     else:
#         print("Erreur: Profil non trouvé.")

#     # 3. Mettre à jour un profil
#     print("\n3. Mise à jour du profil de John Doe (email et adresse de facturation)...")
#     updated_user = update_user_profile(
#         new_user.user_id,
#         email="john.doe.new@example.com",
#         billing_address={"street": "456 Oak Ave", "city": "Otherville", "zip": "67890"},
#         is_active=False
#     )
#     if updated_user:
#         print(f"Profil mis à jour: {updated_user.username}, Nouvel Email: {updated_user.email}, Actif: {updated_user.is_active}")
#         print(f"Nouvelle adresse de facturation: {updated_user.billing_address}")
#     else:
#         print("Erreur: Impossible de mettre à jour le profil.")

#     # 4. Créer un deuxième profil
#     print("\n4. Création d'un deuxième profil utilisateur...")
#     second_user = create_user_profile(
#         username="jane_smith",
#         email="jane.smith@example.com",
#         password="anothersecurepassword",
#         first_name="Jane",
#         last_name="Smith",
#         roles=['admin', 'customer']
#     )
#     save_user_profile(second_user)
#     print(f"Profil créé et sauvegardé pour {second_user.username} (ID: {second_user.user_id})")

#     # 5. Lister tous les profils
#     print("\n5. Liste de tous les profils utilisateurs...")
#     all_profiles = list_all_user_profiles()
#     if all_profiles:
#         for profile in all_profiles:
#             print(f"- ID: {profile.user_id}, Username: {profile.username}, Roles: {profile.roles}, Active: {profile.is_active}")
#     else:
#         print("Aucun profil trouvé.")

#     # 6. Supprimer un profil
#     print(f"\n6. Suppression du profil de John Doe (ID: {new_user.user_id})...")
#     if delete_user_profile(new_user.user_id):
#         print("Profil de John Doe supprimé avec succès.")
#     else:
#         print("Erreur: Impossible de supprimer le profil de John Doe.")

#     # 7. Vérifier que le profil est bien supprimé
#     print("\n7. Vérification de la suppression de John Doe...")
#     if load_user_profile(new_user.user_id) is None:
#         print("Le profil de John Doe n'existe plus.")
#     else:
#         print("Le profil de John Doe existe toujours (erreur de suppression).")

#     # 8. Lister à nouveau pour vérifier
#     print("\n8. Liste des profils restants...")
#     all_profiles_after_delete = list_all_user_profiles()
#     if all_profiles_after_delete:
#         for profile in all_profiles_after_delete:
#             print(f"- ID: {profile.user_id}, Username: {profile.username}")
#     else:
#         print("Aucun profil restant.")

#     print("\n--- Démo terminée ---")
#     # Nettoyage (optionnel pour les tests)
#     # for profile in all_profiles_after_delete:
#     #     delete_user_profile(profile.user_id)
#     # if os.path.exists(PROFILE_STORAGE_DIR) and not os.listdir(PROFILE_STORAGE_DIR):
#     #     os.rmdir(PROFILE_STORAGE_DIR)