import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

print("⚙️ Démarrage de l'Agent DevOps - Validation et Génération Sécurisée...")

if not supabase_url or not supabase_key:
    print("❌ Erreur : Les clés SUPABASE_URL ou SUPABASE_KEY sont manquantes dans le fichier .env.")
    exit(1)

def lire_architecture(chemin_das="DAS_architecture.json"):
    try:
        with open(chemin_das, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Erreur : Le plan de l'architecte '{chemin_das}' est introuvable.")
        return None

def mapper_type_sql(type_json):
    types_map = {
        "UUID": "UUID",
        "VARCHAR": "VARCHAR(255)",
        "TEXT": "TEXT",
        "INTEGER": "INTEGER",
        "FLOAT": "NUMERIC(10, 2)",
        "BOOLEAN": "BOOLEAN DEFAULT FALSE",
        "TIMESTAMP": "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
    }
    return types_map.get(type_json.upper(), "VARCHAR(255)")

def generer_script_sql(das, nom_fichier_sql="init_database.sql"):
    """Génère un fichier SQL avec sécurité absolue contre les doubles clés primaires."""
    sql_content = "-- 🚀 SCRIPT D'INITIALISATION AUTOMATIQUE SECURED\n"
    sql_content += "-- Généré et corrigé par l'Agent DevOps de la MVP Factory\n\n"
    
    for table in das['database_schema']:
        nom_table = table['table_name']
        sql_content += f"-- Table : {table.get('description', '')}\n"
        sql_content += f"CREATE TABLE IF NOT EXISTS public.{nom_table} (\n"
        
        colonnes_sql = []
        for col in table['columns']:
            nom_col = col['name'].lower()
            
            # FORCE DE MANIÈRE STRICTE : Seule la colonne nommée 'id' a le droit d'être la PRIMARY KEY
            if nom_col == "id":
                col_def = f"    id UUID PRIMARY KEY DEFAULT gen_random_uuid()"
            else:
                # Toutes les autres colonnes prennent leur type normal traduit
                col_def = f"    {col['name']} {mapper_type_sql(col['type'])}"
                
                # Si c'est une relation (clé étrangère), on applique la syntaxe PostgreSQL certifiée
                if col.get('foreign_key_to'):
                    cible = col['foreign_key_to']
                    col_def += f" REFERENCES public.{cible}(id) ON DELETE CASCADE"
            
            colonnes_sql.append(col_def)
            
        sql_content += ",\n".join(colonnes_sql)
        sql_content += "\n);\n\n"
        sql_content += f"ALTER TABLE public.{nom_table} ENABLE ROW LEVEL SECURITY;\n\n"

    with open(nom_fichier_sql, "w", encoding="utf-8") as f:
        f.write(sql_content)
    print(f"💾 [SQL SÉCURISÉ] Le script a été réécrit avec succès : {nom_fichier_sql}")

def executer_provisioning():
    das = lire_architecture()
    if not das:
        return

    print(f"🐳 Connexion établie avec l'instance Supabase : {supabase_url}")
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    infra_ok = True
    tables_manquantes = False
    
    for table in das['database_schema']:
        nom_table = table['table_name']
        url_test = f"{supabase_url}/rest/v1/{nom_table}?limit=1"
        
        try:
            response = requests.get(url_test, headers=headers)
            if response.status_code in [200, 201, 204, 406]:
                print(f"  🔹 Table '{nom_table}' : Détectée / Prête.")
            elif response.status_code == 404:
                print(f"  ⚠️ Table '{nom_table}' : Non initialisée sur Supabase.")
                infra_ok = False
                tables_manquantes = True
            else:
                print(f"  ❌ Table '{nom_table}' : Erreur (Code {response.status_code}).")
                infra_ok = False
        except Exception as e:
            print(f"  ❌ Échec de connexion : {e}")
            infra_ok = False

    # Le script génère ou régénère TOUJOURS le SQL mis à jour pour correspondre aux corrections
    generer_script_sql(das)

    if infra_ok:
        print("\n🚀 [FEU VERT] L'infrastructure Supabase est parfaitement alignée avec le plan de l'Architecte !")
    else:
        print("\n🛑 [BLOCAGE] L'infrastructure n'est pas prête. Injecte le script SQL généré et sécurisé dans ton tableau de bord Supabase.")

if __name__ == "__main__":
    executer_provisioning()