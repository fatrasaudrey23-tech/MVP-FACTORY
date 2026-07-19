import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from pydantic import BaseModel, Field, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HouseholdProfileModel(BaseModel):
    id: Optional[int] = Field(None, description="Unique identifier for the household profile.")
    user_id: int = Field(..., description="User ID associated with this profile.")
    name: str = Field(..., min_length=1, max_length=100, description="Name of the household (e.g., 'Dupont Family').")
    occupants: int = Field(..., gt=0, description="Number of people in the household.")
    dietary_preferences: List[str] = Field(default_factory=list, description="List of dietary preferences (e.g., 'vegetarian', 'gluten-free').")
    allergies: List[str] = Field(default_factory=list, description="List of allergies (e.g., 'peanuts', 'lactose').")
    budget_level: str = Field(..., description="Budget level (e.g., 'low', 'medium', 'high').")
    meal_frequency: Dict[str, int] = Field(default_factory=dict, description="Desired meal frequency by type (e.g., {'dinner': 7, 'lunch': 5}).")
    created_at: Optional[datetime] = Field(None, description="Timestamp of profile creation.")
    updated_at: Optional[datetime] = Field(None, description="Timestamp of last profile update.")

    class Config:
        json_dumps = json.dumps
        json_loads = json.loads
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

