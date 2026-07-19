import pandas as pd
import json
import datetime
from typing import Dict, Any, List, Optional, Union

def load_financial_data(source_type: str, source_path: str, **kwargs) -> pd.DataFrame:
    """
    Charge les données financières brutes depuis une source spécifiée.

    Args:
        source_type (str): Type de la source de données (ex: "csv", "excel", "database").
        source_path (str): Chemin d'accès au fichier (pour CSV/Excel) ou chaîne de connexion/identifiants de base de données (pour DB).
        **kwargs: Arguments supplémentaires passés directement à la fonction de lecture de pandas ou au connecteur DB.

    Returns:
        pd.DataFrame: Un DataFrame pandas contenant les données brutes.

    Raises:
        ValueError: Si le type de source n'est pas supporté ou si des arguments de connexion DB sont manquants.
        IOError: En cas d'erreur de lecture de fichier.
        Exception: Pour d'autres erreurs de lecture de données.
    """
    try:
        if source_type == "csv":
            return pd.read_csv(source_path, **kwargs)
        elif source_type == "excel":
            return pd.read_excel(source_path, **kwargs)
        elif source_type == "database":
            if 'con' not in kwargs:
                raise ValueError("Pour 'database' source_type, 'con' (connection object or URI) must be provided in kwargs.")
            return pd.read_sql(source_path, con=kwargs['con'], **kwargs)
        else:
            raise ValueError(f"Source type '{source_type}' not supported.")
    except FileNotFoundError as e:
        raise IOError(f"File not found at '{source_path}': {e}")
    except pd.errors.EmptyDataError as e:
        raise IOError(f"No data in file at '{source_path}': {e}")
    except Exception as e:
        raise Exception(f"Error loading data from '{source_path}': {e}")

def _preprocess_financial_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fonction interne de nettoyage et de standardisation des données financières chargées.
    Elle assure la cohérence des types et la qualité des données.

    Args:
        df (pd.DataFrame): Le DataFrame de données brutes.

    Returns:
        pd.DataFrame: Un DataFrame nettoyé, avec les types de données corrects et les colonnes standardisées.

    Raises:
        ValueError: Si des colonnes critiques sont manquantes après le renommage.
    """
    # Make a copy to avoid modifying the original DataFrame passed
    processed_df = df.copy()

    # Column standardization (assuming common input names and mapping to standard names)
    column_rename_map = {
        'transaction_date': 'date',
        'Date': 'date',
        'revenue_amount': 'amount',
        'Amount': 'amount',
        'budget_amount': 'budget_amount',
        'Budget': 'budget_amount',
        'revenue_source': 'revenue_source',
        'Source': 'revenue_source',
        'category': 'category',
        'Category': 'category'
    }

    # Apply renaming for existing columns
    cols_to_rename = {col: new_name for col, new_name in column_rename_map.items() if col in processed_df.columns}
    processed_df.rename(columns=cols_to_rename, inplace=True)

    required_cols = ['date', 'amount', 'budget_amount']
    for col in required_cols:
        if col not in processed_df.columns:
            raise ValueError(f"Required column '{col}' is missing after preprocessing. Available columns: {processed_df.columns.tolist()}")

    # Type Conversion
    try:
        processed_df['date'] = pd.to_datetime(processed_df['date'], errors='coerce')
        processed_df['amount'] = pd.to_numeric(processed_df['amount'], errors='coerce')
        processed_df['budget_amount'] = pd.to_numeric(processed_df['budget_amount'], errors='coerce')
    except Exception as e:
        raise ValueError(f"Error converting column types: {e}")

    # Handling missing values
    # Drop rows where 'date' is NaN (as it's a critical identifier)
    processed_df.dropna(subset=['date'], inplace=True)
    # For amounts, fill NaN with 0, assuming missing values mean no revenue/budget
    processed_df['amount'].fillna(0, inplace=True)
    processed_df['budget_amount'].fillna(0, inplace=True)
    # For categorical columns, fill with 'Unknown'
    if 'revenue_source' in processed_df.columns:
        processed_df['revenue_source'].fillna('Unknown', inplace=True)
    if 'category' in processed_df.columns:
        processed_df['category'].fillna('Unknown', inplace=True)

    # Creation of derived columns
    processed_df['year'] = processed_df['date'].dt.year
    processed_df['month'] = processed_df['date'].dt.month

    return processed_df

def get_budget_overview(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcule les indicateurs clés pour la transparence budgétaire.

    Args:
        df (pd.DataFrame): Le DataFrame de données financières prétraitées.

    Returns:
        Dict[str, Any]: Un dictionnaire contenant les métriques d'aperçu budgétaire.
    """
    total_budget = df['budget_amount'].sum()
    total_actual_revenue = df['amount'].sum()
    variance = total_actual_revenue - total_budget

    variance_percentage = 0.0
    if total_budget != 0:
        variance_percentage = (variance / total_budget) * 100

    return {
        "total_budget": round(total_budget, 2),
        "total_actual_revenue": round(total_actual_revenue, 2),
        "budget_variance": round(variance, 2),
        "budget_variance_percentage": round(variance_percentage, 2)
    }

