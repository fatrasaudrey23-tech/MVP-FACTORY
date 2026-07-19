import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
import json
import os
import typing

def load_budget_data(source_path: str, data_format: str = 'csv') -> pd.DataFrame:
    """
    Charge les données budgétaires depuis une source spécifiée.

    Paramètres :
        source_path (str) : Le chemin d'accès au fichier de données (ex: CSV, Excel).
        data_format (str) : Le format du fichier de données ('csv', 'excel', 'json'). Par défaut 'csv'.

    Retourne :
        pd.DataFrame : Contenant les données brutes.
    """
    try:
        if data_format == 'csv':
            df = pd.read_csv(source_path)
        elif data_format == 'excel':
            df = pd.read_excel(source_path)
        elif data_format == 'json':
            df = pd.read_json(source_path)
        else:
            raise ValueError(f"Format de données non supporté : {data_format}. Choisissez parmi 'csv', 'excel', 'json'.")
        print(f"Données chargées avec succès depuis {source_path} ({data_format}).")
        return df
    except FileNotFoundError:
        print(f"Erreur : Le fichier {source_path} est introuvable.")
        raise
    except ValueError as ve:
        print(f"Erreur lors de la lecture du fichier : {ve}")
        raise
    except Exception as e:
        print(f"Une erreur inattendue est survenue lors du chargement des données : {e}")
        raise

def preprocess_budget_data(df: pd.DataFrame, date_col: str, amount_cols: typing.List[str]) -> pd.DataFrame:
    """
    Nettoie, transforme et enrichit les données budgétaires brutes pour l'analyse.

    Paramètres :
        df (pd.DataFrame) : Le DataFrame des données budgétaires brutes.
        date_col (str) : Le nom de la colonne contenant les dates.
        amount_cols (list[str]) : Liste des noms de colonnes contenant les montants (ex: ['Planned Amount', 'Actual Amount']).

    Retourne :
        pd.DataFrame : Avec les données prétraitées et enrichies.
    """
    df_processed = df.copy()

    # Convertir la colonne de date
    try:
        df_processed[date_col] = pd.to_datetime(df_processed[date_col])
    except KeyError:
        print(f"Erreur : La colonne de date '{date_col}' est introuvable dans le DataFrame.")
        raise
    except Exception as e:
        print(f"Erreur lors de la conversion de la colonne '{date_col}' en datetime : {e}")
        raise

    # Assurer que les colonnes de montants sont numériques et gérer les NaNs
    for col in amount_cols:
        if col not in df_processed.columns:
            print(f"Attention : La colonne de montant '{col}' est introuvable. Elle sera ignorée ou pourrait causer des erreurs.")
            continue
        df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce').fillna(0)
    
    planned_col = amount_cols[0] if amount_cols else None
    actual_col = amount_cols[1] if len(amount_cols) > 1 else None

    if planned_col and actual_col and planned_col in df_processed.columns and actual_col in df_processed.columns:
        # Calculer la colonne 'Difference'
        df_processed['Difference'] = df_processed[actual_col] - df_processed[planned_col]

        # Calculer la colonne 'Percentage_Difference'
        # Gérer la division par zéro: si planned_amount est 0, percentage_difference est 0
        df_processed['Percentage_Difference'] = df_processed.apply(
            lambda row: (row['Difference'] / row[planned_col]) * 100 if row[planned_col] != 0 else 0,
            axis=1
        )
    else:
        print("Attention : Les colonnes planifiées et/ou réelles ne sont pas disponibles pour calculer la 'Difference' et la 'Percentage_Difference'.")

    # Extraire des informations temporelles
    if date_col in df_processed.columns:
        df_processed['Year'] = df_processed[date_col].dt.year
        df_processed['Month'] = df_processed[date_col].dt.month_name()
        df_processed['Quarter'] = df_processed[date_col].dt.quarter
    
    print("Données prétraitées et enrichies avec succès.")
    return df_processed

