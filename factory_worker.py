import os
import json
import re
from dotenv import load_dotenv
from google import genai
from supabase import create_client, Client

def selectionner_projet():
    print("\n==============================================")
    print(" 🧑‍🏭 AGENT WORKER - INJECTION DE DONNÉES EXPERTES")
    print("==============================================\n")
    
    dossiers = [d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".")]
    if not dossiers:
        print("❌ Aucun dossier de projet trouvé.")
        exit()
        
    for i, dossier in enumerate(dossiers, 1):
        print(f"[{i}] {dossier}")
        
    choix = input("\n👉 Pour quel projet veux-tu générer des données de test ? (Tape le numéro) : ")
    
    try:
        index = int(choix) - 1
        return dossiers[index]
    except:
        print("❌ Choix invalide.")
        exit()

def executer_worker():
    projet = selectionner_projet()
    
    load_dotenv(dotenv_path=".env")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    chemin_env = os.path.join(projet, "2-readytobuild", ".env")
    load_dotenv(dotenv_path=chemin_env, override=True)
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not all([GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        print("❌ Erreur : Il manque des clés dans tes fichiers .env.")
        exit()

    print("🔌 Connexion à Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    chemin_das = os.path.join(projet, "2-readytobuild", "DAS_architecture.json")
    try:
        with open(chemin_das, "r", encoding="utf-8") as f:
            das_content = json.load(f)
    except Exception as e:
        print(f"❌ Impossible de lire le DAS : {e}")
        exit()

    print("🧠 L'Agent QA génère un jeu de données (Happy Path + Edge Cases)...")
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Tu es un Ingénieur QA (Assurance Qualité) et Data Engineer.
    Voici l'architecture et l'analyse du CTO pour le projet :
    {json.dumps(das_content, indent=2)}
    
    Mission :
    Génère 3 à 4 enregistrements de test réalistes pour CHAQUE table.
    
    Règles de génération strictes :
    1. Inclus un mix de cas nominaux ("Happy Path") et de cas limites ("Edge Cases") identifiés dans l'analyse de l'architecte (ex: statuts suspendus, valeurs inattendues mais gérées).
    2. Respecte scrupuleusement les contraintes ENUM / CHECK définies dans les colonnes.
    3. Fais correspondre parfaitement les clés étrangères (UUID) entre les tables liées.
    4. Utilise des formats UUID valides pour toutes les clés ID (ex: "550e8400-e29b-41d4-a716-446655440000").
    
    Retourne UNIQUEMENT un objet JSON dont les clés sont les noms exacts des tables (database_schema -> table_name), et les valeurs sont des tableaux contenant les objets à insérer.
    N'ajoute aucun texte avant ou après le JSON.
    """

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt
        )
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not match:
             print("❌ L'IA n'a pas généré de structure valide.")
             exit()
             
        data_brute = match.group(0)
        records = json.loads(data_brute)
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération des données : {e}")
        exit()

    print("🚀 Injection des données expertes dans les tables...")
    for nom_table, lignes in records.items():
        try:
            supabase.table(nom_table).insert(lignes).execute()
            print(f"✅ {len(lignes)} ligne(s) insérée(s) dans '{nom_table}'")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'insertion dans '{nom_table}' : {e}")

    print("\n🏁 [AGENT WORKER] Mission terminée. Ta base est prête pour les crash tests !")

if __name__ == "__main__":
    executer_worker()