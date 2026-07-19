import decimal
from typing import Optional

# Simulate a persistence layer (e.g., a database table)
# In a real application, this would be an ORM model or a database client.
_user_budgets_db = {} # type: dict[str, decimal.Decimal]

def validate_budget_input(budget_str: str) -> Optional[decimal.Decimal]:
    """
    Valide une entrée utilisateur (sous forme de chaîne de caractères) pour s'assurer
    qu'elle représente un montant de budget valide. Le montant doit être un nombre
    et strictement positif.
    """
    if not budget_str:
        return None
    try:
        budget_decimal = decimal.Decimal(budget_str)
        if budget_decimal <= decimal.Decimal('0'):
            return None
        return budget_decimal
    except decimal.InvalidOperation:
        return None

def save_user_budget(user_id: str, budget_amount: decimal.Decimal) -> bool:
    """
    Enregistre ou met à jour le montant du budget pour un utilisateur spécifique
    dans le système de persistance. Le budget_amount doit avoir été préalablement validé.
    """
    if not isinstance(user_id, str) or not user_id:
        # User ID must be a non-empty string
        return False
    if not isinstance(budget_amount, decimal.Decimal) or budget_amount <= decimal.Decimal('0'):
        # Budget amount must be a positive Decimal
        return False

    try:
        _user_budgets_db[user_id] = budget_amount
        return True
    except Exception:
        # Simulate a database error
        return False

def get_user_budget(user_id: str) -> Optional[decimal.Decimal]:
    """
    Récupère le budget actuellement défini pour un utilisateur donné.
    """
    if not isinstance(user_id, str) or not user_id:
        return None
    
    try:
        return _user_budgets_db.get(user_id)
    except Exception:
        # Simulate a database error
        return None

def delete_user_budget(user_id: str) -> bool:
    """
    Supprime le budget associé à un utilisateur spécifique.
    """
    if not isinstance(user_id, str) or not user_id:
        return False
        
    try:
        if user_id in _user_budgets_db:
            del _user_budgets_db[user_id]
        return True # Return True even if not found, as the goal (no budget) is achieved
    except Exception:
        # Simulate a database error
        return False