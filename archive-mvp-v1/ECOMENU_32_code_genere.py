import os
import json
import datetime
import logging
import sys
from typing import Dict, List, Any, Optional, Union

import requests
from supabase import create_client, Client
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def load_environment_variables() -> Dict[str, str]:
    """
    Charge les variables d'environnement nécessaires au fonctionnement du script.
    """
    load_dotenv()
    env_vars = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
        "PROMOTIONS_API_URL": os.getenv("PROMOTIONS_API_URL"),
        "PROMOTIONS_API_KEY": os.getenv("PROMOTIONS_API_KEY"),
        "SUPABASE_PROMOTIONS_TABLE": os.getenv("SUPABASE_PROMOTIONS_TABLE"),
    }

    for key, value in env_vars.items():
        if value is None:
            logging.error(f"Missing environment variable: {key}")
            raise ValueError(f"Environment variable {key} is not set.")
    
    logging.info("Environment variables loaded successfully.")
    return env_vars

def initialize_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    """
    Initialise et retourne un client Supabase configuré.
    """
    try:
        client: Client = create_client(supabase_url, supabase_key)
        logging.info("Supabase client initialized successfully.")
        return client
    except Exception as e:
        logging.error(f"Failed to initialize Supabase client: {e}")
        raise

def fetch_promotions_from_source(api_url: str, api_key: Optional[str]) -> List[Dict[str, Any]]:
    """
    Récupère la liste des promotions depuis l'API externe source, gérant la pagination.
    """
    all_promotions: List[Dict[str, Any]] = []
    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        # Assuming the API key is passed as a Bearer token. Adjust if different.

    current_page_url = api_url
    page_number = 1
    
    while current_page_url:
        logging.info(f"Fetching promotions from: {current_page_url} (Page {page_number})")
        try:
            response = requests.get(current_page_url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()

            # Assuming the API returns a list of promotions directly
            # or a dictionary with a 'data' key containing the list.
            if isinstance(data, list):
                promotions_on_page = data
            elif isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                promotions_on_page = data['data']
            else:
                logging.warning(f"Unexpected API response format: {data}. Attempting to parse as list.")
                promotions_on_page = data # Try to treat it as a list anyway, might fail later.

            all_promotions.extend(promotions_on_page)
            logging.info(f"Fetched {len(promotions_on_page)} promotions from page {page_number}.")

            # Pagination logic: Assuming 'next' field in response or 'page' query param
            # This is a generic example, adapt to the actual API's pagination scheme.
            if isinstance(data, dict) and 'next_page' in data and data['next_page']:
                current_page_url = data['next_page']
                page_number += 1
            elif isinstance(data, dict) and 'links' in data and 'next' in data['links'] and data['links']['next']:
                current_page_url = data['links']['next']
                page_number += 1
            else:
                current_page_url = None # No more pages
                logging.info("No more pages found or pagination link not provided.")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching promotions from API (Page {page_number}): {e}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON response from API (Page {page_number}): {e}")
            logging.error(f"Response content: {response.text}")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred while fetching promotions (Page {page_number}): {e}")
            raise

    logging.info(f"Successfully fetched a total of {len(all_promotions)} promotions from the source API.")
    return all_promotions

def _to_iso_utc(date_str: Union[str, datetime.datetime, None]) -> Optional[str]:
    """
    Converts a date string or datetime object to an ISO 8601 string in UTC,
    suitable for Supabase TIMESTAMPZ.
    Handles various ISO formats and ensures timezone awareness.
    """
    if date_str is None:
        return None
    
    dt_obj: Optional[datetime.datetime] = None
    
    # Try parsing common ISO formats
    try:
        if isinstance(date_str, datetime.datetime):
            dt_obj = date_str
        elif isinstance(date_str, str):
            # Attempt to parse as ISO 8601, handling potential missing timezone
            # datetime.fromisoformat requires a specific format, so more robust parsing is better
            # For Python 3.9, dateutil.parser.isoparse is ideal, but we cannot import it.
            # So we rely on fromisoformat for common variants and then manual handling.
            try:
                dt_obj = datetime.datetime.fromisoformat(date_str)
            except ValueError:
                # Fallback for simpler date strings without time or just date and time without 'T'
                try:
                    dt_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        dt_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError:
                        logging.warning(f"Could not parse date string '{date_str}' with known ISO formats. Returning None.")
                        return None
        else:
            logging.warning(f"Unsupported date type: {type(date_str)}. Value: {date_str}. Returning None.")
            return None

        # If parsed, ensure it's timezone-aware and in UTC
        if dt_obj:
            if dt_obj.tzinfo is None:
                # Assume UTC if no timezone info is present, or local time and convert
                # For robustness, assuming UTC if no tzinfo is provided by the source API
                dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)
            else:
                dt_obj = dt_obj.astimezone(datetime.timezone.utc)
            return dt_obj.isoformat(timespec='seconds')
        
    except Exception as e:
        logging.error(f"Error converting date '{date_str}' to ISO UTC: {e}")
        return None
    return None

