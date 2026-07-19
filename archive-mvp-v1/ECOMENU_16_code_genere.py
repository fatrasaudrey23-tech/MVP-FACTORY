import requests
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import typing

# --- Configuration Constants ---
DEFAULT_CONFIG_PATH = "config/brands.json"
DEFAULT_OUTPUT_DIR = "data_raw"
DEFAULT_LOG_FILE_PATH = "logs/brand_data_collector.log"

# --- Setup Logging ---
def setup_logging(log_file_path: str) -> None:
    """
    Configure le système de journalisation pour enregistrer les événements dans un fichier
    et potentiellement sur la console.
    """
    log_dir = Path(log_file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

# --- Configuration Loading ---
def load_brand_configurations(config_path: str) -> typing.Dict[str, typing.Any]:
    """
    Charge les configurations des différentes enseignes à partir d'un fichier JSON.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            configs = json.load(f)
        logging.info(f"Configurations chargées depuis {config_path}")
        return configs
    except FileNotFoundError:
        logging.error(f"Fichier de configuration non trouvé : {config_path}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Erreur de formatage JSON dans le fichier {config_path}: {e}")
        return {}
    except Exception as e:
        logging.error(f"Erreur inattendue lors du chargement des configurations: {e}")
        return {}

# --- Data Fetching Internal Functions ---
def _fetch_web_data(url: str, selectors: typing.Optional[typing.Dict[str, str]]) -> typing.Optional[str]:
    """
    Fonction interne pour récupérer et potentiellement pré-traiter (e.g., BeautifulSoup)
    le contenu d'une page web.
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Lève une exception pour les codes d'état HTTP d'erreur

        if selectors:
            soup = BeautifulSoup(response.text, 'html.parser')
            extracted_parts = []
            for name, selector in selectors.items():
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        extracted_parts.append(str(element))
                else:
                    logging.warning(f"Aucun élément trouvé pour le sélecteur '{selector}' sur {url}")
            return "\n".join(extracted_parts) if extracted_parts else response.text
        else:
            return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur lors de la récupération de la page web {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Erreur inattendue lors du traitement de la page web {url}: {e}")
        return None

def _fetch_api_data(url: str, params: typing.Optional[typing.Dict[str, str]] = None,
                    headers: typing.Optional[typing.Dict[str, str]] = None) -> typing.Union[typing.Dict, typing.List, None]:
    """
    Fonction interne pour interroger une API et récupérer sa réponse.
    """
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status() # Lève une exception pour les codes d'état HTTP d'erreur
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur lors de l'appel API à {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Erreur de décodage JSON de la réponse API pour {url}: {e}. Réponse brute: {response.text[:200]}...")
        return None
    except Exception as e:
        logging.error(f"Erreur inattendue lors de l'appel API à {url}: {e}")
        return None

# --- Main Data Fetching Function ---
def fetch_raw_data(brand_config: typing.Dict[str, typing.Any]) -> typing.Union[str, bytes, None]:
    """
    Fonction principale de récupération de données. Elle délègue à _fetch_web_data
    ou _fetch_api_data en fonction du type de source défini dans la configuration de l'enseigne.
    """
    brand_name = brand_config.get('name', 'UnknownBrand')
    source_type = brand_config.get('type')
    url = brand_config.get('url')

    if not url:
        logging.error(f"URL manquante pour l'enseigne {brand_name}.")
        return None

    logging.info(f"Début de la collecte pour {brand_name} depuis {url} (Type: {source_type}).")

    if source_type == 'web':
        selectors = brand_config.get('extraction_rules')
        return _fetch_web_data(url, selectors)
    elif source_type == 'api':
        params = brand_config.get('params')
        headers = brand_config.get('headers')
        api_data = _fetch_api_data(url, params, headers)
        if api_data is not None:
            # Correction QA: Convertir dict/list en str JSON pour respecter le type de retour
            try:
                return json.dumps(api_data, indent=2, ensure_ascii=False)
            except TypeError as e:
                logging.error(f"Impossible de sérialiser les données API en JSON pour {brand_name}: {e}")
                return None
        return None
    else:
        logging.error(f"Type de source inconnu '{source_type}' pour l'enseigne {brand_name}.")
        return None

# --- Data Saving Function ---
def save_raw_data(brand_name: str, data: typing.Union[str, bytes], output_dir: str, timestamp: str) -> typing.Optional[str]:
    """
    Sauvegarde les données brutes collectées dans un fichier.
    Le chemin de sauvegarde doit être structuré (e.g., output_dir/brand_name/timestamp_data.ext).
    """
    try:
        brand_output_path = Path(output_dir) / brand_name
        brand_output_path.mkdir(parents=True, exist_ok=True)

        file_extension = ".txt"
        if isinstance(data, str):
            try:
                json.loads(data) # Tente de parser pour voir si c'est du JSON
                file_extension = ".json"
            except json.JSONDecodeError:
                if "<html" in data.lower(): # Heuristique simple pour HTML
                    file_extension = ".html"
                else:
                    file_extension = ".txt"
        elif isinstance(data, bytes):
            file_extension = ".bin"

        file_name = f"{timestamp}{file_extension}"
        full_file_path = brand_output_path / file_name

        mode = 'w' if isinstance(data, str) else 'wb'
        encoding = 'utf-8' if isinstance(data, str) else None

        with open(full_file_path, mode, encoding=encoding) as f:
            f.write(data)

        logging.info(f"Données brutes de '{brand_name}' sauvegardées dans {full_file_path}")
        return str(full_file_path)
    except IOError as e:
        logging.error(f"Erreur d'écriture des données pour '{brand_name}' dans {full_file_path}: {e}")
        return None
    except Exception as e:
        logging.error(f"Erreur inattendue lors de la sauvegarde des données pour '{brand_name}': {e}")
        return None

# --- Process Single Brand ---
def process_brand(brand_config: typing.Dict[str, typing.Any], output_dir: str) -> None:
    """
    Orchestre le processus de collecte et de sauvegarde pour une seule enseigne.
    """
    brand_name = brand_config.get('name', 'UnknownBrand')
    current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logging.info(f"Traitement de l'enseigne : {brand_name}")

    raw_data = fetch_raw_data(brand_config)

    if raw_data is not None:
        saved_path = save_raw_data(brand_name, raw_data, output_dir, current_timestamp)
        if saved_path:
            logging.info(f"Collecte et sauvegarde réussies pour {brand_name}. Fichier: {saved_path}")
        else:
            logging.error(f"Échec de la sauvegarde des données pour {brand_name}.")
    else:
        logging.error(f"Échec de la récupération des données pour {brand_name}.")

# --- Main Script Function ---
def main(config_path: str = DEFAULT_CONFIG_PATH,
         output_dir: str = DEFAULT_OUTPUT_DIR,
         log_file_path: str = DEFAULT_LOG_FILE_PATH) -> None:
    """
    Fonction principale du script, orchestre l'ensemble du processus pour toutes les enseignes configurées.
    """
    setup_logging(log_file_path)
    logging.info("Démarrage du script de collecte de données brutes des enseignes.")

    # Créer le répertoire de sortie principal si inexistant
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    logging.info(f"Répertoire de sortie '{output_dir}' vérifié/créé.")

    brand_configurations = load_brand_configurations(config_path)

    if not brand_configurations:
        logging.error("Aucune configuration d'enseigne valide à traiter. Arrêt du script.")
        return

    for brand_name, config in brand_configurations.items():
        # Ajouter le nom de l'enseigne à la configuration pour un accès facile
        config['name'] = brand_name
        try:
            process_brand(config, output_dir)
        except Exception as e:
            logging.error(f"Erreur irrécupérable lors du traitement de l'enseigne {brand_name}: {e}", exc_info=True)

    logging.info("Fin du script de collecte de données brutes des enseignes.")

# --- Entry Point ---
if __name__ == "__main__":
    # Assurez-vous que les répertoires "config" et "logs" existent pour les exemples.
    Path("config").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)

    # Exemple de fichier de configuration (à créer manuellement ou par un autre script)
    # config/brands.json
    # {
    #   "BrandA": {
    #     "type": "web",
    #     "url": "http://quotes.toscrape.com/",
    #     "extraction_rules": {
    #       "main_content": ".row"
    #     }
    #   },
    #   "BrandB": {
    #     "type": "api",
    #     "url": "https://jsonplaceholder.typicode.com/posts/1",
    #     "params": {},
    #     "headers": {
    #       "Accept": "application/json"
    #     }
    #   },
    #   "BrandC": {
    #     "type": "web",
    #     "url": "https://www.google.com/search?q=example",
    #     "extraction_rules": {}
    #   },
    #   "BrandD": {
    #     "type": "api",
    #     "url": "https://httpbin.org/get",
    #     "params": {"test": "value"},
    #     "headers": {"User-Agent": "EcoMenu-Collector/1.0"}
    #   }
    # }
    #
    # Créez un fichier config/brands.json avec ce contenu pour tester.

    # Pour l'exécution directe, on peut passer les chemins ou utiliser les valeurs par défaut.
    main(
        config_path=DEFAULT_CONFIG_PATH,
        output_dir=DEFAULT_OUTPUT_DIR,
        log_file_path=DEFAULT_LOG_FILE_PATH
    )