def get_revenue_breakdown(df: pd.DataFrame, group_by_columns: List[str]) -> List[Dict[str, Any]]:
    """
    Fournit le détail des recettes regroupées selon une ou plusieurs colonnes spécifiées.

    Args:
        df (pd.DataFrame): Le DataFrame de données financières prétraitées.
        group_by_columns (List[str]): Liste des noms de colonnes par lesquelles regrouper les recettes.

    Returns:
        List[Dict[str, Any]]: Une liste de dictionnaires, où chaque dictionnaire représente un groupe
                              avec le total des recettes et les critères de regroupement.
    """
    for col in group_by_columns:
        if col not in df.columns:
            raise ValueError(f"Grouping column '{col}' not found in the DataFrame. Available columns: {df.columns.tolist()}")

    # Group by the specified columns and sum the 'amount'
    breakdown = df.groupby(group_by_columns)['amount'].sum().reset_index()
    
    # Convert amounts to rounded floats for cleaner output
    breakdown['amount'] = breakdown['amount'].round(2)

    return breakdown.to_dict(orient='records')

def generate_financial_report(source_type: str, source_path: str, **kwargs) -> Dict[str, Any]:
    """
    Fonction principale qui orchestre l'ensemble du processus de génération du rapport financier complet.

    Args:
        source_type (str): Type de la source de données.
        source_path (str): Chemin d'accès ou chaîne de connexion.
        **kwargs: Paramètres pour personnaliser le rapport, tels que les colonnes à utiliser pour les regroupements
                  (e.g., 'breakdown_by_sources_columns', 'breakdown_by_periods_columns', 'db_connection_params').

    Returns:
        Dict[str, Any]: Un dictionnaire structuré contenant l'ensemble du rapport financier.
    """
    report: Dict[str, Any] = {
        "status": "success",
        "message": "Financial report generated successfully.",
        "report_data": {}
    }

    try:
        # 1. Load data
        db_con = kwargs.pop('db_connection_params', None)
        load_kwargs = {k: v for k, v in kwargs.items() if k not in ['breakdown_by_sources_columns', 'breakdown_by_periods_columns']}
        if source_type == 'database' and db_con is not None:
             load_kwargs['con'] = db_con

        raw_df = load_financial_data(source_type, source_path, **load_kwargs)

        if raw_df.empty:
            report["status"] = "warning"
            report["message"] = "No data loaded. Report generation aborted."
            return report

        # 2. Preprocess data
        processed_df = _preprocess_financial_data(raw_df)

        if processed_df.empty:
            report["status"] = "warning"
            report["message"] = "No valid data after preprocessing. Report generation aborted."
            return report

        # 3. Get Budget Overview
        report["report_data"]["budget_overview"] = get_budget_overview(processed_df)

        # 4. Get Revenue Breakdown by Source
        breakdown_by_sources_cols = kwargs.get('breakdown_by_sources_columns', ['revenue_source'])
        if all(col in processed_df.columns for col in breakdown_by_sources_cols):
            report["report_data"]["revenue_by_source"] = get_revenue_breakdown(processed_df, breakdown_by_sources_cols)
        else:
            report["report_data"]["revenue_by_source"] = "N/A - Required columns for source breakdown are missing."
            report["status"] = "warning"
            report["message"] = "Report generated with partial data due to missing columns for source breakdown."


        # 5. Get Revenue Breakdown by Period (e.g., year, month)
        breakdown_by_periods_cols = kwargs.get('breakdown_by_periods_columns', ['year', 'month'])
        if all(col in processed_df.columns for col in breakdown_by_periods_cols):
            report["report_data"]["revenue_by_period"] = get_revenue_breakdown(processed_df, breakdown_by_periods_cols)
        else:
            report["report_data"]["revenue_by_period"] = "N/A - Required columns for period breakdown are missing."
            report["status"] = "warning"
            report["message"] = "Report generated with partial data due to missing columns for period breakdown."

    except (ValueError, IOError, Exception) as e:
        report["status"] = "error"
        report["message"] = f"Failed to generate financial report: {e}"
        report["report_data"] = {} # Clear any partial data on error

    return report

