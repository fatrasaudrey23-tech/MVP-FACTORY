import os
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

print("🧠 Démarrage de l'Agent PO - Organisateur de Sprints...")
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
JIRA_URL = os.environ.get("JIRA_URL")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN")
JIRA_BOARD_ID = os.environ.get("JIRA_BOARD_ID")

if not all([GEMINI_API_KEY, JIRA_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_BOARD_ID]):
    print("❌ Erreur : Clés manquantes dans le fichier .env (Vérifie JIRA_BOARD_ID !)")
    exit()

auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_TOKEN)
headers = {"Accept": "application/json", "Content-Type": "application/json"}
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY)

# =====================================================================
# 1. RÉCUPÉRATION DU BACKLOG GLOBAL (CORRIGÉ : VISION PLUS LARGE)
# =====================================================================
try:
    search_url = f"{JIRA_URL.rstrip('/')}/rest/api/3/search/jql"
    payload = {
        # Trié par le plus RÉCENT en premier pour attraper le Sprint 2 immédiatement
        "jql": "project=ECOMENU AND sprint IS EMPTY ORDER BY created DESC",
        "maxResults": 30, # Augmenté à 30 pour que l'IA ait une vraie vue d'ensemble
        "fields": ["summary", "description"]
    }
    response = requests.post(search_url, headers=headers, json=payload, auth=auth)
    tickets = response.json().get("issues", [])
    
    if not tickets:
        print("📭 Aucun ticket hors-sprint trouvé dans le Backlog. Tout est déjà organisé !")
        exit()
        
    backlog_texte = ""
    liste_cles = []
    for t in tickets:
        backlog_texte += f"- [{t['key']}] {t['fields']['summary']}\n"
        liste_cles.append(t['key'])
        
    print(f"📥 {len(tickets)} tickets détectés dans le Backlog en attente d'organisation.")
except Exception as e:
    print(f"❌ Erreur lors de la lecture du backlog : {e}")
    exit()

# =====================================================================
# 2# =====================================================================
# 2. L'AGENT PO DÉDUIT LA COMPOSITION DU PROCHAIN SPRINT
# =====================================================================
print("\n🔮 [Agent PO] Analyse du backlog pour concevoir la prochaine itération...")

system_prompt = """Tu es le Product Owner Virtuel.
Ton rôle est de regarder la liste de tickets en attente dans le backlog et de regrouper entre 2 et 4 tickets qui ont une forte cohérence technique ou fonctionnelle pour former le prochain Sprint.
Tu dois répondre UNIQUEMENT sous la forme d'un tableau JSON contenant la liste des clés sélectionnées.
Exemple de réponse attendue :
["ECOMENU-19", "ECOMENU-20"]"""

response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=backlog_texte)])

try:
    texte_propre = response.content.strip().replace("```json", "").replace("```", "")
    tickets_selectionnes = json.loads(texte_propre)
    print(f"🎯 [Agent PO] Choix validé pour le nouveau Sprint : {tickets_selectionnes}")
except Exception as e:
    print(f"⚠️ Erreur de lecture du choix de l'IA, sélection automatique.")
    tickets_selectionnes = liste_cles[:3]

# =====================================================================
# # =====================================================================
# 3. CRÉATION DYNAMIQUE DU SPRINT SUR JIRA
# =====================================================================
try:
    # A. Demander à Jira combien de Sprints existent déjà
    get_sprints_url = f"{JIRA_URL.rstrip('/')}/rest/agile/1.0/board/{JIRA_BOARD_ID}/sprint"
    sprints_existants = requests.get(get_sprints_url, headers=headers, auth=auth).json().get("values", [])
    numero_prochain_sprint = len(sprints_existants) + 1
    nom_du_sprint = f"Sprint {numero_prochain_sprint} - Auto"
    
    # B. Créer le nouveau Sprint
    sprint_url = f"{JIRA_URL.rstrip('/')}/rest/agile/1.0/sprint"
    sprint_payload = {
        "name": nom_du_sprint,
        "originBoardId": int(JIRA_BOARD_ID),
        "goal": "Implémentation des tickets sélectionnés par l'Agent PO."
    }
    
    sprint_res = requests.post(sprint_url, headers=headers, json=sprint_payload, auth=auth)
    
    if sprint_res.status_code != 201:
        print(f"❌ Impossible de créer le Sprint sur Jira : {sprint_res.text}")
        exit()
        
    sprint_id = sprint_res.json().get("id")
    print(f"📆 [JIRA] '{nom_du_sprint}' créé avec succès (ID: {sprint_id}) !")
    
    # C. Déplacer les tickets dedans
    move_url = f"{JIRA_URL.rstrip('/')}/rest/agile/1.0/sprint/{sprint_id}/issue"
    move_payload = {"issues": tickets_selectionnes}
    move_res = requests.post(move_url, headers=headers, json=move_payload, auth=auth)
    
    print(f"🚀 [SUCCÈS] L'Agent PO a rangé les tickets dans le {nom_du_sprint} !")

except Exception as e:
    print(f"❌ Erreur lors des requêtes Agile Jira : {e}")