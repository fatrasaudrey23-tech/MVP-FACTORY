import os
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- SQLAlchemy Base ---
Base = declarative_base()

# --- Database Model ---
class Promotion(Base):
    __tablename__ = 'promotions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    promotion_type = Column(String(100), nullable=True)  # e.g., 'percentage_off', 'fixed_amount_off', 'buy_x_get_y'
    promotion_value = Column(String(100), nullable=True) # e.g., '10%', '$5', 'Buy 1 Get 1 Free'
    url_source = Column(String(500), unique=True, nullable=False) # URL where promotion was found
    extracted_at = Column(DateTime, default=datetime.now, nullable=False)
    last_updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self):
        return f"<Promotion(id={self.id}, title='{self.title}', url_source='{self.url_source}')>"

# A. Fonctions de Configuration et d'Initialisation :

def load_environment_variables() -> Dict[str, str]:
    """
    Charge les variables d'environnement essentielles depuis un fichier .env et les retourne.
    """
    load_dotenv()
    env_vars: Dict[str, str] = {}
    env_vars['DATABASE_URL'] = os.getenv('DATABASE_URL', 'sqlite:///promotions.db')
    # Example for API keys, can be extended
    env_vars['API_KEY_EXAMPLE'] = os.getenv('API_KEY_EXAMPLE') 
    logger.info("Environment variables loaded.")
    return env_vars

def get_database_engine(db_url: str):
    """
    Initialise et retourne un moteur de base de données SQLAlchemy.
    """
    try:
        engine = create_engine(db_url)
        logger.info(f"Database engine created for URL: {db_url}")
        return engine
    except SQLAlchemyError as e:
        logger.error(f"Error creating database engine: {e}")
        raise

def initialize_database_schema(engine):
    """
    Vérifie et crée la table 'promotions' si elle n'existe pas.
    """
    try:
        Base.metadata.create_all(engine)
        logger.info("Database schema initialized (table 'promotions' checked/created).")
    except SQLAlchemyError as e:
        logger.error(f"Error initializing database schema: {e}")
        raise

# B. Fonctions d'Extraction :