def analyze_budget_data(df: pd.DataFrame, category_col: str, planned_col: str, actual_col: str) -> typing.Dict[str, typing.Any]:
    """
    Effectue des agrégations et des calculs clés pour extraire des informations budgétaires pour la transparence.

    Paramètres :
        df (pd.DataFrame) : Le DataFrame des données budgétaires prétraitées.
        category_col (str) : Le nom de la colonne des catégories (ex: 'Category').
        planned_col (str) : Le nom de la colonne du montant planifié.
        actual_col (str) : Le nom de la colonne du montant réel.

    Retourne :
        dict : Contenant des statistiques résumées et des agrégations clés.
    """
    analysis_results = {}

    if not all(col in df.columns for col in [planned_col, actual_col, 'Difference', 'Percentage_Difference']):
        print("Erreur : Le DataFrame ne contient pas toutes les colonnes requises pour l'analyse (Planned, Actual, Difference, Percentage_Difference).")
        return analysis_results

    # Totaux globaux
    total_planned = df[planned_col].sum()
    total_actual = df[actual_col].sum()
    total_difference = df['Difference'].sum()
    
    global_pct_difference = (total_difference / total_planned) * 100 if total_planned != 0 else 0

    analysis_results['global_summary'] = {
        'total_planned': total_planned,
        'total_actual': total_actual,
        'total_difference': total_difference,
        'global_percentage_difference': global_pct_difference
    }

    # Agrégation par catégorie
    if category_col in df.columns:
        category_breakdown = df.groupby(category_col).agg(
            planned_amount=(planned_col, 'sum'),
            actual_amount=(actual_col, 'sum'),
            difference=('Difference', 'sum')
        )
        category_breakdown['percentage_difference'] = category_breakdown.apply(
            lambda row: (row['difference'] / row['planned_amount']) * 100 if row['planned_amount'] != 0 else 0,
            axis=1
        )
        analysis_results['category_breakdown'] = category_breakdown.to_dict('index')

        # Catégories avec les plus grands écarts
        top_overspenders = category_breakdown.sort_values(by='difference', ascending=False).head(5)
        top_savers = category_breakdown.sort_values(by='difference', ascending=True).head(5)
        analysis_results['top_deviations'] = {
            'overspenders': top_overspenders.to_dict('index'),
            'savers': top_savers.to_dict('index')
        }
    else:
        print(f"Attention : La colonne de catégorie '{category_col}' est introuvable. L'analyse par catégorie sera omise.")

    # Agrégation par période (mensuelle)
    if 'Year' in df.columns and 'Month' in df.columns:
        monthly_trends = df.groupby(['Year', 'Month']).agg(
            planned_amount=(planned_col, 'sum'),
            actual_amount=(actual_col, 'sum'),
            difference=('Difference', 'sum')
        ).reset_index()
        # Ensure Month is ordered correctly for plotting
        month_order = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        monthly_trends['Month'] = pd.Categorical(monthly_trends['Month'], categories=month_order, ordered=True)
        monthly_trends = monthly_trends.sort_values(by=['Year', 'Month'])
        
        analysis_results['monthly_trends'] = monthly_trends.to_dict('records')
    else:
        print("Attention : Les colonnes 'Year' et 'Month' sont introuvables. L'analyse des tendances mensuelles sera omise.")

    print("Analyse des données budgétaires terminée.")
    return analysis_results

