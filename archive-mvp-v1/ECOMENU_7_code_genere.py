import json
import uuid
import datetime
from typing import List, Dict, Optional, Any

# --- Configuration ---
CONFIG_FILE_PATH = "lunchbox_configurations.json"

# --- Internal Utility Functions ---

def _load_configurations(file_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Loads all Lunch Box configurations from a JSON file.
    Returns an empty dictionary if the file does not exist or is empty/invalid.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                # Log or print a warning if the file content is not a dictionary
                # For a standalone script, a simple print is acceptable.
                print(f"Warning: Configuration file {file_path} contains invalid data (not a dictionary). Returning empty dict.")
                return {}
            return data
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        # Log or print a warning if the file is empty or contains malformed JSON.
        print(f"Warning: Configuration file {file_path} is empty or contains invalid JSON. Returning empty dict.")
        return {}
    except Exception as e:
        # Catch any other unexpected errors during file loading.
        print(f"Error loading configurations from {file_path}: {e}")
        return {}

def _save_configurations(file_path: str, configurations: Dict[str, Dict[str, Any]]) -> None:
    """
    Saves all Lunch Box configurations to a JSON file.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(configurations, f, indent=4, ensure_ascii=False)
    except IOError as e:
        raise IOError(f"Failed to save configurations to {file_path}: {e}")

# --- Validation Function ---

def validate_lunchbox_config_data(config_data: Dict[str, Any]) -> bool:
    """
    Validates the structure and consistency of Lunch Box configuration data.
    """
    if not isinstance(config_data, dict):
        return False

    # Validate mandatory fields: 'name' and 'components'
    if "name" not in config_data or not isinstance(config_data["name"], str) or not config_data["name"].strip():
        return False
    
    if "components" not in config_data or not isinstance(config_data["components"], list):
        return False
    
    if not config_data["components"]: # Components list must not be empty
        return False

    # Validate each component within the 'components' list
    for component in config_data["components"]:
        if not isinstance(component, dict):
            return False
        if "type" not in component or not isinstance(component["type"], str) or not component["type"].strip():
            return False
        if "item_id" not in component or not isinstance(component["item_id"], str) or not component["item_id"].strip():
            return False
        if "quantity" not in component or not isinstance(component["quantity"], int) or component["quantity"] <= 0:
            return False

    # Validate optional fields if they are present
    if "description" in config_data and not isinstance(config_data["description"], str):
        return False

    if "dietary_tags" in config_data:
        if not isinstance(config_data["dietary_tags"], list):
            return False
        for tag in config_data["dietary_tags"]:
            if not isinstance(tag, str):
                return False
    
    if "is_active" in config_data and not isinstance(config_data["is_active"], bool):
        return False

    return True

# --- CRUD Operations ---

def create_lunchbox_configuration(config_data: Dict[str, Any]) -> str:
    """
    Creates a new Lunch Box configuration and saves it.
    """
    # Validate the incoming data before processing
    if not validate_lunchbox_config_data(config_data):
        raise ValueError("Invalid Lunch Box configuration data provided.")

    configurations = _load_configurations(CONFIG_FILE_PATH)

    new_config_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()

    # Construct the new configuration dictionary, including defaults for optional fields
    new_config = {
        "id": new_config_id,
        "name": config_data["name"],
        "description": config_data.get("description", ""),
        "components": config_data["components"],
        "dietary_tags": config_data.get("dietary_tags", []),
        "is_active": config_data.get("is_active", True), # Default to True if not provided
        "created_at": now,
        "updated_at": now
    }

    configurations[new_config_id] = new_config
    _save_configurations(CONFIG_FILE_PATH, configurations)
    return new_config_id

def get_lunchbox_configuration(config_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a Lunch Box configuration by its identifier.
    """
    configurations = _load_configurations(CONFIG_FILE_PATH)
    return configurations.get(config_id)

def update_lunchbox_configuration(config_id: str, new_data: Dict[str, Any]) -> bool:
    """
    Updates an existing Lunch Box configuration.
    """
    configurations = _load_configurations(CONFIG_FILE_PATH)
    
    if config_id not in configurations:
        return False

    existing_config = configurations[config_id]
    updated_config = existing_config.copy() # Work on a copy to apply changes

    # Apply updates from new_data, excluding internal fields like 'id' and 'created_at'
    for key, value in new_data.items():
        if key not in ["id", "created_at"]:
            updated_config[key] = value

    # Validate the configuration *after* applying the updates
    if not validate_lunchbox_config_data(updated_config):
        raise ValueError("Invalid Lunch Box configuration data after update. Validation failed.")
    
    updated_config["updated_at"] = datetime.datetime.now().isoformat()
    configurations[config_id] = updated_config
    _save_configurations(CONFIG_FILE_PATH, configurations)
    return True

def delete_lunchbox_configuration(config_id: str) -> bool:
    """
    Deletes a Lunch Box configuration.
    """
    configurations = _load_configurations(CONFIG_FILE_PATH)
    
    if config_id in configurations:
        del configurations[config_id]
        _save_configurations(CONFIG_FILE_PATH, configurations)
        return True
    return False

def list_all_configurations(active_only: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves all available Lunch Box configurations, optionally filtered by active status.
    """
    configurations = _load_configurations(CONFIG_FILE_PATH)
    
    config_list = list(configurations.values())
    
    if active_only:
        # Filter for configurations where 'is_active' is explicitly True.
        # If 'is_active' field is missing, it defaults to False for filtering purposes.
        return [config for config in config_list if config.get("is_active", False)]
    return config_list