# Example Usage (for testing purposes, not part of the required output)
if __name__ == '__main__':
    # Create a dummy CSV file for demonstration
    dummy_csv_content = """transaction_date,revenue_source,revenue_amount,budget_amount,category
2023-01-01,Sales,1000.00,900.00,Food
2023-01-05,Sales,1200.50,1100.00,Drinks
2023-01-10,Marketing,500.00,600.00,Advertising
2023-01-15,Sales,800.00,850.00,Food
2023-02-01,Sales,1500.00,1400.00,Drinks
2023-02-10,Marketing,700.00,750.00,Promotions
2023-02-15,Sales,950.00,900.00,Food
2023-03-01,Sales,1100.00,1000.00,Drinks
2023-03-05,Marketing,600.00,650.00,Advertising
2023-03-10,Other,200.00,150.00,Misc
"""
    with open("dummy_financial_data.csv", "w") as f:
        f.write(dummy_csv_content)

    print("--- Generating Report from CSV ---")
    report_csv = generate_financial_report(
        source_type="csv",
        source_path="dummy_financial_data.csv",
        breakdown_by_sources_columns=['revenue_source'],
        breakdown_by_periods_columns=['year', 'month']
    )
    print(json.dumps(report_csv, indent=4))

    print("\n--- Generating Report with different breakdown columns (e.g., category) ---")
    report_category = generate_financial_report(
        source_type="csv",
        source_path="dummy_financial_data.csv",
        breakdown_by_sources_columns=['category'], # Group by category
        breakdown_by_periods_columns=['year', 'month']
    )
    print(json.dumps(report_category, indent=4))

    # Example of error handling (non-existent file)
    print("\n--- Generating Report with non-existent file (expecting error) ---")
    error_report = generate_financial_report(
        source_type="csv",
        source_path="non_existent_file.csv"
    )
    print(json.dumps(error_report, indent=4))

    # Example of error handling (missing column for breakdown)
    print("\n--- Generating Report with missing breakdown column (expecting warning) ---")
    report_missing_col = generate_financial_report(
        source_type="csv",
        source_path="dummy_financial_data.csv",
        breakdown_by_sources_columns=['non_existent_column'],
        breakdown_by_periods_columns=['year', 'month']
    )
    print(json.dumps(report_missing_col, indent=4))

    # Clean up dummy file
    import os
    os.remove("dummy_financial_data.csv")