def _fetch_from_api(url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Effectue une requête GET vers une API et retourne la réponse JSON.
    """
    logger.info(f"Fetching data from API: {url}")
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        logger.info(f"Successfully fetched {len(data)} items from API: {url}")
        # Assuming the API returns a list of dicts directly or a dict with a 'results' key
        if isinstance(data, dict) and 'results' in data:
            return data['results']
        elif isinstance(data, list):
            return data
        else:
            logger.warning(f"API response for {url} is not a list or dict with 'results'. Returning empty list.")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from API {url}: {e}")
        return []
    except ValueError as e: # JSONDecodeError
        logger.error(f"Error decoding JSON response from API {url}: {e}")
        return []

def _scrape_webpage(url: str, selectors: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Récupère le contenu d'une page web, le parse et extrait les données de promotions.
    `selectors` doit inclure un 'container' selector pour les éléments de promotion.
    Ex: {'container': '.promotion-item', 'title': 'h2.promo-title', 'description': '.promo-desc'}
    """
    logger.info(f"Scraping data from webpage: {url}")
    promotions_data: List[Dict[str, Any]] = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        container_selector = selectors.get('container')
        if not container_selector:
            logger.error(f"Missing 'container' selector for webpage scraping: {url}")
            return []

        promotion_elements = soup.select(container_selector)
        if not promotion_elements:
            logger.warning(f"No promotion elements found with selector '{container_selector}' on {url}.")
            return []

        for element in promotion_elements:
            promo_item: Dict[str, Any] = {'url_source': url} # Add source URL by default
            for field, selector in selectors.items():
                if field == 'container': # Skip container selector
                    continue
                
                # Special handling for attribute extraction if selector ends with '::attr(attribute_name)'
                if '::attr(' in selector:
                    selector_parts = selector.split('::attr(')
                    css_selector = selector_parts[0]
                    attr_name = selector_parts[1][:-1] # Remove ')'
                    found_element = element.select_one(css_selector)
                    if found_element:
                        promo_item[field] = found_element.get(attr_name)
                    else:
                        promo_item[field] = None
                else:
                    # Attempt to find the text content, handling potential None
                    found_element = element.select_one(selector)
                    if found_element:
                        promo_item[field] = found_element.get_text(strip=True)
                    else:
                        promo_item[field] = None # Or raise error, depending on strictness
            promotions_data.append(promo_item)
        
        logger.info(f"Successfully scraped {len(promotions_data)} items from webpage: {url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error scraping webpage {url}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during scraping {url}: {e}")
    return promotions_data

def fetch_data_from_source(source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fonction générique pour orchestrer l'extraction de données à partir d'une source spécifique.
    """
    source_type = source_config.get('type')
    url = source_config.get('url')
    
    if not url:
        logger.error(f"Source configuration missing URL: {source_config}")
        return []

    if source_type == 'API':
        headers = source_config.get('headers')
        params = source_config.get('params')
        return _fetch_from_api(url, headers=headers, params=params)
    elif source_type == 'WEB_SCRAPING':
        selectors = source_config.get('selectors')
        if not selectors:
            logger.error(f"Web scraping source configuration missing selectors: {source_config}")
            return []
        return _scrape_webpage(url, selectors)
    else:
        logger.warning(f"Unknown source type: {source_type}. Skipping extraction for {url}")
        return []

# C. Fonctions de Transformation :

def standardize_promotion_schema(raw_promotion_data: Dict[str, Any], source_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Transforme un dictionnaire de données brutes en un format de schéma standardisé.
    Gère les renommages de champs, les conversions de types.
    `source_mapping` : {'raw_field_name': 'standard_field_name'}
    """
    standardized_data: Dict[str, Any] = {}
    for raw_field, standard_field in source_mapping.items():
        value = raw_promotion_data.get(raw_field)
        
        if value is None:
            standardized_data[standard_field] = None
            continue

        # Type conversions
        if standard_field in ['start_date', 'end_date', 'extracted_at', 'last_updated_at']:
            if isinstance(value, (datetime, date)):
                standardized_data[standard_field] = value
            elif isinstance(value, str):
                try:
                    # Attempt common date formats
                    if 'T' in value and '.' in value: # ISO format with milliseconds
                        standardized_data[standard_field] = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
                    elif 'T' in value: # ISO format without milliseconds
                        standardized_data[standard_field] = datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
                    else: # YYYY-MM-DD
                        standardized_data[standard_field] = datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Could not parse date '{value}' for field '{standard_field}'. Setting to None.")
                    standardized_data[standard_field] = None
            else:
                logger.warning(f"Unexpected type for date field '{standard_field}': {type(value)}. Setting to None.")
                standardized_data[standard_field] = None
        elif standard_field == 'promotion_value':
            standardized_data[standard_field] = str(value)
        else:
            standardized_data[standard_field] = value
            
    # Ensure extracted_at and last_updated_at are set if not provided by source
    if 'extracted_at' not in standardized_data or standardized_data['extracted_at'] is None:
        standardized_data['extracted_at'] = datetime.now()
    if 'last_updated_at' not in standardized_data or standardized_data['last_updated_at'] is None:
        standardized_data['last_updated_at'] = datetime.now()

    return standardized_data

def validate_promotion_data(standardized_data: Dict[str, Any]) -> bool:
    """
    Valide la conformité des données standardisées.
    """
    required_fields = ['title', 'start_date', 'url_source']
    for field in required_fields:
        if standardized_data.get(field) is None:
            logger.warning(f"Validation failed: Missing required field '{field}' for promotion: {standardized_data.get('title', 'N/A')}")
            return False

    # Date validation
    start_date = standardized_data.get('start_date')
    end_date = standardized_data.get('end_date')

    if not isinstance(start_date, datetime):
        logger.warning(f"Validation failed: 'start_date' is not a datetime object for promotion: {standardized_data.get('title', 'N/A')}")
        return False
    
    if end_date is not None and not isinstance(end_date, datetime):
        logger.warning(f"Validation failed: 'end_date' is not a datetime object (and not None) for promotion: {standardized_data.get('title', 'N/A')}")
        return False

    if end_date and start_date and end_date < start_date:
        logger.warning(f"Validation failed: 'end_date' ({end_date}) is before 'start_date' ({start_date}) for promotion: {standardized_data.get('title', 'N/A')}")
        return False
    
    # URL validation (basic check)
    url_source = standardized_data.get('url_source')
    if not isinstance(url_source, str) or not url_source.startswith(('http://', 'https://')):
        logger.warning(f"Validation failed: Invalid 'url_source' format for promotion: {standardized_data.get('title', 'N/A')}")
        return False

    return True

# D. Fonctions de Chargement :

def store_promotions_in_database(engine, promotions_data: List[Dict[str, Any]]):
    """
    Insère ou met à jour les promotions validées dans la base de données.
    Utilise une stratégie d'upsert basée sur 'url_source'.
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    inserted_count = 0
    updated_count = 0

    try:
        for promo_data in promotions_data:
            # Check if promotion already exists based on a unique identifier (e.g., url_source)
            existing_promotion = session.query(Promotion).filter_by(url_source=promo_data['url_source']).first()

            if existing_promotion:
                # Update existing promotion
                for key, value in promo_data.items():
                    setattr(existing_promotion, key, value)
                existing_promotion.last_updated_at = datetime.now()
                updated_count += 1
                logger.debug(f"Updated promotion: {existing_promotion.title}")
            else:
                # Insert new promotion
                new_promotion = Promotion(**promo_data)
                session.add(new_promotion)
                inserted_count += 1
                logger.debug(f"Inserted new promotion: {new_promotion.title}")
        
        session.commit()
        logger.info(f"Successfully loaded {inserted_count} new promotions and updated {updated_count} existing promotions into the database.")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error storing promotions in database: {e}")
    finally:
        session.close()

# E. Fonction d'Orchestration principale :

def execute_promotion_pipeline(source_configs: List[Dict[str, Any]]):
    """
    Fonction principale qui orchestre l'ensemble du pipeline.
    """
    logger.info("Starting promotion extraction pipeline.")

    try:
        env_vars = load_environment_variables()
        db_url = env_vars['DATABASE_URL']
        engine = get_database_engine(db_url)
        initialize_database_schema(engine)
    except Exception as e:
        logger.critical(f"Pipeline initialization failed: {e}")
        return

    for config in source_configs:
        source_name = config.get('name', 'Unknown Source')
        logger.info(f"Processing source: {source_name}")
        
        raw_data = fetch_data_from_source(config)
        if not raw_data:
            logger.warning(f"No data extracted from source: {source_name}. Skipping transformation and loading.")
            continue

        valid_promotions: List[Dict[str, Any]] = []
        source_mapping = config.get('mapping', {})

        for item in raw_data:
            standardized_item = standardize_promotion_schema(item, source_mapping)
            if validate_promotion_data(standardized_item):
                valid_promotions.append(standardized_item)
            else:
                logger.warning(f"Skipping invalid promotion data from {source_name}: {item.get('title', 'N/A')}")
        
        if valid_promotions:
            logger.info(f"Found {len(valid_promotions)} valid promotions from source: {source_name}. Storing in DB.")
            store_promotions_in_database(engine, valid_promotions)
        else:
            logger.warning(f"No valid promotions to store from source: {source_name}.")
    
    logger.info("Promotion extraction pipeline finished.")

# F. Point d'entrée du script :

def main():
    """
    Point d'entrée pour l'exécution du script.
    Définit les configurations des sources et appelle execute_promotion_pipeline.
    """
    # Example source configurations
    # In a real application, these would likely be loaded from a config file (YAML, JSON)
    # or a database.
    source_configs = [
        {
            'name': 'Example API Source',
            'type': 'API',
            'url': 'https://api.example.com/promotions', # Replace with a real API endpoint for testing
            'headers': {'Authorization': 'Bearer ' + os.getenv('API_KEY_EXAMPLE', 'your_default_api_key')},
            'params': {'status': 'active', 'limit': 100},
            'mapping': {
                'promo_title': 'title',
                'description_text': 'description',
                'start_date_iso': 'start_date',
                'end_date_iso': 'end_date',
                'type': 'promotion_type',
                'value': 'promotion_value',
                'source_url': 'url_source',
                'extracted_timestamp': 'extracted_at'
            }
        },
        {
            'name': 'Example Web Scraping Source',
            'type': 'WEB_SCRAPING',
            'url': 'https://www.example.com/deals', # Replace with a real webpage for testing
            'selectors': {
                'container': '.deal-card',
                'title': 'h3.deal-title',
                'description': '.deal-description',
                'start_date': '.deal-start-date', # Assumed to be in YYYY-MM-DD or similar
                'end_date': '.deal-end-date',
                'promo_type': '.deal-type',
                'promo_value': '.deal-value',
                'link': 'a.deal-link::attr(href)' # Special case for attribute extraction
            },
            'mapping': {
                'title': 'title',
                'description': 'description',
                'start_date': 'start_date',
                'end_date': 'end_date',
                'promo_type': 'promotion_type',
                'promo_value': 'promotion_value',
                'link': 'url_source' # Map 'link' from scraper to 'url_source'
            }
        }
    ]

    # Mocking API and scraping responses for demonstration purposes
    # In a real scenario, these would be actual network calls.
    # For this example, I'll provide a dummy source config to avoid real network calls
    # and focus on the pipeline logic.
    
    # --- Dummy source config to demonstrate pipeline flow without external network calls ---
    # To make the script runnable without actual external dependencies beyond basic packages
    # and to simulate data for the pipeline's core logic.
    dummy_api_response_data = [
        {
            "promo_title": "Summer Sale 2023",
            "description_text": "Up to 50% off on selected items!",
            "start_date_iso": "2023-07-01T00:00:00.000Z",
            "end_date_iso": "2023-07-31T23:59:59.000Z",
            "type": "percentage_off",
            "value": "50%",
            "source_url": "https://www.example.com/api/promos/summer-sale",
            "extracted_timestamp": "2023-06-25T10:00:00.000Z"
        },
        {
            "promo_title": "Buy One Get One Free",
            "description_text": "On all coffee products this week.",
            "start_date_iso": "2023-07-10",
            "end_date_iso": "2023-07-16",
            "type": "BOGO",
            "value": "BOGO Free",
            "source_url": "https://www.example.com/api/promos/bogo-coffee",
            "extracted_timestamp": "2023-07-09T12:30:00.000Z"
        },
        {
            "promo_title": "Invalid Promo - No URL",
            "description_text": "This should be skipped.",
            "start_date_iso": "2023-07-10",
            "end_date_iso": "2023-07-16",
            "type": "BOGO",
            "value": "BOGO Free",
            "source_url": None, # This will make validation fail
            "extracted_timestamp": "2023-07-09T12:30:00.000Z"
        }
    ]

    # Override the _fetch_from_api and _scrape_webpage to return dummy data for this main call
    # This is a common pattern for testing or demonstrating a pipeline without external calls.
    # In a production environment, you would remove this mocking.
    original_fetch_from_api = globals()['_fetch_from_api']
    original_scrape_webpage = globals()['_scrape_webpage']

    def mock_fetch_from_api(url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        logger.info(f"MOCK: Fetching data from API: {url}")
        return dummy_api_response_data

    def mock_scrape_webpage(url: str, selectors: Dict[str, str]) -> List[Dict[str, Any]]:
        logger.info(f"MOCK: Scraping webpage: {url}")
        # Simulate some scraped data based on selectors
        mock_scraped_data = [
            {
                'title': 'Flash Deal - 20% Off',
                'description': 'Limited time offer on all electronics.',
                'start_date': '2023-07-15',
                'end_date': '2023-07-17',
                'promo_type': 'discount',
                'promo_value': '20% OFF',
                'link': 'https://www.example.com/deals/flash-electronics'
            },
            {
                'title': 'New Customer Discount',
                'description': '10% off your first order.',
                'start_date': '2023-01-01', # Long running promo
                'end_date': None, # No end date
                'promo_type': 'welcome',
                'promo_value': '10% OFF',
                'link': 'https://www.example.com/deals/new-customer'
            },
             { # Invalid data for scraping: missing title
                'title': None,
                'description': 'This should be skipped.',
                'start_date': '2023-07-15',
                'end_date': '2023-07-17',
                'promo_type': 'discount',
                'promo_value': '20% OFF',
                'link': 'https://www.example.com/deals/invalid-no-title'
            },
            { # Invalid data for scraping: end_date before start_date
                'title': 'Promo with invalid dates',
                'description': 'This should be skipped.',
                'start_date': '2023-07-17',
                'end_date': '2023-07-15',
                'promo_type': 'discount',
                'promo_value': '20% OFF',
                'link': 'https://www.example.com/deals/invalid-dates'
            }
        ]
        
        # Filter mock data based on simple selector simulation for demonstration
        # In a real scraper, this filtering happens during BeautifulSoup parsing
        result_data = []
        for item in mock_scraped_data:
            scraped_item = {}
            for field, selector in selectors.items():
                if field == 'container':
                    continue
                # Simulate attribute extraction for 'link'
                if '::attr(href)' in selector:
                    scraped_item[field] = item.get(field) # Direct map for mock
                else:
                    scraped_item[field] = item.get(field)
            result_data.append(scraped_item)
        return result_data

    # Temporarily replace functions with mocks
    globals()['_fetch_from_api'] = mock_fetch_from_api
    globals()['_scrape_webpage'] = mock_scrape_webpage

    execute_promotion_pipeline(source_configs)

    # Restore original functions (good practice if running multiple tests or parts of app)
    globals()['_fetch_from_api'] = original_fetch_from_api
    globals()['_scrape_webpage'] = original_scrape_webpage

if __name__ == "__main__":
    main()