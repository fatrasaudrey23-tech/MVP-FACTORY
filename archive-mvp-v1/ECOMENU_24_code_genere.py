import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any

# --- Mock Data Storage (replaces a real database) ---
_mock_db: Dict[str, List[Dict[str, Any]]] = {
    "menus": [
        {"id": 1, "name": "Menu Classique", "description": "Un menu traditionnel", "price": 15.99, "is_active": True},
        {"id": 2, "name": "Menu Végétarien", "description": "Options sans viande", "price": 12.50, "is_active": True},
    ],
    "dishes": [
        {"id": 101, "name": "Salade César", "description": "Salade fraîche", "price": 8.00, "category": "Entrée"},
        {"id": 102, "name": "Burger Maison", "description": "Avec frites", "price": 14.50, "category": "Plat Principal"},
        {"id": 103, "name": "Mousse au chocolat", "description": "Dessert gourmand", "price": 6.00, "category": "Dessert"},
    ],
    "ingredients": [
        {"id": 1001, "name": "Tomate", "unit": "kg", "stock": 50},
        {"id": 1002, "name": "Fromage", "unit": "kg", "stock": 20},
        {"id": 1003, "name": "Laitue", "unit": "pièces", "stock": 100},
    ],
    "users": [
        {"id": 1, "username": "admin", "email": "admin@ecomenu.com", "role": "admin"},
        {"id": 2, "username": "chef", "email": "chef@ecomenu.com", "role": "chef"},
    ],
}

_next_id: Dict[str, int] = {
    "menus": 3,
    "dishes": 104,
    "ingredients": 1004,
    "users": 3,
}

# --- Mock Data Access Layer (replaces data_access_layer.py) ---

def _get_all_entities(entity_type: str) -> List[Dict[str, Any]]:
    """Retrieves all entities of a given type from the mock database."""
    return _mock_db.get(entity_type, [])

