import os
import json
import re
from dotenv import load_dotenv
from google import genai

def selectionner_projet():
    """Affiche un menu interactif pour choisir le projet cible."""
    print("\n==============================================")
    print(" 🗄️ AGENT BÂTISSEUR - GÉNÉRATION SQL EXPERTE")
    print("==============================================\n")
    
    dossiers = [d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".")]
    
    if not dossiers:
        print("❌ Aucun dossier de projet trouvé.")
        exit()
        
    for i, dossier in enumerate(dossiers, 1):
        print(f"[{i}] {dossier}")
        
    choix = input("\n👉 Pour quel projet veux-tu générer le schéma SQL ? (Tape le numéro) : ")
    
    try:
        index = int(choix) - 1
        return dossiers[index]
    except:
        print("❌ Choix invalide.")
        exit()

def executer_database():
    projet = selectionner_projet()
    
    load_dotenv(dotenv_path=".env")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("❌ Erreur : GEMINI_API_KEY introuvable.")
        exit()

    chemin_das = os.path.join(projet, "2-readytobuild", "DAS_architecture.json")
    try:
        with open(chemin_das, "r", encoding="utf-8") as f:
            das_content = json.load(f)
    except Exception as e:
        print(f"❌ Impossible de lire le fichier DAS : {e}. Lance d'abord l'Architecte !")
        exit()

    print("🧠 L'Agent DBA rédige le script PostgreSQL de niveau production...")
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Tu es un Administrateur de Base de Données (DBA) Expert sur PostgreSQL et Supabase.
    Voici l'architecture (DAS) demandée par le CTO :
    {json.dumps(das_content, indent=2)}
    
    Mission :
    Rédige le script SQL complet pour créer ces tables de manière robuste.
    
    Règles de production strictes :
    1. Ajoute `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";` au début.
    2. Utilise `CREATE TABLE IF NOT EXISTS`.
    3. Les clés primaires (id) DOIVENT être de type `UUID PRIMARY KEY DEFAULT uuid_generate_v4()`.
    4. Gère les clés étrangères avec `ON DELETE CASCADE` si pertinent.
    5. Convertis les indications d'ENUM du DAS en contraintes `CHECK` (ex: `status VARCHAR CHECK (status IN ('actif', 'en_attente'))`).
    6. Ajoute les colonnes d'audit obligatoires : 
       `created_at TIMESTAMPTZ DEFAULT NOW()`
       `updated_at TIMESTAMPTZ DEFAULT NOW()`
    
    Retourne UNIQUEMENT le code SQL pur, sans blabla avant ni après, et sans les balises markdown (```sql).
    """

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt
        )
        # Nettoyage des éventuelles balises markdown
        sql_brut = response.text.replace("```sql", "").replace("```", "").strip()
    except Exception as e:
        print(f"❌ Erreur lors de la génération SQL : {e}")
        exit()

    # Sauvegarde du fichier .sql
    dossier_build = os.path.join(projet, "2-readytobuild")
    chemin_sql = os.path.join(dossier_build, "schema.sql")
    
    try:
        with open(chemin_sql, "w", encoding="utf-8") as f:
            f.write(sql_brut)
        print(f"\n✅ Script SQL généré avec succès dans : {chemin_sql}")
        print("💡 Pour appliquer ces fondations :")
        print("   1. Ouvre ce fichier schema.sql dans VS Code.")
        print("   2. Copie tout son contenu.")
        print("   3. Colle-le dans l'onglet 'SQL Editor' de ton dashboard Supabase, et clique sur 'Run'.")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde : {e}")

if __name__ == "__main__":
    executer_database()