def transform_promotion_data(raw_promotion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforme un dictionnaire de promotion brute de la source en un format
    compatible avec le schéma de la table `promotions` de Supabase.
    """
    transformed: Dict[str, Any] = {
        "source_id": str(raw_promotion.get("id")), # Assuming 'id' from source is unique external ID
        "name": raw_promotion.get("name"),
        "description": raw_promotion.get("description"),
        "start_date": _to_iso_utc(raw_promotion.get("start_date")),
        "end_date": _to_iso_utc(raw_promotion.get("end_date")),
        "discount_type": raw_promotion.get("discount_type"),
        "value": float(raw_promotion.get("value", 0.0)),
        "is_active": bool(raw_promotion.get("is_active", True)),
        "last_synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
    }

    # Basic validation for critical fields
    if not transformed["source_id"]:
        logging.warning(f"Skipping promotion due to missing source_id: {raw_promotion}")
        raise ValueError("Promotion has no source_id.")
    if not transformed["name"]:
        logging.warning(f"Promotion {transformed['source_id']} has no name.")
    
    return transformed

def get_existing_promotions_from_supabase(supabase_client: Client, table_name: str) -> Dict[str, str]:
    """
    Récupère les identifiants et les identifiants source des promotions déjà présentes dans Supabase.
    Retourne un dictionnaire {source_id: supabase_id}.
    """
    existing_promotions_map: Dict[str, str] = {}
    try:
        response = supabase_client.table(table_name).select("id, source_id").execute()
        if response and response.data:
            for promo in response.data:
                existing_promotions_map[str(promo["source_id"])] = str(promo["id"])
        logging.info(f"Found {len(existing_promotions_map)} existing promotions in Supabase.")
    except Exception as e:
        logging.error(f"Error fetching existing promotions from Supabase table '{table_name}': {e}")
        raise
    return existing_promotions_map

def upsert_promotions_to_supabase(
    supabase_client: Client,
    table_name: str,
    transformed_promotions: List[Dict[str, Any]],
    existing_promotions_map: Dict[str, str]
) -> Dict[str, int]:
    """
    Insère les nouvelles promotions ou met à jour les promotions existantes dans Supabase.
    Gère également la désactivation des promotions manquantes.
    """
    stats = {'inserted': 0, 'updated': 0, 'deactivated': 0, 'errors': 0}
    promotions_to_insert: List[Dict[str, Any]] = []
    promotions_to_update: List[Dict[str, Any]] = []
    
    # Track source_ids that are still active in the incoming data
    active_source_ids_in_batch = set()

    for promo in transformed_promotions:
        source_id = promo["source_id"]
        active_source_ids_in_batch.add(source_id)

        if source_id in existing_promotions_map:
            # Update existing promotion
            promo["id"] = existing_promotions_map[source_id] # Add Supabase ID for update
            promotions_to_update.append(promo)
        else:
            # Insert new promotion
            promotions_to_insert.append(promo)
    
    # Perform bulk insert
    if promotions_to_insert:
        try:
            insert_response = supabase_client.table(table_name).insert(promotions_to_insert).execute()
            stats['inserted'] = len(insert_response.data) if insert_response and insert_response.data else 0
            logging.info(f"Successfully inserted {stats['inserted']} new promotions.")
        except Exception as e:
            logging.error(f"Error during bulk insert of promotions: {e}")
            stats['errors'] += len(promotions_to_insert)

    # Perform bulk update using upsert for existing items
    # Supabase upsert works by matching a unique constraint (like source_id)
    # or primary key. We'll use source_id as the unique identifier for upsert.
    # If Supabase upsert requires 'id' for update, we've already added it.
    # If it needs 'on_conflict' with 'source_id', we can specify that.
    if promotions_to_update:
        try:
            # Supabase upsert will match on primary key 'id' if present, or on 'source_id' if specified in on_conflict
            # For simplicity, assuming 'source_id' is a unique column and upsert will use it if 'id' is not supplied,
            # but if 'id' is supplied, it will update by 'id'.
            # We already added 'id' to promotions_to_update
            update_response = supabase_client.table(table_name).upsert(promotions_to_update, on_conflict="source_id").execute()
            stats['updated'] = len(update_response.data) if update_response and update_response.data else 0
            logging.info(f"Successfully updated {stats['updated']} existing promotions.")
        except Exception as e:
            logging.error(f"Error during bulk update of promotions: {e}")
            stats['errors'] += len(promotions_to_update)

    # Deactivate missing promotions
    promotions_to_deactivate_ids: List[str] = []
    for source_id, supabase_id in existing_promotions_map.items():
        if source_id not in active_source_ids_in_batch:
            promotions_to_deactivate_ids.append(supabase_id)
    
    if promotions_to_deactivate_ids:
        try:
            # Supabase doesn't have a direct "update where id in (...)" for a list of IDs.
            # We would typically need to loop or use a more complex query if the list is huge.
            # For a reasonable number, iterating is fine. For very large numbers, consider batches.
            deactivated_count = 0
            for promo_id in promotions_to_deactivate_ids:
                deactivate_response = supabase_client.table(table_name).update({"is_active": False, "last_synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}).eq("id", promo_id).execute()
                if deactivate_response and deactivate_response.data:
                    deactivated_count += 1
            stats['deactivated'] = deactivated_count
            logging.info(f"Successfully deactivated {stats['deactivated']} promotions that are no longer in the source.")
        except Exception as e:
            logging.error(f"Error deactivating promotions: {e}")
            stats['errors'] += len(promotions_to_deactivate_ids)

    return stats

def main() -> None:
    """
    Fonction orchestratrice principale du script.
    """
    logging.info("Starting promotions synchronization script...")
    try:
        # 1. Load environment variables
        env_vars = load_environment_variables()
        supabase_url = env_vars["SUPABASE_URL"]
        supabase_key = env_vars["SUPABASE_KEY"]
        promotions_api_url = env_vars["PROMOTIONS_API_URL"]
        promotions_api_key = env_vars["PROMOTIONS_API_KEY"]
        supabase_promotions_table = env_vars["SUPABASE_PROMOTIONS_TABLE"]

        # 2. Initialize Supabase client
        supabase_client = initialize_supabase_client(supabase_url, supabase_key)

        # 3. Fetch promotions from source API
        raw_promotions = fetch_promotions_from_source(promotions_api_url, promotions_api_key)
        logging.info(f"Retrieved {len(raw_promotions)} raw promotions from source.")

        # 4. Transform promotion data
        transformed_promotions: List[Dict[str, Any]] = []
        for raw_promo in raw_promotions:
            try:
                transformed_promotions.append(transform_promotion_data(raw_promo))
            except ValueError as ve:
                logging.warning(f"Skipping transformation for a promotion due to data error: {ve} - Raw data: {raw_promo}")
            except Exception as e:
                logging.error(f"Error transforming promotion data: {e} - Raw data: {raw_promo}")
        logging.info(f"Successfully transformed {len(transformed_promotions)} promotions.")

        if not transformed_promotions:
            logging.warning("No promotions to process after transformation. Exiting.")
            return

        # 5. Get existing promotions from Supabase
        existing_promotions_map = get_existing_promotions_from_supabase(supabase_client, supabase_promotions_table)

        # 6. Upsert promotions to Supabase
        sync_stats = upsert_promotions_to_supabase(
            supabase_client,
            supabase_promotions_table,
            transformed_promotions,
            existing_promotions_map
        )

        # 7. Display summary
        logging.info("--- Synchronization Summary ---")
        logging.info(f"Promotions inserted: {sync_stats['inserted']}")
        logging.info(f"Promotions updated: {sync_stats['updated']}")
        logging.info(f"Promotions deactivated: {sync_stats['deactivated']}")
        logging.info(f"Errors encountered: {sync_stats['errors']}")
        logging.info("Synchronization script finished.")

    except ValueError as ve:
        logging.critical(f"Configuration error: {ve}")
        sys.exit(1)
    except requests.exceptions.RequestException as re:
        logging.critical(f"Network or API error during synchronization: {re}")
        sys.exit(1)
    except Exception as e:
        logging.critical(f"An unexpected error occurred during synchronization: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()