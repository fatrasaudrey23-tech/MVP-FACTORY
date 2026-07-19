import requests
from bs4 import BeautifulSoup
import json
import os
import logging
from datetime import datetime
import PyPDF2
from typing import Dict, Any, List, Optional, Union
import re # For PDF regex parsing

# Pillow and pytesseract are imported but their full functionality for OCR
# is only outlined as it depends on external Tesseract installation and
# complex image processing, which goes beyond basic text extraction for this
# initial implementation.
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

def setup_logging() -> None:
    """
    Initialise et configure le système de journalisation (logging) pour l'application.
    Les messages de log sont dirigés vers un fichier spécifique et vers la console.
    """
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)
    log_filename = datetime.now().strftime("ecomenu_collector_%Y%m%d_%H%M%S.log")
    log_filepath = os.path.join(log_dir, log_filename)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filepath, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging setup complete.")

def load_collection_config(config_path: str) -> Dict[str, Any]:
    """
    Charge la configuration des différentes sources de circulaires à partir d'un fichier spécifié.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logging.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found at {config_path}")
        raise
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {config_path}. Check file format.")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading config: {e}")
        raise

def fetch_page_content(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Optional[str]:
    """
    Effectue une requête HTTP GET pour récupérer le contenu (généralement HTML) d'une URL donnée.
    """
    if headers is None:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()  # Lève une exception pour les codes d'état HTTP d'erreur
        logging.info(f"Successfully fetched content from {url}")
        return response.text
    except requests.exceptions.Timeout:
        logging.warning(f"Timeout occurred while fetching {url}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching {url}: {e}")
        return None

def fetch_pdf_content(url: str, output_dir: str, filename: str) -> Optional[str]:
    """
    Télécharge un fichier PDF depuis une URL spécifiée et l'enregistre dans un répertoire local.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    try:
        response = requests.get(url, stream=True, timeout=60) # Increased timeout for large files
        response.raise_for_status()

        if 'content-type' not in response.headers or 'application/pdf' not in response.headers['content-type']:
            logging.warning(f"URL {url} did not return a PDF content type. Actual: {response.headers.get('content-type', 'N/A')}")
            return None

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Successfully downloaded PDF from {url} to {filepath}")
        return filepath
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading PDF from {url}: {e}")
        return None
    except IOError as e:
        logging.error(f"Error writing PDF to file {filepath}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while downloading PDF from {url}: {e}")
        return None