def _get_entity_by_id(entity_type: str, entity_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a specific entity by its ID from the mock database."""
    for entity in _mock_db.get(entity_type, []):
        if entity.get("id") == entity_id:
            return entity
    return None

def _create_entity(entity_type: str, data: Dict[str, Any]) -> bool:
    """Creates a new entity in the mock database."""
    if entity_type in _mock_db:
        data["id"] = _next_id[entity_type]
        _mock_db[entity_type].append(data)
        _next_id[entity_type] += 1
        return True
    return False

def _update_entity(entity_type: str, entity_id: int, data: Dict[str, Any]) -> bool:
    """Updates an existing entity in the mock database."""
    if entity_type in _mock_db:
        for i, entity in enumerate(_mock_db[entity_type]):
            if entity.get("id") == entity_id:
                _mock_db[entity_type][i].update(data)
                return True
    return False

def _delete_entity(entity_type: str, entity_id: int) -> bool:
    """Deletes an entity from the mock database."""
    if entity_type in _mock_db:
        initial_len = len(_mock_db[entity_type])
        _mock_db[entity_type] = [e for e in _mock_db[entity_type] if e.get("id") != entity_id]
        return len(_mock_db[entity_type]) < initial_len
    return False

def _get_dashboard_stats() -> Dict[str, int]:
    """Retrieves statistics for the dashboard."""
    return {
        "menus_count": len(_mock_db["menus"]),
        "dishes_count": len(_mock_db["dishes"]),
        "ingredients_count": len(_mock_db["ingredients"]),
        "users_count": len(_mock_db["users"]),
    }

# --- Mock Utility Functions (replaces utils.py) ---

def _validate_entity_data(entity_type: str, data: Dict[str, Any]) -> bool:
    """Validates input data for a given entity type."""
    # This is a basic placeholder. Real validation would be more complex.
    if not data:
        return False
    if entity_type == "menus":
        return "name" in data and "price" in data and isinstance(data["price"], (int, float))
    if entity_type == "dishes":
        return "name" in data and "price" in data and isinstance(data["price"], (int, float))
    if entity_type == "ingredients":
        return "name" in data and "stock" in data and isinstance(data["stock"], int)
    if entity_type == "users":
        return "username" in data and "email" in data
    return False

# --- Streamlit Application Functions ---

def _render_add_edit_form(entity_type: str, entity_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Displays a form to create a new entity or modify an existing one.
    """
    is_edit = entity_data is not None
    form_title = f"Modifier {entity_type.capitalize().rstrip('s')}" if is_edit else f"Ajouter un nouveau {entity_type.capitalize().rstrip('s')}"
    entity_id = entity_data.get("id") if is_edit else None

    with st.form(key=f"{entity_type}_form_{entity_id if is_edit else 'new'}"):
        st.subheader(form_title)

        form_data: Dict[str, Any] = {}
        if entity_type == "menus":
            form_data["name"] = st.text_input("Nom du Menu", value=entity_data.get("name", "") if is_edit else "")
            form_data["description"] = st.text_area("Description", value=entity_data.get("description", "") if is_edit else "")
            form_data["price"] = st.number_input("Prix", min_value=0.0, value=float(entity_data.get("price", 0.0)) if is_edit else 0.0, format="%.2f")
            form_data["is_active"] = st.checkbox("Actif", value=entity_data.get("is_active", True) if is_edit else True)
        elif entity_type == "dishes":
            form_data["name"] = st.text_input("Nom du Plat", value=entity_data.get("name", "") if is_edit else "")
            form_data["description"] = st.text_area("Description", value=entity_data.get("description", "") if is_edit else "")
            form_data["price"] = st.number_input("Prix", min_value=0.0, value=float(entity_data.get("price", 0.0)) if is_edit else 0.0, format="%.2f")
            form_data["category"] = st.selectbox("Catégorie", options=["Entrée", "Plat Principal", "Dessert", "Boisson"], index=["Entrée", "Plat Principal", "Dessert", "Boisson"].index(entity_data.get("category", "Plat Principal")) if is_edit else 1)
        elif entity_type == "ingredients":
            form_data["name"] = st.text_input("Nom de l'Ingrédient", value=entity_data.get("name", "") if is_edit else "")
            form_data["unit"] = st.text_input("Unité de mesure", value=entity_data.get("unit", "") if is_edit else "")
            form_data["stock"] = st.number_input("Stock", min_value=0, value=entity_data.get("stock", 0) if is_edit else 0, format="%d")
        elif entity_type == "users":
            form_data["username"] = st.text_input("Nom d'utilisateur", value=entity_data.get("username", "") if is_edit else "")
            form_data["email"] = st.text_input("Email", value=entity_data.get("email", "") if is_edit else "")
            form_data["role"] = st.selectbox("Rôle", options=["admin", "chef", "staff"], index=["admin", "chef", "staff"].index(entity_data.get("role", "staff")) if is_edit else 2)

        submitted = st.form_submit_button("Valider")

        if submitted:
            if not _validate_entity_data(entity_type, form_data):
                st.error("Erreur de validation: Veuillez remplir tous les champs requis.")
                return

            if is_edit and entity_id is not None:
                if _update_entity(entity_type, entity_id, form_data):
                    st.success(f"{entity_type.capitalize().rstrip('s')} mis à jour avec succès!")
                    st.session_state[f"{entity_type}_current_action"] = "view"
                    st.experimental_rerun()
                else:
                    st.error(f"Échec de la mise à jour du {entity_type.rstrip('s')}.")
            else:
                if _create_entity(entity_type, form_data):
                    st.success(f"{entity_type.capitalize().rstrip('s')} ajouté avec succès!")
                    st.session_state[f"{entity_type}_current_action"] = "view"
                    st.experimental_rerun()
                else:
                    st.error(f"Échec de l'ajout du nouveau {entity_type.rstrip('s')}.")

def render_dashboard() -> None:
    """
    Renders the dashboard section with an overview of the system.
    """
    st.header("Dashboard ECOMENU")
    st.write("Bienvenue sur le panneau d'administration ECOMENU.")

    stats = _get_dashboard_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Menus", stats.get("menus_count", 0))
    with col2:
        st.metric("Plats", stats.get("dishes_count", 0))
    with col3:
        st.metric("Ingrédients", stats.get("ingredients_count", 0))
    with col4:
        st.metric("Utilisateurs", stats.get("users_count", 0))

    st.subheader("Aperçu rapide")
    st.write("Ceci est un aperçu rapide des données du système.")
    
    st.markdown("---")
    st.subheader("Derniers Menus")
    menus_df = pd.DataFrame(_get_all_entities("menus"))
    if not menus_df.empty:
        st.dataframe(menus_df.head(5).set_index("id"))
    else:
        st.info("Aucun menu enregistré.")

def render_entity_management(entity_type: str) -> None:
    """
    Renders the CRUD management interface for a specific entity type.
    """
    st.header(f"Gestion des {entity_type.capitalize()}")

    # Initialize session state for current action if not present
    if f"{entity_type}_current_action" not in st.session_state:
        st.session_state[f"{entity_type}_current_action"] = "view"
        st.session_state[f"{entity_type}_selected_entity_id"] = None

    current_action = st.session_state[f"{entity_type}_current_action"]
    selected_entity_id = st.session_state[f"{entity_type}_selected_entity_id"]

    if current_action == "view":
        if st.button(f"Ajouter un nouveau {entity_type.rstrip('s')}", key=f"add_{entity_type}"):
            st.session_state[f"{entity_type}_current_action"] = "add"
            st.session_state[f"{entity_type}_selected_entity_id"] = None
            st.experimental_rerun()

        st.subheader(f"Liste des {entity_type.capitalize()}")
        entities = _get_all_entities(entity_type)
        if entities:
            df = pd.DataFrame(entities)
            st.dataframe(df.set_index("id"))

            st.write("---")
            st.subheader("Actions sur les entités")
            
            col_edit, col_delete = st.columns(2)
            with col_edit:
                entity_to_edit_id = st.number_input(f"ID du {entity_type.rstrip('s')} à modifier", min_value=1, key=f"edit_id_{entity_type}")
                if st.button("Modifier", key=f"edit_btn_{entity_type}"):
                    if _get_entity_by_id(entity_type, entity_to_edit_id):
                        st.session_state[f"{entity_type}_current_action"] = "edit"
                        st.session_state[f"{entity_type}_selected_entity_id"] = entity_to_edit_id
                        st.experimental_rerun()
                    else:
                        st.error(f"{entity_type.rstrip('s').capitalize()} non trouvé.")
            with col_delete:
                entity_to_delete_id = st.number_input(f"ID du {entity_type.rstrip('s')} à supprimer", min_value=1, key=f"delete_id_{entity_type}")
                if st.button("Supprimer", key=f"delete_btn_{entity_type}"):
                    if _delete_entity(entity_type, entity_to_delete_id):
                        st.success(f"{entity_type.rstrip('s').capitalize()} supprimé avec succès!")
                        st.experimental_rerun()
                    else:
                        st.error(f"Échec de la suppression du {entity_type.rstrip('s')}. ID non trouvé.")
        else:
            st.info(f"Aucun {entity_type.rstrip('s')} enregistré pour le moment.")

    elif current_action == "add":
        _render_add_edit_form(entity_type)
        if st.button("Annuler", key=f"cancel_add_{entity_type}"):
            st.session_state[f"{entity_type}_current_action"] = "view"
            st.session_state[f"{entity_type}_selected_entity_id"] = None
            st.experimental_rerun()

    elif current_action == "edit":
        entity_data = _get_entity_by_id(entity_type, selected_entity_id)
        if entity_data:
            _render_add_edit_form(entity_type, entity_data)
            if st.button("Annuler", key=f"cancel_edit_{entity_type}"):
                st.session_state[f"{entity_type}_current_action"] = "view"
                st.session_state[f"{entity_type}_selected_entity_id"] = None
                st.experimental_rerun()
        else:
            st.error(f"{entity_type.rstrip('s').capitalize()} à modifier non trouvé.")
            st.session_state[f"{entity_type}_current_action"] = "view"
            st.session_state[f"{entity_type}_selected_entity_id"] = None
            st.experimental_rerun()


def main() -> None:
    """
    Main entry point for the Streamlit application.
    Manages global navigation and content display.
    """
    st.set_page_config(
        page_title="ECOMENU Admin",
        page_icon="🍽️",
        layout="wide"
    )

    st.sidebar.title("Navigation")
    selection = st.sidebar.radio(
        "Aller à",
        ("Dashboard", "Menus", "Plats", "Ingrédients", "Utilisateurs")
    )

    if selection == "Dashboard":
        render_dashboard()
    elif selection == "Menus":
        render_entity_management("menus")
    elif selection == "Plats":
        render_entity_management("dishes")
    elif selection == "Ingrédients":
        render_entity_management("ingredients")
    elif selection == "Utilisateurs":
        render_entity_management("users")

if __name__ == "__main__":
    main()