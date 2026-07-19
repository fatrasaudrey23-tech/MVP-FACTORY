import uuid
import datetime
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field, EmailStr

# 3.1. Modèles de Données (Concepts Pydantic `BaseModel`)

class UserProfileData(BaseModel):
    id: Optional[uuid.UUID] = None
    first_name: str
    last_name: str
    email: EmailStr
    dietary_preferences: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    household_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

class HouseholdData(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str
    address: Optional[str] = None
    shared_preferences: List[str] = Field(default_factory=list)
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

# In-memory "Data Access Layer" simulation
# Stores dictionaries representing the data, keyed by UUID
_user_profiles_db: Dict[uuid.UUID, Dict[str, Any]] = {}
_households_db: Dict[uuid.UUID, Dict[str, Any]] = {}

# Helper to convert Pydantic model to a storable dict, ensuring UUIDs are kept as UUID objects
def _to_storable_dict(model_instance: BaseModel) -> Dict[str, Any]:
    data = model_instance.dict()
    # Pydantic's .dict() might convert UUIDs to str, ensure they are UUID objects for our in-memory DB
    if 'id' in data and data['id'] is not None and not isinstance(data['id'], uuid.UUID):
        data['id'] = uuid.UUID(str(data['id']))
    if 'household_id' in data and data['household_id'] is not None and not isinstance(data['household_id'], uuid.UUID):
        data['household_id'] = uuid.UUID(str(data['household_id']))
    return data

# Helper to convert a storable dict back to Pydantic model for internal manipulation
def _to_user_profile_data(data: Dict[str, Any]) -> UserProfileData:
    return UserProfileData(**data)

def _to_household_data(data: Dict[str, Any]) -> HouseholdData:
    return HouseholdData(**data)

# 3.2. Fonctions de Gestion des Profils Utilisateurs (`UserProfile`)

def create_user_profile(profile_data: UserProfileData) -> Dict[str, Any]:
    if profile_data.id is None:
        profile_data.id = uuid.uuid4()
    
    now = datetime.datetime.utcnow()
    profile_data.created_at = now
    profile_data.updated_at = now

    user_profile_dict = _to_storable_dict(profile_data)
    _user_profiles_db[profile_data.id] = user_profile_dict
    return user_profile_dict

def get_user_profile(user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    return _user_profiles_db.get(user_id)

def update_user_profile(user_id: uuid.UUID, update_data: UserProfileData) -> Optional[Dict[str, Any]]:
    existing_profile_dict = _user_profiles_db.get(user_id)
    if not existing_profile_dict:
        return None
    
    existing_profile = _to_user_profile_data(existing_profile_dict)
    
    # Apply updates from update_data, only if the field is set in update_data
    update_dict = update_data.dict(exclude_unset=True)
    
    for key, value in update_dict.items():
        if key not in ['id', 'created_at']: # id and created_at should not be updated
            setattr(existing_profile, key, value)
    
    existing_profile.updated_at = datetime.datetime.utcnow()
    
    updated_profile_dict = _to_storable_dict(existing_profile)
    _user_profiles_db[user_id] = updated_profile_dict
    return updated_profile_dict

def delete_user_profile(user_id: uuid.UUID) -> bool:
    if user_id in _user_profiles_db:
        del _user_profiles_db[user_id]
        return True
    return False

# 3.3. Fonctions de Gestion des Foyers (`Household`)

def create_household(household_data: HouseholdData) -> Dict[str, Any]:
    if household_data.id is None:
        household_data.id = uuid.uuid4()
    
    now = datetime.datetime.utcnow()
    household_data.created_at = now
    household_data.updated_at = now

    household_dict = _to_storable_dict(household_data)
    _households_db[household_data.id] = household_dict
    return household_dict

def get_household(household_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    return _households_db.get(household_id)

def update_household(household_id: uuid.UUID, update_data: HouseholdData) -> Optional[Dict[str, Any]]:
    existing_household_dict = _households_db.get(household_id)
    if not existing_household_dict:
        return None
    
    existing_household = _to_household_data(existing_household_dict)

    update_dict = update_data.dict(exclude_unset=True)
    
    for key, value in update_dict.items():
        if key not in ['id', 'created_at']:
            setattr(existing_household, key, value)
            
    existing_household.updated_at = datetime.datetime.utcnow()
    
    updated_household_dict = _to_storable_dict(existing_household)
    _households_db[household_id] = updated_household_dict
    return updated_household_dict

def delete_household(household_id: uuid.UUID) -> bool:
    if household_id in _households_db:
        del _households_db[household_id]
        
        # Crucial Consideration: Handle users linked to this household
        # Iterate over a copy of keys to allow modification of _user_profiles_db
        for user_id in list(_user_profiles_db.keys()):
            user_profile_dict = _user_profiles_db[user_id]
            if user_profile_dict.get('household_id') == household_id:
                user_profile_dict['household_id'] = None
                user_profile_dict['updated_at'] = datetime.datetime.utcnow()
        return True
    return False

# 3.4. Fonctions de Gestion des Relations Utilisateur-Foyer

def assign_user_to_household(user_id: uuid.UUID, household_id: uuid.UUID) -> bool:
    user_profile_dict = _user_profiles_db.get(user_id)
    household_dict = _households_db.get(household_id)

    if not user_profile_dict or not household_dict:
        return False # User or household not found

    # Check if already assigned to this household
    if user_profile_dict.get('household_id') == household_id:
        return True # Already assigned, consider it a success

    user_profile_dict['household_id'] = household_id
    user_profile_dict['updated_at'] = datetime.datetime.utcnow()
    return True

def remove_user_from_household(user_id: uuid.UUID, household_id: uuid.UUID) -> bool:
    user_profile_dict = _user_profiles_db.get(user_id)
    household_dict = _households_db.get(household_id)

    if not user_profile_dict or not household_dict:
        return False # User or household not found

    # Check if user is actually a member of this household
    if user_profile_dict.get('household_id') != household_id:
        return False # User is not a member of the specified household

    user_profile_dict['household_id'] = None
    user_profile_dict['updated_at'] = datetime.datetime.utcnow()
    return True

def get_household_members(household_id: uuid.UUID) -> List[Dict[str, Any]]:
    if household_id not in _households_db:
        return [] # Household does not exist

    members: List[Dict[str, Any]] = []
    for user_profile_dict in _user_profiles_db.values():
        if user_profile_dict.get('household_id') == household_id:
            members.append(user_profile_dict)
    return members