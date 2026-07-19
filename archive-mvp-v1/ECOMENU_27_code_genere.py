import json
import logging
import datetime
from typing import List, Dict, Any, Optional

# --- Global/Module-level configurations and logger ---
_LOGGER: logging.Logger = logging.getLogger(__name__)
_CONFIG: Dict[str, Any] = {}

def initialize_dashboard_service(config: Dict[str, Any]) -> None:
    """
    Initializes the service by loading necessary configurations and setting up logging.
    """
    global _CONFIG
    _CONFIG = config

    log_level_str = config.get("logging_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logging.basicConfig(level=log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    _LOGGER.info("Dashboard service initialized with configuration: %s", json.dumps(config))

def _fetch_dashboard_metrics(user_id: int, user_role: str) -> Dict[str, Any]:
    """
    Retrieves raw and aggregated dashboard-specific data for a given user,
    potentially filtered by their role.
    """
    _LOGGER.info("Fetching dashboard metrics for user_id: %d, role: %s", user_id, user_role)

    # Placeholder for actual data fetching logic (e.g., from a database or external API)
    # In a real application, this would involve database queries or API calls.
    if user_role == 'admin':
        metrics = {
            'total_orders_today': 45,
            'revenue_mtd': 5678.90,
            'pending_reservations': 7,
            'top_selling_item': 'Truffle Pizza',
            'new_customers_this_week': 12,
            'operational_status': 'All Systems Green'
        }
    elif user_role == 'staff':
        metrics = {
            'total_orders_today': 15,
            'pending_reservations': 3,
            'items_to_restock': ['Milk', 'Coffee Beans'],
            'shift_start_time': '08:00 AM'
        }
    else: # customer or other roles
        metrics = {
            'your_last_order_date': datetime.date(2023, 10, 26).isoformat(),
            'loyalty_points': 520,
            'favorite_item': 'Burger Deluxe'
        }

    _LOGGER.debug("Metrics fetched for user %d: %s", user_id, json.dumps(metrics))
    return metrics

def _get_base_menu_items() -> List[Dict[str, Any]]:
    """
    Defines and returns the complete, unfiltered structure of the application's main menu.
    """
    _LOGGER.info("Retrieving base menu items.")

    # Menu items could also be loaded from a JSON configuration file specified in _CONFIG.
    menu_items = [
        {'label': 'Dashboard', 'path': '/', 'icon': 'home', 'required_roles': ['admin', 'staff', 'customer']},
        {'label': 'Orders', 'path': '/orders', 'icon': 'shopping-cart', 'required_roles': ['admin', 'staff']},
        {'label': 'Reservations', 'path': '/reservations', 'icon': 'calendar', 'required_roles': ['admin', 'staff']},
        {'label': 'Menu Management', 'path': '/menu', 'icon': 'book', 'required_roles': ['admin']},
        {'label': 'Customers', 'path': '/customers', 'icon': 'users', 'required_roles': ['admin', 'staff']},
        {'label': 'Reports', 'path': '/reports', 'icon': 'bar-chart', 'required_roles': ['admin']},
        {'label': 'Profile', 'path': '/profile', 'icon': 'user', 'required_roles': ['admin', 'staff', 'customer']},
        {'label': 'Settings', 'path': '/settings', 'icon': 'settings', 'required_roles': ['admin']}
    ]
    _LOGGER.debug("Base menu items: %s", json.dumps(menu_items))
    return menu_items

def _filter_menu_by_role(all_menu_items: List[Dict[str, Any]], user_role: str) -> List[Dict[str, Any]]:
    """
    Filters the complete list of menu items to include only those accessible by the specified user role.
    """
    _LOGGER.info("Filtering menu items for role: %s", user_role)
    filtered_menu = []
    for item in all_menu_items:
        if user_role in item.get('required_roles', []):
            filtered_menu.append(item)
    _LOGGER.debug("Filtered menu for role %s: %s", user_role, json.dumps(filtered_menu))
    return filtered_menu

def _log_user_access(user_id: int, user_role: str) -> None:
    """
    Logs an event of a user accessing the dashboard and main menu for audit or analysis.
    """
    _LOGGER.info("User access logged: user_id=%d, role=%s, event='dashboard_access'", user_id, user_role)

def get_dashboard_and_menu_data(user_id: int, user_role: str) -> Dict[str, Any]:
    """
    Orchestrates the retrieval of dashboard data and the construction of the main menu
    for a specific user.
    """
    _LOGGER.info("Starting data retrieval for dashboard and menu for user_id: %d, role: %s", user_id, user_role)

    _log_user_access(user_id, user_role)

    dashboard_data = _fetch_dashboard_metrics(user_id, user_role)
    all_menu_items = _get_base_menu_items()
    main_menu = _filter_menu_by_role(all_menu_items, user_role)

    result = {
        'dashboard_data': dashboard_data,
        'main_menu': main_menu
    }

    _LOGGER.info("Finished data retrieval for dashboard and menu for user_id: %d", user_id)
    _LOGGER.debug("Full response for user %d: %s", user_id, json.dumps(result))
    return result

if __name__ == "__main__":
    # Example Usage:

    # 1. Initialize the service with some configuration
    service_config = {
        "database_url": "sqlite:///./app.db",
        "menu_config_path": "./menu.json",
        "logging_level": "DEBUG" # Set to INFO for less verbose output
    }
    initialize_dashboard_service(service_config)

    print("\n--- Testing for Admin User ---")
    admin_user_id = 101
    admin_user_role = 'admin'
    admin_data = get_dashboard_and_menu_data(admin_user_id, admin_user_role)
    print("Admin Dashboard Data:", json.dumps(admin_data['dashboard_data'], indent=2))
    print("Admin Main Menu:", json.dumps(admin_data['main_menu'], indent=2))

    print("\n--- Testing for Staff User ---")
    staff_user_id = 202
    staff_user_role = 'staff'
    staff_data = get_dashboard_and_menu_data(staff_user_id, staff_user_role)
    print("Staff Dashboard Data:", json.dumps(staff_data['dashboard_data'], indent=2))
    print("Staff Main Menu:", json.dumps(staff_data['main_menu'], indent=2))

    print("\n--- Testing for Customer User ---")
    customer_user_id = 303
    customer_user_role = 'customer'
    customer_data = get_dashboard_and_menu_data(customer_user_id, customer_user_role)
    print("Customer Dashboard Data:", json.dumps(customer_data['dashboard_data'], indent=2))
    print("Customer Main Menu:", json.dumps(customer_data['main_menu'], indent=2))

    print("\n--- Testing for Unknown Role User ---")
    unknown_user_id = 404
    unknown_user_role = 'guest' # A role not explicitly handled in _fetch_dashboard_metrics
    unknown_data = get_dashboard_and_menu_data(unknown_user_id, unknown_user_role)
    print("Unknown Role Dashboard Data:", json.dumps(unknown_data['dashboard_data'], indent=2))
    print("Unknown Role Main Menu:", json.dumps(unknown_data['main_menu'], indent=2))