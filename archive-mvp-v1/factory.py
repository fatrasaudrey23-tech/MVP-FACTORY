import os
import json
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build as build_drive
from google import genai
from jira import JIRA

# =====================================================================
# 1. INITIALISATION ET CONFIGURATION
# =====================================================================
# Chargement du coffre-fort .env
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")
JIRA_URL = os.environ.get("JIRA_URL")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN")

# Sécurité : Vérification que rien ne manque dans le .env
if not all([GEMINI_API_KEY, DRIVE_FOLDER_ID, JIRA_URL, JIRA_EMAIL, JIRA_TOKEN]):
    print("❌ Erreur : Configuration incomplète. Vérifie ton fichier .env !")
    exit()

# La clé de ton projet Jira validée
PROJECT_KEY = "ECOMENU"

# =====================================================================
# 2. CONNECTEUR GOOGLE DRIVE : ASPIRATION DU PRD
# =====================================================================
print("🔌 Réveil du robot et connexion à Google Drive...")
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

try:
    creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    drive_service = build_drive('drive', 'v3', credentials=creds)
except Exception as e:
    print(f"❌ Erreur d'accès au fichier credentials.json : {e}")
    exit()

print("🔍 Recherche du PRD actif dans le dossier de construction...")
# Requête pour cibler un fichier non supprimé commençant par 'PRD_' dans ton dossier spécifié
query = f"'{DRIVE_FOLDER_ID}' in parents and name contains 'PRD_' and trashed = false"
results = drive_service.files().list(q=query, fields="files(id, name)").execute()
files = results.get('files', [])

if not files:
    print("❌ Aucun document commencé par 'PRD_' trouvé dans ton dossier '02_Ready_To_Build'. L'usine s'arrête.")
    exit()

# On prend le premier document correspondant trouvé
file_id = files[0]['id']
file_name = files[0]['name']
print(f"📂 Document détecté : {file_name}")

# Téléchargement et conversion du Google Doc en texte brut
print("📥 Téléchargement et lecture des spécifications...")
request = drive_service.files().export_media(fileId=file_id, mimeType='text/plain')
prd_text = request.execute().decode('utf-8')
print("✅ Contenu du PRD extrait avec succès.")

# =====================================================================
# 3. ANALYSE ET DÉCOUPAGE PAR L'INTELLIGENCE ARTIFICIELLE
# =====================================================================
print("🧠 1. Analyse du PRD et génération du Backlog par Gemini...")
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# NOUVEAU PROMPT : Directives strictes et exhaustives pour le PO
prompt = f"""
Tu es un Business Analyst technique et Product Manager senior. 
Ta mission est d'analyser le document de spécifications (PRD) suivant et de le découper en User Stories prêtes pour le développement.

RÈGLE ABSOLUE : Tu dois être EXHAUSTIF. Ne résume pas le document et ne tronque pas le périmètre. 
Tu dois impérativement extraire et créer des User Stories pour TOUTES les strates du projet, sans exception. Tu dois obligatoirement inclure des tickets pour :
1. Le Frontend et l'Interface Utilisateur (Interface Streamlit, navigation).
2. Le Backend et le Moteur d'optimisation (Algorithme mathématique).
3. L'infrastructure et la Base de données (Intégration Supabase, sauvegarde des profils utilisateurs et des menus).
4. Les flux de données externes (Scraping ou connexion API pour lire les prix des circulaires de supermarchés).

Pour chaque User Story, fournis obligatoirement :
1. Un titre clair et fonctionnel.
2. Une description au format standard : "En tant que... Je veux... Afin de...".
3. Les critères d'acceptation détaillés sous forme de liste à puces.

Renvoie le résultat STRICTEMENT sous la forme d'un tableau JSON valide, sans aucun texte d'introduction ou de conclusion, et sans blocs de code markdown (pas de ```json), en respectant exactement cette structure :
[
  {{
    "titre": "Titre de la story",
    "description": "En tant que... Je veux... Afin de...",
    "criteres": "- Critère 1\\n- Critère 2"
  }}
]

Voici le texte du PRD à traiter :
{prd_text}
"""

try:
    # Utilisation du modèle stable validé
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    # Nettoyage de sécurité au cas où le modèle ajouterait du markdown architectural
    response_text = response.text.strip()
    if response_text.startswith("```json"):
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif response_text.startswith("```"):
        response_text = response_text.split("```")[1].split("```")[0].strip()
        
    tickets = json.loads(response_text)
    print(f"✨ Analyse réussie ! {len(tickets)} User Stories ont été structurées.")
except Exception as e:
    print(f"❌ Erreur lors de la chaîne d'analyse IA : {e}")
    exit()

# =====================================================================
# 4. CONNEXION JIRA ET INJECTION DES TICKETS
# =====================================================================
print("🚀 2. Connexion à l'instance Atlassian Jira...")
try:
    jira_client = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_TOKEN))
except Exception as e:
    print(f"❌ Impossible de s'authentifier à Jira : {e}")
    exit()

print(f"📦 3. Injection des tickets dans le projet [{PROJECT_KEY}]...")

for idx, item in enumerate(tickets, 1):
    try:
        issue_dict = {
            'project': {'key': PROJECT_KEY},
            'summary': item['titre'],
            'description': f"{item['description']}\n\n*Critères d'acceptation :*\n{item['criteres']}",
            'issuetype': {'name': 'Story'},
        }
        
        # Création effective du ticket sur ton tableau
        new_issue = jira_client.create_issue(fields=issue_dict)
        print(f"  🔹 [{idx}/{len(tickets)}] Ticket créé : {new_issue.key} ➔ {item['titre']}")
        
    except Exception as e:
        print(f"  🔺 [{idx}/{len(tickets)}] Échec de création pour '{item['titre']}' : {e}")

print("\n🎉 [TRAVAIL TERMINÉ] L'usine a fini de tourner. Ton backlog Jira est à jour et synchronisé avec ton Google Drive !")