import sqlite3
import json
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError

# Modèle de base pour un profil de foyer
class FoyerProfileBase(BaseModel):
    name: str = Field(..., min_length=1, description="Nom du foyer (ex: Famille Dupont)")
    member_count: int = Field(..., gt=0, description="Nombre de membres du foyer")
    dietary_preferences: List[str] = Field(default_factory=list, description="Liste des préférences alimentaires (ex: ['végétarien', 'sans gluten'])")
    energy_consumption_habit: str = Field(..., description="Habitude de consommation énergétique (ex: 'faible', 'modéré', 'élevé')")
    address: Optional[str] = Field(None, description="Adresse du foyer (optionnel)")
    user_id: int = Field(..., description="ID de l'utilisateur propriétaire du foyer")

# Modèle pour la création d'un profil (ID est généré par la BDD)
class FoyerProfileCreate(FoyerProfileBase):
    pass

# Modèle pour la lecture/réponse d'un profil (inclut l'ID généré)
class FoyerProfile(FoyerProfileBase):
    id: int = Field(..., description="ID unique du profil de foyer")

    class Config:
        from_attributes = True # Permet de créer un modèle à partir d'un objet ORM ou d'un dict

# Modèle pour la mise à jour partielle d'un profil (tous les champs sont optionnels)
class FoyerProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Nom du foyer (ex: Famille Dupont)")
    member_count: Optional[int] = Field(None, gt=0, description="Nombre de membres du foyer")
    dietary_preferences: Optional[List[str]] = Field(None, description="Liste des préférences alimentaires (ex: ['végétarien', 'sans gluten'])")
    energy_consumption_habit: Optional[str] = Field(None, description="Habitude de consommation énergétique (ex: 'faible', 'modéré', 'élevé')")
    address: Optional[str] = Field(None, description="Adresse du foyer (optionnel)")
    # user_id ne devrait pas être modifiable via update_foyer_profile

# --- Database Configuration ---
DATABASE_NAME = "foyer_profiles.db"

# --- Fonctions utilitaires de la base de données ---

def _get_db_connection() -> sqlite3.Connection:
    """
    Établit et retourne une connexion à la base de données SQLite.
    Gère les erreurs de connexion.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row # Permet d'accéder aux colonnes par leur nom
        return conn
    except sqlite3.Error as e:
        print("Erreur de connexion à la base de données:", e)
        raise

def initialize_database(db_connection: Optional[sqlite3.Connection] = None) -> None:
    """
    Initialise la structure de la base de données pour les profils de foyer.
    Crée la table 'foyer_profiles' si elle n'existe pas.
    """
    conn = db_connection if db_connection else _get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS foyer_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                member_count INTEGER NOT NULL,
                dietary_preferences TEXT DEFAULT '[]',
                energy_consumption_habit TEXT NOT NULL,
                address TEXT,
                user_id INTEGER NOT NULL
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print("Erreur lors de l'initialisation de la base de données:", e)
        raise
    finally:
        if not db_connection: # Close connection if it was opened by this function
            conn.close()

def _row_to_foyer_profile(row: sqlite3.Row) -> FoyerProfile:
    """Convert a sqlite3.Row object to a FoyerProfile Pydantic model."""
    data = dict(row)
    # Convert JSON string back to list for dietary_preferences
    if 'dietary_preferences' in data and data['dietary_preferences']:
        data['dietary_preferences'] = json.loads(data['dietary_preferences'])
    else:
        data['dietary_preferences'] = [] # Ensure it's a list even if DB value is NULL or empty string
    return FoyerProfile(**data)

# --- Fonctions CRUD pour les profils de foyer ---

def create_foyer_profile(profile_data: FoyerProfileCreate) -> FoyerProfile:
    """
    Crée un nouveau profil de foyer dans la base de données.
    Args:
        profile_data: Objet FoyerProfileCreate contenant les données du nouveau profil.
    Returns:
        L'objet FoyerProfile créé avec son ID.
    Raises:
        ValueError: Si une contrainte de données est violée (ex: user_id inexistant).
        sqlite3.Error: Pour les erreurs de base de données.
    """
    conn = _get_db_connection()
    try:
        cursor = conn.cursor()
        dietary_preferences_json = json.dumps(profile_data.dietary_preferences)
        cursor.execute("""
            INSERT INTO foyer_profiles (name, member_count, dietary_preferences, energy_consumption_habit, address, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            profile_data.name,
            profile_data.member_count,
            dietary_preferences_json,
            profile_data.energy_consumption_habit,
            profile_data.address,
            profile_data.user_id
        ))
        conn.commit()
        profile_id = cursor.lastrowid
        if profile_id is None:
            raise sqlite3.Error("Failed to retrieve last inserted row ID.")
        
        # Fetch the newly created profile to ensure all data is correctly represented
        created_profile = get_foyer_profile(profile_id)
        if created_profile is None:
            raise sqlite3.Error("Failed to retrieve the newly created profile.")
        return created_profile
    except ValidationError as e:
        raise ValueError("Données de profil invalides: {}".format(e))
    except sqlite3.IntegrityError as e:
        raise ValueError("Violation de contrainte de données: {}".format(e))
    except sqlite3.Error as e:
        print("Erreur lors de la création du profil de foyer:", e)
        raise
    finally:
        conn.close()