class HouseholdProfileService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialize_db()
        logger.info(f"HouseholdProfileService initialized with DB: {db_path}")

    def _connect_db(self) -> sqlite3.Connection:
        """Establishes a connection to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Allows accessing columns by name
        return conn

    def _initialize_db(self):
        """Creates the household_profiles table if it doesn't exist."""
        try:
            with self._connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS household_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        occupants INTEGER NOT NULL,
                        dietary_preferences TEXT,
                        allergies TEXT,
                        budget_level TEXT NOT NULL,
                        meal_frequency TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """)
                conn.commit()
            logger.info("Database table 'household_profiles' ensured.")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def _map_row_to_profile(self, row: sqlite3.Row) -> HouseholdProfileModel:
        """Converts a database row into a HouseholdProfileModel instance."""
        if row is None:
            raise ValueError("Cannot map None row to profile model.")

        data = dict(row)
        
        # Deserialize JSON fields
        for field in ['dietary_preferences', 'allergies']:
            data[field] = json.loads(data[field]) if data[field] else []
        data['meal_frequency'] = json.loads(data['meal_frequency']) if data[field] else {}

        # Convert datetime strings to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else None
        data['updated_at'] = datetime.fromisoformat(data['updated_at']) if data['updated_at'] else None
        
        try:
            return HouseholdProfileModel(**data)
        except ValidationError as e:
            logger.error(f"Validation error mapping DB row to HouseholdProfileModel: {e} for data: {data}")
            raise

    def _map_profile_to_db_params(self, profile: HouseholdProfileModel) -> Dict[str, Any]:
        """Converts a HouseholdProfileModel instance into a dictionary of parameters suitable for DB insertion/update."""
        params = profile.dict() # Get all fields, including 'id' if set
        
        # Serialize List and Dict fields to JSON strings
        params['dietary_preferences'] = json.dumps(params.get('dietary_preferences', []))
        params['allergies'] = json.dumps(params.get('allergies', []))
        params['meal_frequency'] = json.dumps(params.get('meal_frequency', {}))
        
        # Convert datetime objects to ISO format strings
        if params.get('created_at') is not None:
            params['created_at'] = params['created_at'].isoformat()
        if params.get('updated_at') is not None:
            params['updated_at'] = params['updated_at'].isoformat()
            
        return params

    def create_profile(self, user_id: int, profile_data: HouseholdProfileModel) -> HouseholdProfileModel:
        """Creates a new household profile in the database."""
        current_time = datetime.utcnow()
        profile_data.user_id = user_id
        profile_data.created_at = current_time
        profile_data.updated_at = current_time
        profile_data.id = None # Ensure ID is not set for creation

        try:
            # Validate the profile_data before mapping and inserting
            profile_data_validated = HouseholdProfileModel(**profile_data.dict())
            db_params = self._map_profile_to_db_params(profile_data_validated)
            
            # Remove 'id' from parameters as it's AUTOINCREMENT
            if 'id' in db_params:
                del db_params['id']
            
            columns = ', '.join(db_params.keys())
            placeholders = ', '.join(['?' for _ in db_params])
            
            with self._connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    INSERT INTO household_profiles ({columns})
                    VALUES ({placeholders})
                """, list(db_params.values()))
                profile_id = cursor.lastrowid
                conn.commit()
            
            profile_data_validated.id = profile_id
            logger.info(f"Profile created successfully for user_id: {user_id}, profile_id: {profile_id}")
            return profile_data_validated
        except ValidationError as e:
            logger.error(f"Validation error for profile creation for user_id {user_id}: {e}")
            raise
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error creating profile for user_id {user_id}: {e}. User might already have a profile.")
            raise ValueError(f"Profile already exists for user ID {user_id}.")
        except sqlite3.Error as e:
            logger.error(f"Database error creating profile for user_id {user_id}: {e}")
            raise

    def get_profile(self, user_id: int) -> Optional[HouseholdProfileModel]:
        """Retrieves a household profile by user_id."""
        try:
            with self._connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM household_profiles WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
            
            if row:
                logger.info(f"Profile found for user_id: {user_id}")
                return self._map_row_to_profile(row)
            else:
                logger.info(f"No profile found for user_id: {user_id}")
                return None
        except sqlite3.Error as e:
            logger.error(f"Database error fetching profile for user_id {user_id}: {e}")
            raise
        except ValueError as e: # Catching error from _map_row_to_profile if row is None, though current logic handles it.
            logger.error(f"Error mapping profile for user_id {user_id}: {e}")
            raise

    def update_profile(self, user_id: int, profile_data: HouseholdProfileModel) -> HouseholdProfileModel:
        """Updates an existing household profile for a given user_id."""
        existing_profile = self.get_profile(user_id)
        if not existing_profile:
            logger.warning(f"Attempted to update non-existent profile for user_id: {user_id}")
            raise ValueError(f"No profile found for user ID {user_id} to update.")

        current_time = datetime.utcnow()
        
        # Create a new model instance by merging existing data with new data
        # profile_data.dict(exclude_unset=True) ensures only provided fields override existing ones
        updated_data = existing_profile.copy(update=profile_data.dict(exclude_unset=True))
        updated_data.updated_at = current_time
        updated_data.user_id = user_id # Ensure user_id remains consistent

        try:
            # Validate the merged data
            updated_data_validated = HouseholdProfileModel(**updated_data.dict())
            db_params = self._map_profile_to_db_params(updated_data_validated)
            
            # Exclude 'id', 'user_id', and 'created_at' from update parameters
            # 'id' is primary key, 'user_id' is in WHERE clause, 'created_at' should not change
            params_for_update = {k: v for k, v in db_params.items() if k not in ['id', 'user_id', 'created_at']}
            
            set_clauses = ', '.join([f"{key} = ?" for key in params_for_update.keys()])
            
            with self._connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    UPDATE household_profiles
                    SET {set_clauses}
                    WHERE user_id = ?
                """, list(params_for_update.values()) + [user_id])
                conn.commit()
                
                if cursor.rowcount == 0:
                    logger.warning(f"Update operation for user_id {user_id} affected 0 rows, profile might have been deleted concurrently.")
                    raise ValueError(f"No profile found for user ID {user_id} to update.")

            logger.info(f"Profile updated successfully for user_id: {user_id}")
            return updated_data_validated
        except ValidationError as e:
            logger.error(f"Validation error for profile update for user_id {user_id}: {e}")
            raise
        except sqlite3.Error as e:
            logger.error(f"Database error updating profile for user_id {user_id}: {e}")
            raise

    def delete_profile(self, user_id: int) -> bool:
        """Deletes a household profile from the database for a given user_id."""
        try:
            with self._connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM household_profiles WHERE user_id = ?", (user_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Profile deleted successfully for user_id: {user_id}")
                    return True
                else:
                    logger.info(f"No profile found for user_id: {user_id} to delete.")
                    return False
        except sqlite3.Error as e:
            logger.error(f"Database error deleting profile for user_id {user_id}: {e}")
            raise

if __name__ == "__main__":
    DB_PATH = "ecomenu_profiles.db"
    service = HouseholdProfileService(DB_PATH)

    user_id_1 = 101
    profile_data_1 = HouseholdProfileModel(
        name="Famille Dupont",
        occupants=4,
        dietary_preferences=["végétarien", "sans gluten"],
        allergies=["lactose"],
        budget_level="moyen",
        meal_frequency={"diner": 7, "dejeuner": 5, "petit-dejeuner": 7}
    )
    
    print("--- Creating profile for user 101 ---")
    try:
        created_profile_1 = service.create_profile(user_id_1, profile_data_1)
        print(f"Created Profile 1: {created_profile_1.json(indent=2)}")
    except (ValueError, sqlite3.Error) as e:
        print(f"Error creating profile 101: {e}")

    print("\n--- Attempting to create profile for user 101 again (should fail) ---")
    try:
        service.create_profile(user_id_1, profile_data_1)
    except (ValueError, sqlite3.Error) as e:
        print(f"Error creating profile 101 again (expected): {e}")

    print("\n--- Getting profile for user 101 ---")
    retrieved_profile_1 = service.get_profile(user_id_1)
    if retrieved_profile_1:
        print(f"Retrieved Profile 1: {retrieved_profile_1.json(indent=2)}")
    else:
        print(f"Profile for user_id {user_id_1} not found.")

    print("\n--- Updating profile for user 101 ---")
    update_data_1 = HouseholdProfileModel(
        name="Famille Dupont-Martin",
        occupants=5,
        budget_level="élevé",
        allergies=["lactose", "arachides"]
    )
    try:
        updated_profile_1 = service.update_profile(user_id_1, update_data_1)
        print(f"Updated Profile 1: {updated_profile_1.json(indent=2)}")
    except (ValueError, sqlite3.Error) as e:
        print(f"Error updating profile 101: {e}")

    print("\n--- Getting updated profile for user 101 to verify ---")
    verified_profile_1 = service.get_profile(user_id_1)
    if verified_profile_1:
        print(f"Verified Profile 1: {verified_profile_1.json(indent=2)}")

    user_id_2 = 102
    profile_data_2 = HouseholdProfileModel(
        name="Colocation étudiante",
        occupants=3,
        dietary_preferences=["vegan"],
        allergies=[],
        budget_level="faible",
        meal_frequency={"diner": 5}
    )
    print("\n--- Creating profile for user 102 ---")
    try:
        created_profile_2 = service.create_profile(user_id_2, profile_data_2)
        print(f"Created Profile 2: {created_profile_2.json(indent=2)}")
    except (ValueError, sqlite3.Error) as e:
        print(f"Error creating profile 102: {e}")

    print("\n--- Deleting profile for user 101 ---")
    try:
        deleted = service.delete_profile(user_id_1)
        print(f"Profile 101 deleted: {deleted}")
    except sqlite3.Error as e:
        print(f"Error deleting profile 101: {e}")

    print("\n--- Getting deleted profile for user 101 (should be None) ---")
    retrieved_deleted_profile_1 = service.get_profile(user_id_1)
    print(f"Retrieved deleted Profile 101: {retrieved_deleted_profile_1}")

    print("\n--- Deleting profile for user 102 ---")
    try:
        deleted = service.delete_profile(user_id_2)
        print(f"Profile 102 deleted: {deleted}")
    except sqlite3.Error as e:
        print(f"Error deleting profile 102: {e}")

    import os
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"\nCleaned up {DB_PATH}")