import os
import json
from dotenv import load_dotenv
from google import genai
from jira import JIRA

print("🤖 [AGENT DÉVELOPPEUR] Initialisation de l'ouvrier IA...")

# =====================================================================
# 1. INITIALISATION DES OUTILS
# =====================================================================
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
JIRA_URL = os.environ.get("JIRA_URL")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN")

PROJECT_KEY = "ECOMENU"

# =====================================================================
# 2. CONNEXION JIRA ET RECHERCHE DE TRAVAIL
# =====================================================================
print("🔌 Connexion à Jira pour vérifier le Backlog...")
try:
    jira_client = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_TOKEN))
except Exception as e:
    print(f"❌ Impossible de s'authentifier à Jira : {e}")
    exit()

# Recherche le ticket le plus prioritaire qui est "À Faire" (To Do)
jql_query = f'project = {PROJECT_KEY} AND statusCategory = "To Do" ORDER BY priority DESC'
issues = jira_client.search_issues(jql_query, maxResults=1)

if not issues:
    print("☕ Aucun ticket 'À Faire' trouvé dans le backlog. L'usine est à jour, l'agent se repose.")
    exit()

ticket = issues[0]
print(f"📥 Prise en charge du ticket : [{ticket.key}] {ticket.fields.summary}")

# =====================================================================
# 3. CHARGEMENT DU CONTEXTE ARCHITECTURAL
# =====================================================================
das_context = ""
if os.path.exists("DAS_architecture.json"):
    with open("DAS_architecture.json", "r", encoding="utf-8") as f:
        das_context = f.read()

# =====================================================================
# 4. RÉFLEXION ET CODAGE (GEMINI PRO)
# =====================================================================
print("🧠 Analyse des critères d'acceptation et écriture du code en cours...")
ai_client = genai.Client(api_key=GEMINI_API_KEY)

prompt = f"""
Tu es un Ingénieur Logiciel Senior ultra-compétent. 
Voici un ticket Jira que tu dois développer.

TITRE DU TICKET : {ticket.fields.summary}
DESCRIPTION ET CRITÈRES D'ACCEPTATION :
{ticket.fields.description}

ARCHITECTURE DE LA BASE DE DONNÉES DU PROJET (DAS) :
{das_context}

Ta mission :
Écris le code complet et fonctionnel qui répond EXACTEMENT aux critères de ce ticket.
Règles strictes :
1. Ne fournis QUE le code brut, sans aucun texte d'introduction ou de conclusion (pas de "Voici le code...").
2. Si c'est du Python, encadre tout le code avec ```python et ```. 
3. Si c'est du HTML/CSS/JS, encadre avec ```html et ```.
"""

try:
    response = ai_client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt
    )
    code_brut = response.text
except Exception as e:
    print(f"❌ Erreur lors de la génération du code par l'IA : {e}")
    exit()

# =====================================================================
# 5. NETTOYAGE ET SAUVEGARDE DU FICHIER
# =====================================================================
extension = "txt"
code_propre = code_brut

if "```python" in code_brut.lower():
    code_propre = code_brut.split("```python")[1].split("```")[0].strip()
    extension = "py"
elif "```html" in code_brut.lower():
    code_propre = code_brut.split("```html")[1].split("```")[0].strip()
    extension = "html"
elif "```javascript" in code_brut.lower():
    code_propre = code_brut.split("```javascript")[1].split("```")[0].strip()
    extension = "js"
else:
    code_propre = code_brut.replace("```", "").strip()

nom_fichier = f"build_{ticket.key}.{extension}"

with open(nom_fichier, "w", encoding="utf-8") as f:
    f.write(code_propre)

print(f"💾 Succès ! Code généré et sauvegardé localement sous : {nom_fichier}")

# =====================================================================
# 6. RETOUR D'INFORMATION DANS JIRA
# =====================================================================
commentaire = f"✅ **Code généré automatiquement par l'Agent Développeur.**\n\nLe résultat a été sauvegardé en local dans ton usine sous le nom : `{nom_fichier}`.\nMerci de réviser le code."
jira_client.add_comment(ticket, commentaire)

print(f"🚀 Ticket {ticket.key} mis à jour avec un commentaire.")
print("🏁 [AGENT DÉVELOPPEUR] Fin de mission de codage.")