def get_foyer_profile(profile_id: int) -> Optional[FoyerProfile]:
    """
    Récupère un profil de foyer par son ID.
    Args:
        profile_id: L'ID unique du profil de foyer.
    Returns:
        L'objet FoyerProfile correspondant, ou None si non trouvé.
    Raises:
        sqlite3.Error: Pour les erreurs de base de données.
    """
    conn = _get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM foyer_profiles WHERE id = ?", (profile_id,))
        row = cursor.fetchone()
        if row:
            return _row_to_foyer_profile(row)
        return None
    except sqlite3.Error as e:
        print("Erreur lors de la récupération du profil de foyer:", e)
        raise
    finally:
        conn.close()

def get_foyer_profiles_by_user(user_id: int) -> List[FoyerProfile]:
    """
    Récupère tous les profils de foyer associés à un utilisateur spécifique.
    Args:
        user_id: L'ID de l'utilisateur.
    Returns:
        Une liste d'objets FoyerProfile.
    Raises:
        sqlite3.Error: Pour les erreurs de base de données.
    """
    conn = _get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM foyer_profiles WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        return [_row_to_foyer_profile(row) for row in rows]
    except sqlite3.Error as e:
        print("Erreur lors de la récupération des profils de foyer par utilisateur:", e)
        raise
    finally:
        conn.close()

def update_foyer_profile(profile_id: int, profile_data: FoyerProfileUpdate) -> Optional[FoyerProfile]:
    """
    Met à jour un profil de foyer existant par son ID.
    Les champs non spécifiés dans profile_data ne seront pas modifiés.
    Args:
        profile_id: L'ID unique du profil de foyer à mettre à jour.
        profile_data: Objet FoyerProfileUpdate contenant les champs à modifier.
    Returns:
        L'objet FoyerProfile mis à jour, ou None si le profil n'existe pas.
    Raises:
        ValueError: Si les données de mise à jour sont invalides.
        sqlite3.Error: Pour les erreurs de base de données.
    """
    conn = _get_db_connection()
    try:
        # First, retrieve the existing profile to ensure it exists
        existing_profile = get_foyer_profile(profile_id)
        if existing_profile is None:
            return None # Profile not found

        # Build the update query dynamically based on provided fields in profile_data
        set_clauses = []
        values = []

        if profile_data.name is not None:
            set_clauses.append("name = ?")
            values.append(profile_data.name)
        if profile_data.member_count is not None:
            set_clauses.append("member_count = ?")
            values.append(profile_data.member_count)
        if profile_data.dietary_preferences is not None:
            set_clauses.append("dietary_preferences = ?")
            values.append(json.dumps(profile_data.dietary_preferences))
        if profile_data.energy_consumption_habit is not None:
            set_clauses.append("energy_consumption_habit = ?")
            values.append(profile_data.energy_consumption_habit)
        if profile_data.address is not None:
            set_clauses.append("address = ?")
            values.append(profile_data.address)
        
        if not set_clauses:
            # No fields to update, return the existing profile without modification
            return existing_profile

        values.append(profile_id) # Add the ID for the WHERE clause

        query = "UPDATE foyer_profiles SET {} WHERE id = ?".format(", ".join(set_clauses))
        
        cursor = conn.cursor()
        cursor.execute(query, tuple(values))
        conn.commit()

        if cursor.rowcount == 0:
            # This case should ideally not be reached if existing_profile was found
            return None 

        # Fetch and return the updated profile
        updated_profile = get_foyer_profile(profile_id)
        return updated_profile
    except ValidationError as e:
        raise ValueError("Données de mise à jour de profil invalides: {}".format(e))
    except sqlite3.IntegrityError as e:
        raise ValueError("Violation de contrainte de données lors de la mise à jour: {}".format(e))
    except sqlite3.Error as e:
        print("Erreur lors de la mise à jour du profil de foyer:", e)
        raise
    finally:
        conn.close()

def delete_foyer_profile(profile_id: int) -> bool:
    """
    Supprime un profil de foyer par son ID.
    Args:
        profile_id: L'ID unique du profil de foyer à supprimer.
    Returns:
        True si le profil a été supprimé avec succès, False sinon.
    Raises:
        sqlite3.Error: Pour les erreurs de base de données.
    """
    conn = _get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM foyer_profiles WHERE id = ?", (profile_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print("Erreur lors de la suppression du profil de foyer:", e)
        raise
    finally:
        conn.close()