def parse_html_flyer_list(html_content: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyse le contenu HTML d'une page pour identifier et extraire les métadonnées de chaque circulaire.
    """
    flyers: List[Dict[str, Any]] = []
    if not html_content:
        logging.warning("No HTML content provided for parsing flyer list.")
        return flyers

    try:
        soup = BeautifulSoup(html_content, 'lxml')
        list_config = config.get('selectors', {}).get('flyer_list', {})
        container_selector = list_config.get('container')

        if not container_selector:
            logging.warning("No 'container' selector defined for flyer list in config.")
            return flyers

        containers = soup.select(container_selector)
        if not containers:
            logging.warning(f"No flyer containers found with selector: {container_selector}")
            return flyers

        for container in containers:
            title_elem = container.select_one(list_config.get('title', ''))
            period_elem = container.select_one(list_config.get('period', ''))
            url_elem = container.select_one(list_config.get('url', ''))

            flyer_title = title_elem.get_text(strip=True) if title_elem else "N/A"
            flyer_period = period_elem.get_text(strip=True) if period_elem else "N/A"
            flyer_url = url_elem['href'] if url_elem and 'href' in url_elem.attrs else "N/A"
            flyer_type = url_elem.get(list_config.get('type_attribute', ''), 'html') if url_elem else 'html'

            # Ensure absolute URL
            if flyer_url and not flyer_url.startswith(('http://', 'https://')):
                # This is a simplification; a more robust solution would require the base URL of the page
                # to construct absolute URLs correctly. For now, we'll just log a warning.
                logging.warning(f"Relative URL found: {flyer_url}. Cannot resolve to absolute without base URL.")
                # For demonstration, assume base URL is part of the config or context.
                # For now, we'll keep it as is, or prepend a dummy base.
                # Example: flyer_url = urljoin(base_url, flyer_url)

            flyers.append({
                "title": flyer_title,
                "period": flyer_period,
                "url": flyer_url,
                "type": flyer_type
            })
        logging.info(f"Extracted {len(flyers)} flyers from HTML content.")
    except Exception as e:
        logging.error(f"Error parsing HTML flyer list: {e}")
    return flyers

def parse_html_flyer_items(html_content: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyse le contenu HTML d'une page de circulaire spécifique pour en extraire les informations brutes des articles promotionnels.
    """
    items: List[Dict[str, Any]] = []
    if not html_content:
        logging.warning("No HTML content provided for parsing flyer items.")
        return items

    try:
        soup = BeautifulSoup(html_content, 'lxml')
        item_config = config.get('selectors', {}).get('flyer_items', {})
        item_container_selector = item_config.get('item_container')

        if not item_container_selector:
            logging.warning("No 'item_container' selector defined for flyer items in config.")
            return items

        containers = soup.select(item_container_selector)
        if not containers:
            logging.warning(f"No item containers found with selector: {item_container_selector}")
            return items

        for container in containers:
            name_elem = container.select_one(item_config.get('name', ''))
            price_elem = container.select_one(item_config.get('price', ''))
            desc_elem = container.select_one(item_config.get('description', ''))
            image_elem = container.select_one(item_config.get('image_url', ''))

            product_name = name_elem.get_text(strip=True) if name_elem else "N/A"
            product_price = price_elem.get_text(strip=True) if price_elem else "N/A"
            product_desc = desc_elem.get_text(strip=True) if desc_elem else "N/A"
            image_url = image_elem['src'] if image_elem and 'src' in image_elem.attrs else "N/A"

            items.append({
                "name": product_name,
                "price": product_price,
                "description": product_desc,
                "image_url": image_url
            })
        logging.info(f"Extracted {len(items)} items from HTML flyer content.")
    except Exception as e:
        logging.error(f"Error parsing HTML flyer items: {e}")
    return items

def parse_pdf_flyer_content(pdf_path: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrait le texte et potentiellement des informations structurées d'un fichier PDF de circulaire local.
    Cette fonction utilise PyPDF2 pour l'extraction de texte. Pour les PDFs scannés (images),
    une logique OCR utilisant Pillow et pytesseract serait nécessaire.
    """
    items: List[Dict[str, Any]] = []
    if not os.path.exists(pdf_path):
        logging.error(f"PDF file not found at {pdf_path}")
        return items

    try:
        pdf_text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfFileReader(file)
            for page_num in range(reader.numPages):
                page = reader.getPage(page_num)
                pdf_text += page.extractText() + "\n"

        if not pdf_text.strip():
            logging.warning(f"No text extracted from PDF {pdf_path} using PyPDF2. It might be an image-based PDF.")
            if OCR_AVAILABLE:
                logging.info("OCR is available. Attempting OCR on PDF pages (requires Poppler and pdf2image or PyMuPDF).")
                # Placeholder for OCR logic.
                # This would typically involve converting PDF pages to images (e.g., using pdf2image or PyMuPDF)
                # and then processing each image with pytesseract.
                # Example (requires `pdf2image` and `Poppler`):
                # from pdf2image import convert_from_path
                # images = convert_from_path(pdf_path)
                # for i, image in enumerate(images):
                #     text_from_image = pytesseract.image_to_string(image)
                #     pdf_text += text_from_image + "\n"
                #     logging.debug(f"OCR extracted text from page {i+1}.")
                if not pdf_text.strip(): # If OCR also yielded nothing, or if not implemented
                    logging.warning(f"OCR attempt for {pdf_path} also yielded no significant text or was not fully implemented.")
            else:
                logging.warning("OCR libraries (Pillow, pytesseract) not fully configured or available for image-based PDF processing.")
            return items # Return empty if no text or OCR not fully implemented

        # Apply regex rules from config to extract structured data
        pdf_extraction_rules = config.get('selectors', {}).get('pdf_extraction_rules', {})
        price_pattern = pdf_extraction_rules.get('regex_pattern_price')
        product_pattern = pdf_extraction_rules.get('regex_pattern_product')

        # This is a simplified regex-based extraction. Real-world PDF parsing is highly complex.
        if price_pattern and product_pattern:
            # Find all product names and prices
            product_names = re.findall(product_pattern, pdf_text, re.MULTILINE)
            prices = re.findall(price_pattern, pdf_text, re.MULTILINE)

            # Simple pairing, assuming order and quantity match. This is a weak assumption.
            # A more robust solution would involve more context-aware parsing.
            min_len = min(len(product_names), len(prices))
            for i in range(min_len):
                items.append({
                    "name": product_names[i].strip(),
                    "price": prices[i].strip(),
                    "description": "Extracted from PDF",
                    "image_url": "N/A" # No image URL from text PDF
                })
            logging.info(f"Extracted {len(items)} items from PDF {pdf_path} using regex rules.")
        else:
            logging.info(f"No specific regex rules provided for {pdf_path}. Storing raw text as one item.")
            items.append({"raw_text": pdf_text}) # Fallback to storing all text
            
    except PyPDF2.utils.PdfReadError as e:
        logging.error(f"Failed to read PDF file {pdf_path}: {e}. File might be corrupted or encrypted.")
    except Exception as e:
        logging.error(f"Error parsing PDF content from {pdf_path}: {e}")
    return items

def save_raw_data(data: List[Dict[str, Any]], source_name: str, flyer_metadata: Dict[str, Any], output_base_dir: str) -> str:
    """
    Enregistre les données brutes collectées pour une circulaire spécifique dans un fichier JSON.
    """
    # Create a unique identifier for the flyer based on its metadata and collection date
    # Sanitize title for filename
    sanitized_title = re.sub(r'[^\w\-_\. ]', '_', flyer_metadata.get('title', 'untitled_flyer'))
    collection_date = datetime.now().strftime("%Y%m%d_%H%M%S")
    flyer_id = f"{sanitized_title}_{collection_date}"

    # Construct output directory path: output_base_dir/source_name/flyer_id/
    flyer_output_dir = os.path.join(output_base_dir, source_name, flyer_id)
    os.makedirs(flyer_output_dir, exist_ok=True)

    # Save flyer items data
    data_filepath = os.path.join(flyer_output_dir, "items.json")
    try:
        with open(data_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logging.info(f"Raw flyer items saved to {data_filepath}")
    except IOError as e:
        logging.error(f"Error saving flyer items to {data_filepath}: {e}")
        return ""

    # Save flyer metadata
    metadata_filepath = os.path.join(flyer_output_dir, "metadata.json")
    try:
        with open(metadata_filepath, 'w', encoding='utf-8') as f:
            json.dump(flyer_metadata, f, ensure_ascii=False, indent=4)
        logging.info(f"Flyer metadata saved to {metadata_filepath}")
    except IOError as e:
        logging.error(f"Error saving flyer metadata to {metadata_filepath}: {e}")
        return ""

    return data_filepath

def orchestrate_collection(config: Dict[str, Any]) -> None:
    """
    Fonction principale qui gère le flux de travail complet de la collecte.
    """
    output_base_dir = config.get('output_base_dir', './raw_data')
    sources = config.get('sources', {})

    for source_name, source_config in sources.items():
        logging.info(f"Starting collection for source: {source_name}")
        collection_type = source_config.get('collection_type', 'html')
        flyer_list_url = source_config.get('flyer_list_url')
        source_headers = source_config.get('headers')

        if not flyer_list_url:
            logging.error(f"Skipping source {source_name}: 'flyer_list_url' is missing in configuration.")
            continue

        collected_flyers: List[Dict[str, Any]] = []

        if collection_type == "html":
            logging.info(f"Fetching HTML flyer list from {flyer_list_url}")
            html_content = fetch_page_content(flyer_list_url, headers=source_headers)
            if html_content:
                collected_flyers = parse_html_flyer_list(html_content, source_config)
            else:
                logging.error(f"Failed to retrieve HTML content for flyer list from {flyer_list_url}")
                continue
        elif collection_type == "pdf" and ".pdf" in flyer_list_url.lower():
            # QA FIX: Direct PDF link for a source configured as "pdf"
            logging.info(f"Source {source_name} is configured for direct PDF collection from {flyer_list_url}")
            # Create a dummy flyer metadata for this direct PDF
            pdf_filename = os.path.basename(flyer_list_url).split('?')[0] # Remove query params
            flyer_metadata = {
                "title": f"{source_name} Direct PDF",
                "period": datetime.now().strftime("%Y-%m-%d"),
                "url": flyer_list_url,
                "type": "pdf"
            }
            collected_flyers.append(flyer_metadata)
        else:
            logging.error(f"Unsupported collection_type '{collection_type}' or invalid flyer_list_url for source {source_name}.")
            continue

        if not collected_flyers:
            logging.warning(f"No flyers found or parsed for source {source_name}.")
            continue

        for flyer in collected_flyers:
            flyer_url = flyer.get('url')
            flyer_type = flyer.get('type', 'html') # Default to html if not specified
            if not flyer_url or flyer_url == "N/A":
                logging.warning(f"Skipping flyer with missing URL: {flyer.get('title', 'N/A')}")
                continue

            logging.info(f"Processing flyer: {flyer.get('title')} ({flyer_url}) [Type: {flyer_type}]")
            raw_items_data: List[Dict[str, Any]] = []

            if flyer_type == "html":
                flyer_html_content = fetch_page_content(flyer_url, headers=source_headers)
                if flyer_html_content:
                    raw_items_data = parse_html_flyer_items(flyer_html_content, source_config)
                else:
                    logging.error(f"Failed to retrieve HTML content for flyer {flyer.get('title')} from {flyer_url}")
            elif flyer_type == "pdf":
                # Generate a filename for the PDF
                pdf_filename = os.path.basename(flyer_url).split('?')[0] # Remove query parameters
                # Use flyer title or a generic name if title is not clean for filename
                sanitized_pdf_name = re.sub(r'[^\w\-_\. ]', '_', flyer.get('title', 'downloaded_pdf'))
                pdf_filename = f"{sanitized_pdf_name}_{datetime.now().strftime('%Y%m%d')}.pdf"

                pdf_local_path = fetch_pdf_content(flyer_url, os.path.join(output_base_dir, source_name, "pdfs"), pdf_filename)
                if pdf_local_path:
                    raw_items_data = parse_pdf_flyer_content(pdf_local_path, source_config)
                else:
                    logging.error(f"Failed to download PDF for flyer {flyer.get('title')} from {flyer_url}")
            else:
                logging.warning(f"Unsupported flyer type '{flyer_type}' for flyer {flyer.get('title')}. Skipping.")
                continue

            if raw_items_data:
                save_raw_data(raw_items_data, source_name, flyer, output_base_dir)
            else:
                logging.warning(f"No raw items data collected for flyer {flyer.get('title')}.")

        logging.info(f"Finished collection for source: {source_name}")

if __name__ == "__main__":
    setup_logging()
    logging.info("Starting Ecomenu Circulars Collector.")

    # Create a dummy config file for demonstration
    dummy_config_path = "config.json"
    dummy_config_content = {
        "output_base_dir": "./raw_data",
        "log_dir": "./logs",
        "sources": {
            "example_retailer_html": {
                "collection_type": "html",
                "flyer_list_url": "http://www.example.com/flyers", # Replace with a real URL for testing
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
                "selectors": {
                    "flyer_list": {
                        "container": ".flyer-card",
                        "title": "h3.flyer-title",
                        "period": ".flyer-period",
                        "url": "a.flyer-link",
                        "type_attribute": "data-flyer-type"
                    },
                    "flyer_items": {
                        "item_container": ".product-item",
                        "name": ".product-name",
                        "price": ".product-price",
                        "description": ".product-desc",
                        "image_url": "img.product-image"
                    }
                }
            },
            "example_retailer_pdf_direct": {
                "collection_type": "pdf",
                "flyer_list_url": "http://www.africau.edu/images/default/sample.pdf", # A sample PDF for direct download
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
                "selectors": {
                    "pdf_extraction_rules": {
                        # These regex patterns are highly dependent on PDF content structure
                        "regex_pattern_price": "\\$(\\d+\\.\\d{2})",
                        "regex_pattern_product": "([A-Z][a-z]+(?:\\s[A-Z][a-z]+)*)\\s+\\$\\d+\\.\\d{2}"
                    }
                }
            }
        }
    }

    try:
        with open(dummy_config_path, 'w', encoding='utf-8') as f:
            json.dump(dummy_config_content, f, ensure_ascii=False, indent=4)
        logging.info(f"Dummy config file created at {dummy_config_path}")

        collection_config = load_collection_config(dummy_config_path)
        orchestrate_collection(collection_config)

    except Exception as e:
        logging.critical(f"A critical error occurred during the collection process: {e}", exc_info=True)
    finally:
        # Clean up the dummy config file
        if os.path.exists(dummy_config_path):
            os.remove(dummy_config_path)
            logging.info(f"Cleaned up dummy config file: {dummy_config_path}")
        logging.info("Ecomenu Circulars Collector finished.")