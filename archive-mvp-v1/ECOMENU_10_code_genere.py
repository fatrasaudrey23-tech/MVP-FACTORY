import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import typing

def load_budget_data(data_source: str, data_format: str = 'csv') -> pd.DataFrame:
    """
    Charge les données budgétaires depuis une source spécifiée.

    Args:
        data_source (str): Le chemin vers le fichier de données.
        data_format (str, optional): Le format du fichier de données ('csv', 'excel'). Par défaut 'csv'.

    Returns:
        pd.DataFrame: Un DataFrame Pandas contenant les données budgétaires.

    Raises:
        FileNotFoundError: Si le fichier de données n'est pas trouvé.
        ValueError: Si le format de données n'est pas supporté.
    """
    if not os.path.exists(data_source):
        raise FileNotFoundError(f"La source de données '{data_source}' n'existe pas.")

    if data_format == 'csv':
        df = pd.read_csv(data_source)
    elif data_format == 'excel':
        df = pd.read_excel(data_source)
    else:
        raise ValueError(f"Le format de données '{data_format}' n'est pas supporté. Utilisez 'csv' ou 'excel'.")
    return df

def preprocess_budget_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prétraite le DataFrame budgétaire en convertissant les types, gérant les manquants
    et calculant les colonnes dérivées (e.g., Variance, Month, Year).

    Args:
        df (pd.DataFrame): Le DataFrame brut des données budgétaires.

    Returns:
        pd.DataFrame: Le DataFrame prétraité.
    """
    df_processed = df.copy()

    # Convertir les colonnes d'argent en numérique, gérer les erreurs
    for col in ['PlannedAmount', 'ActualAmount']:
        if col in df_processed.columns:
            df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce').fillna(0)
        else:
            df_processed[col] = 0 # Ajouter la colonne si manquante avec des zeros

    # Convertir la colonne Date en datetime, gérer les erreurs
    if 'Date' in df_processed.columns:
        df_processed['Date'] = pd.to_datetime(df_processed['Date'], errors='coerce')
        # Supprimer les lignes où la date n'a pas pu être convertie
        df_processed.dropna(subset=['Date'], inplace=True)
    else:
        # Si 'Date' n'existe pas, créer une colonne par défaut pour éviter les erreurs
        df_processed['Date'] = pd.to_datetime('today')

    # Calculer la Variance
    df_processed['Variance'] = df_processed['ActualAmount'] - df_processed['PlannedAmount']

    # Extraire le mois et l'année
    df_processed['Month'] = df_processed['Date'].dt.month
    df_processed['Year'] = df_processed['Date'].dt.year

    # S'assurer que 'Category' existe et est de type string, remplir les NaN
    if 'Category' not in df_processed.columns:
        df_processed['Category'] = 'Uncategorized'
    df_processed['Category'] = df_processed['Category'].astype(str).fillna('Uncategorized')

    return df_processed

def _filter_by_period(df: pd.DataFrame, period: str, year: typing.Optional[int], month: typing.Optional[int]) -> pd.DataFrame:
    """Helper function to filter DataFrame by period."""
    filtered_df = df.copy()
    if period == 'yearly' and year is not None:
        filtered_df = filtered_df[filtered_df['Year'] == year]
    elif period == 'monthly' and year is not None and month is not None:
        filtered_df = filtered_df[(filtered_df['Year'] == year) & (filtered_df['Month'] == month)]
    return filtered_df

def generate_category_breakdown_chart(
    df: pd.DataFrame,
    period: str = 'all',
    year: typing.Optional[int] = None,
    month: typing.Optional[int] = None,
    output_path: str = 'reports/category_breakdown.png'
) -> None:
    """
    Génère un graphique de répartition des dépenses par catégorie.

    Args:
        df (pd.DataFrame): Le DataFrame budgétaire prétraité.
        period (str, optional): La période à analyser ('monthly', 'yearly', 'all'). Par défaut 'all'.
        year (int, optional): L'année spécifique pour le filtrage.
        month (int, optional): Le mois spécifique pour le filtrage.
        output_path (str): Le chemin complet où sauvegarder le graphique.
    """
    filtered_df = _filter_by_period(df, period, year, month)
    
    category_actuals = filtered_df.groupby('Category')['ActualAmount'].sum()
    category_actuals = category_actuals[category_actuals > 0] # Filter out categories with zero spending

    if category_actuals.empty:
        print(f"Aucune donnée de dépenses réelle pour la période spécifiée ({period}, Année: {year}, Mois: {month}).")
        return

    plt.figure(figsize=(10, 8))
    plt.pie(category_actuals, labels=category_actuals.index, autopct='%1.1f%%', startangle=90, pctdistance=0.85)
    plt.title(f'Répartition des dépenses réelles par catégorie ({period.capitalize()} - {year if year else "All"} {f"Mois {month}" if month else ""})')
    plt.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Graphique de répartition par catégorie sauvegardé à : {output_path}")

def generate_actual_vs_planned_chart(
    df: pd.DataFrame,
    period: str = 'all',
    year: typing.Optional[int] = None,
    month: typing.Optional[int] = None,
    output_path: str = 'reports/actual_vs_planned.png'
) -> None:
    """
    Génère un graphique comparant les dépenses réelles aux dépenses prévues.

    Args:
        df (pd.DataFrame): Le DataFrame budgétaire prétraité.
        period (str, optional): La période à analyser ('monthly', 'yearly', 'all'). Par défaut 'all'.
        year (int, optional): L'année spécifique pour le filtrage.
        month (int, optional): Le mois spécifique pour le filtrage.
        output_path (str): Le chemin complet où sauvegarder le graphique.
    """
    filtered_df = _filter_by_period(df, period, year, month)

    summary_df = filtered_df.groupby('Category')[['PlannedAmount', 'ActualAmount']].sum().reset_index()
    summary_df = summary_df[(summary_df['PlannedAmount'] > 0) | (summary_df['ActualAmount'] > 0)]

    if summary_df.empty:
        print(f"Aucune donnée planifiée ou réelle pour la période spécifiée ({period}, Année: {year}, Mois: {month}).")
        return

    summary_melted = summary_df.melt(id_vars='Category', var_name='Type', value_name='Amount')

    plt.figure(figsize=(12, 7))
    sns.barplot(x='Category', y='Amount', hue='Type', data=summary_melted, palette={'PlannedAmount': 'skyblue', 'ActualAmount': 'lightcoral'})
    plt.title(f'Dépenses réelles vs. prévues par catégorie ({period.capitalize()} - {year if year else "All"} {f"Mois {month}" if month else ""})')
    plt.xlabel('Catégorie')
    plt.ylabel('Montant')
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='Type de Montant')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Graphique réel vs. prévu sauvegardé à : {output_path}")

def generate_spending_trend_chart(
    df: pd.DataFrame,
    category: typing.Optional[str] = None,
    output_path: str = 'reports/spending_trend.png'
) -> None:
    """
    Génère un graphique de tendance des dépenses sur le temps.

    Args:
        df (pd.DataFrame): Le DataFrame budgétaire prétraité.
        category (str, optional): La catégorie spécifique à suivre. Si None, la tendance totale.
        output_path (str): Le chemin complet où sauvegarder le graphique.
    """
    plot_df = df.copy()
    if category is not None:
        plot_df = plot_df[plot_df['Category'] == category]
        if plot_df.empty:
            print(f"Aucune donnée pour la catégorie '{category}'.")
            return

    # Aggregate by Year-Month
    plot_df['YearMonth'] = plot_df['Date'].dt.to_period('M')
    trend_data = plot_df.groupby('YearMonth')['ActualAmount'].sum().reset_index()
    trend_data['YearMonth'] = trend_data['YearMonth'].astype(str) # For plotting on x-axis

    if trend_data.empty:
        print(f"Aucune donnée de tendance pour la catégorie '{category if category else 'toutes les catégories'}'.")
        return

    plt.figure(figsize=(12, 7))
    sns.lineplot(x='YearMonth', y='ActualAmount', data=trend_data, marker='o')
    title_suffix = f"pour la catégorie '{category}'" if category else "totales"
    plt.title(f'Tendance des dépenses réelles {title_suffix} par mois')
    plt.xlabel('Mois')
    plt.ylabel('Montant Réel')
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Graphique de tendance des dépenses sauvegardé à : {output_path}")

def main_budget_visualizer(
    data_source: str,
    data_format: str = 'csv',
    output_directory: str = 'budget_reports'
) -> None:
    """
    Fonction principale pour générer les visualisations transparentes du budget.

    Args:
        data_source (str): Le chemin vers le fichier de données budgétaires.
        data_format (str, optional): Le format du fichier de données. Par défaut 'csv'.
        output_directory (str, optional): Le répertoire où les graphiques seront sauvegardés.
    """
    os.makedirs(output_directory, exist_ok=True)
    
    try:
        df_raw = load_budget_data(data_source, data_format)
    except (FileNotFoundError, ValueError) as e:
        print(f"Erreur lors du chargement des données : {e}")
        return

    df_processed = preprocess_budget_data(df_raw)

    if df_processed.empty:
        print("Le DataFrame prétraité est vide. Impossible de générer des graphiques.")
        return

    print("Génération des graphiques...")

    # Exemple de génération pour l'année la plus récente et un mois spécifique
    latest_year = df_processed['Year'].max()
    
    # Graphique de répartition par catégorie
    generate_category_breakdown_chart(
        df_processed,
        period='yearly',
        year=latest_year,
        output_path=os.path.join(output_directory, f'category_breakdown_{latest_year}.png')
    )
    generate_category_breakdown_chart(
        df_processed,
        period='all',
        output_path=os.path.join(output_directory, 'category_breakdown_all_time.png')
    )

    # Graphique réel vs prévu
    generate_actual_vs_planned_chart(
        df_processed,
        period='yearly',
        year=latest_year,
        output_path=os.path.join(output_directory, f'actual_vs_planned_{latest_year}.png')
    )
    generate_actual_vs_planned_chart(
        df_processed,
        period='all',
        output_path=os.path.join(output_directory, 'actual_vs_planned_all_time.png')
    )

    # Graphique de tendance des dépenses
    generate_spending_trend_chart(
        df_processed,
        output_path=os.path.join(output_directory, 'spending_trend_total.png')
    )

    # Exemple de tendance pour une catégorie spécifique (si présente)
    if 'Category' in df_processed.columns and not df_processed['Category'].empty:
        sample_category = df_processed['Category'].mode()[0] # Get the most frequent category
        if sample_category:
            generate_spending_trend_chart(
                df_processed,
                category=sample_category,
                output_path=os.path.join(output_directory, f'spending_trend_{sample_category.replace(" ", "_")}.png')
            )
    
    print(f"Tous les graphiques ont été générés et sauvegardés dans '{output_directory}'.")


if __name__ == '__main__':
    # Ceci est un exemple d'utilisation.
    # Pour exécuter, assurez-vous d'avoir un fichier CSV ou Excel de données budgétaires.
    # Créez un fichier CSV d'exemple si vous n'en avez pas :
    # data/my_budget_data.csv
    # Date,Category,PlannedAmount,ActualAmount
    # 2023-01-01,Groceries,300,320
    # 2023-01-05,Rent,1000,1000
    # 2023-01-10,Utilities,150,145
    # 2023-02-01,Groceries,300,280
    # 2023-02-03,Transport,50,60
    # 2023-03-01,Groceries,320,350
    # 2023-03-07,Rent,1000,1000
    # 2023-04-01,Groceries,310,300
    # 2023-04-15,Entertainment,80,95
    # 2024-01-01,Groceries,330,340
    # 2024-01-05,Rent,1050,1050
    # 2024-02-01,Groceries,330,310
    # 2024-02-10,Transport,55,65

    # Assurez-vous que le répertoire 'data' existe
    if not os.path.exists('data'):
        os.makedirs('data')

    # Création d'un fichier de données d'exemple si non existant
    example_data_path = 'data/my_budget_data.csv'
    if not os.path.exists(example_data_path):
        print(f"Création du fichier de données d'exemple : {example_data_path}")
        with open(example_data_path, 'w') as f:
            f.write("Date,Category,PlannedAmount,ActualAmount\n")
            f.write("2023-01-01,Groceries,300,320\n")
            f.write("2023-01-05,Rent,1000,1000\n")
            f.write("2023-01-10,Utilities,150,145\n")
            f.write("2023-02-01,Groceries,300,280\n")
            f.write("2023-02-03,Transport,50,60\n")
            f.write("2023-03-01,Groceries,320,350\n")
            f.write("2023-03-07,Rent,1000,1000\n")
            f.write("2023-04-01,Groceries,310,300\n")
            f.write("2023-04-15,Entertainment,80,95\n")
            f.write("2024-01-01,Groceries,330,340\n")
            f.write("2024-01-05,Rent,1050,1050\n")
            f.write("2024-02-01,Groceries,330,310\n")
            f.write("2024-02-10,Transport,55,65\n")
            f.write("2024-02-20,Entertainment,90,85\n")


    main_budget_visualizer(data_source=example_data_path, output_directory='budget_reports')
    # Pour tester avec un fichier Excel, changez data_format='excel' et le chemin du fichier.
    # main_budget_visualizer(data_source='data/my_budget_data.xlsx', data_format='excel')