def generate_budget_visualization(df: pd.DataFrame, analysis_results: typing.Dict[str, typing.Any], viz_type: str, output_dir: str = 'output_visualizations', 
                                  planned_col: str = 'Planned Amount', actual_col: str = 'Actual Amount', category_col: str = 'Category') -> None:
    """
    Génère et sauvegarde diverses visualisations des données budgétaires pour assurer la transparence.

    Paramètres :
        df (pd.DataFrame) : Le DataFrame des données budgétaires prétraitées (pour les visualisations détaillées).
        analysis_results (dict) : Les résultats de l'analyse (`analyze_budget_data`) pour les visualisations de synthèse.
        viz_type (str) : Le type de visualisation à générer (ex: 'category_comparison', 'monthly_trend', 'deviation_pie').
        output_dir (str) : Le répertoire où sauvegarder les graphiques. Crée le répertoire s'il n'existe pas.
        planned_col (str) : Le nom de la colonne du montant planifié.
        actual_col (str) : Le nom de la colonne du montant réel.
        category_col (str) : Le nom de la colonne des catégories.

    Retourne :
        None.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Répertoire de sortie '{output_dir}' créé.")

    plt.style.use('seaborn-v0_8-darkgrid') # Use a consistent style

    if viz_type == 'category_comparison':
        if category_col not in df.columns or planned_col not in df.columns or actual_col not in df.columns:
            print(f"Impossible de générer '{viz_type}': colonnes requises manquantes.")
            return

        category_data = df.groupby(category_col)[[planned_col, actual_col]].sum().reset_index()
        category_data_melted = category_data.melt(id_vars=category_col, var_name='Type', value_name='Amount')

        plt.figure(figsize=(12, 7))
        sns.barplot(x=category_col, y='Amount', hue='Type', data=category_data_melted, palette='viridis')
        plt.title('Comparaison du budget planifié et réel par catégorie', fontsize=16)
        plt.xlabel('Catégorie', fontsize=12)
        plt.ylabel('Montant (€)', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.legend(title='Type de Dépense')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'category_comparison.png'))
        plt.close()
        print(f"Visualisation 'category_comparison.png' générée.")

    elif viz_type == 'monthly_trend':
        if 'monthly_trends' not in analysis_results:
            print(f"Impossible de générer '{viz_type}': données mensuelles manquantes dans les résultats d'analyse.")
            return
        
        monthly_df = pd.DataFrame(analysis_results['monthly_trends'])
        if monthly_df.empty:
            print(f"Impossible de générer '{viz_type}': DataFrame des tendances mensuelles est vide.")
            return

        # Reconstruct full date for proper plotting if necessary, or ensure 'Month' is ordered
        monthly_df['Month_Num'] = pd.to_datetime(monthly_df['Month'], format='%B').dt.month
        monthly_df['Year_Month'] = monthly_df['Year'].astype(str) + '-' + monthly_df['Month_Num'].astype(str).str.zfill(2)
        monthly_df = monthly_df.sort_values(by='Year_Month')

        plt.figure(figsize=(14, 7))
        sns.lineplot(x='Year_Month', y='planned_amount', data=monthly_df, marker='o', label='Planifié', color='blue')
        sns.lineplot(x='Year_Month', y='actual_amount', data=monthly_df, marker='o', label='Réel', color='red')
        plt.title('Tendance mensuelle des dépenses planifiées vs. réelles', fontsize=16)
        plt.xlabel('Mois', fontsize=12)
        plt.ylabel('Montant (€)', fontsize=12)
        plt.xticks(rotation=60, ha='right')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'monthly_trend.png'))
        plt.close()
        print(f"Visualisation 'monthly_trend.png' générée.")

    elif viz_type == 'deviation_breakdown':
        if 'category_breakdown' not in analysis_results:
            print(f"Impossible de générer '{viz_type}': données par catégorie manquantes dans les résultats d'analyse.")
            return

        deviation_df = pd.DataFrame.from_dict(analysis_results['category_breakdown'], orient='index')
        deviation_df = deviation_df.reset_index().rename(columns={'index': category_col})
        
        if deviation_df.empty:
            print(f"Impossible de générer '{viz_type}': DataFrame des écarts par catégorie est vide.")
            return

        plt.figure(figsize=(12, 7))
        sns.barplot(x=category_col, y='difference', data=deviation_df.sort_values(by='difference', ascending=False), palette='coolwarm')
        plt.title('Écarts (Réel - Planifié) par Catégorie', fontsize=16)
        plt.xlabel('Catégorie', fontsize=12)
        plt.ylabel('Différence (€)', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.axhline(0, color='grey', linestyle='--')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'deviation_breakdown.png'))
        plt.close()
        print(f"Visualisation 'deviation_breakdown.png' générée.")

    elif viz_type == 'overall_distribution':
        if category_col not in df.columns or actual_col not in df.columns:
            print(f"Impossible de générer '{viz_type}': colonnes requises manquantes.")
            return

        actual_spending_by_category = df.groupby(category_col)[actual_col].sum()
        
        if actual_spending_by_category.empty or actual_spending_by_category.sum() == 0:
            print(f"Impossible de générer '{viz_type}': Aucune dépense réelle ou total zéro à distribuer.")
            return

        plt.figure(figsize=(10, 10))
        plt.pie(actual_spending_by_category, labels=actual_spending_by_category.index, autopct='%1.1f%%', startangle=90, wedgeprops={'edgecolor': 'black'})
        plt.title('Distribution des dépenses réelles par catégorie', fontsize=16)
        plt.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'overall_distribution.png'))
        plt.close()
        print(f"Visualisation 'overall_distribution.png' générée.")

    else:
        print(f"Type de visualisation '{viz_type}' non reconnu. Aucune visualisation générée pour ce type.")

def main(config_path: str = 'config.json') -> None:
    """
    Fonction principale qui orchestre le flux de travail complet : chargement, prétraitement, analyse et visualisation.

    Paramètres :
        config_path (str) : Le chemin vers un fichier de configuration (JSON) contenant les paramètres.

    Retourne :
        None.
    """
    print("Démarrage de l'analyseur de budget...")
    config = {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Configuration chargée depuis {config_path}.")
    except FileNotFoundError:
        print(f"Erreur : Le fichier de configuration '{config_path}' est introuvable. Veuillez le créer.")
        return
    except json.JSONDecodeError:
        print(f"Erreur : Le fichier de configuration '{config_path}' n'est pas un JSON valide.")
        return
    except Exception as e:
        print(f"Une erreur inattendue est survenue lors du chargement de la configuration : {e}")
        return

    # Extraire les paramètres de la configuration
    data_source = config.get('data_source')
    data_format = config.get('data_format', 'csv')
    date_column = config.get('date_column')
    planned_amount_column = config.get('planned_amount_column')
    actual_amount_column = config.get('actual_amount_column')
    category_column = config.get('category_column')
    visualizations_to_generate = config.get('visualizations_to_generate', [])
    output_directory = config.get('output_directory', 'budget_reports')

    if not all([data_source, date_column, planned_amount_column, actual_amount_column, category_column]):
        print("Erreur : Les paramètres essentiels (data_source, date_column, planned_amount_column, actual_amount_column, category_column) sont manquants dans la configuration.")
        return

    df = pd.DataFrame()
    try:
        df = load_budget_data(data_source, data_format)
    except Exception:
        print("Échec de l'étape de chargement des données. Arrêt du programme.")
        return

    df_processed = pd.DataFrame()
    try:
        df_processed = preprocess_budget_data(df, date_column, [planned_amount_column, actual_amount_column])
    except Exception:
        print("Échec de l'étape de prétraitement des données. Arrêt du programme.")
        return

    analysis_results = {}
    try:
        analysis_results = analyze_budget_data(df_processed, category_column, planned_amount_column, actual_amount_column)
        print("Résultats de l'analyse :")
        for key, value in analysis_results.items():
            print(f"  {key}: {value}")
    except Exception:
        print("Échec de l'étape d'analyse des données. Arrêt du programme.")
        return

    try:
        if not visualizations_to_generate:
            print("Aucun type de visualisation spécifié dans la configuration. Aucune visualisation ne sera générée.")
        else:
            for viz_type in visualizations_to_generate:
                generate_budget_visualization(df_processed, analysis_results, viz_type, output_directory,
                                            planned_amount_column, actual_amount_column, category_column)
    except Exception as e:
        print(f"Une erreur est survenue lors de la génération des visualisations : {e}")
        # Continue pour permettre à d'autres visualisations de se générer si possible.

    print("Analyse du budget terminée avec succès.")

if __name__ == '__main__':
    # Exemple de création d'un fichier de configuration et de données pour le test
    # Ceci est juste pour rendre le script exécutable directement pour la démonstration
    # Dans un cas réel, ces fichiers existeraient déjà.
    
    # Création d'un fichier config.json
    sample_config = {
        "data_source": "budget_data.csv",
        "data_format": "csv",
        "date_column": "Date",
        "planned_amount_column": "Planned Amount",
        "actual_amount_column": "Actual Amount",
        "category_column": "Category",
        "visualizations_to_generate": [
            "category_comparison",
            "monthly_trend",
            "deviation_breakdown",
            "overall_distribution"
        ],
        "output_directory": "budget_reports"
    }
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=4)

    # Création d'un fichier budget_data.csv
    sample_data = {
        'Date': pd.to_datetime(['2023-01-15', '2023-01-20', '2023-02-10', '2023-02-25', '2023-03-05', '2023-03-18', '2023-04-01', '2023-04-10']),
        'Category': ['Food', 'Transport', 'Food', 'Rent', 'Utilities', 'Food', 'Transport', 'Food'],
        'Planned Amount': [300, 100, 350, 1000, 150, 300, 120, 320],
        'Actual Amount': [320, 90, 340, 1000, 160, 280, 130, 310]
    }
    sample_df = pd.DataFrame(sample_data)
    sample_df.to_csv('budget_data.csv', index=False)
    
    # Exécution de la fonction main
    main()