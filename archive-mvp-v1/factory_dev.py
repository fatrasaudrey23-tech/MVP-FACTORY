import os
import json
import requests
from requests.auth import HTTPBasicAuth
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph

# =====================================================================
# 1. INITIALISATION ET SÉCURITÉ
# =====================================================================
print("🔌 Démarrage de la Factory Dev (Mode SPRINT RUNNER)...")
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
JIRA_URL = os.environ.get("JIRA_URL")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN")

if not all([GEMINI_API_KEY, JIRA_URL, JIRA_EMAIL, JIRA_TOKEN]):
    print("❌ Erreur : Impossible de démarrer. Vérifie tes clés dans le fichier .env !")
    exit()

print("✅ Clés validées. L'usine de développement est sous tension !")

# =====================================================================
# 2. LA MÉMOIRE PARTAGÉE (LE STATE LANGGRAPH)
# =====================================================================
class AgentState(TypedDict):
    ticket_id: str
    ticket_description: str
    architecture_plan: str
    generated_code: str
    qa_errors: str
    iterations: int

# =====================================================================
# 3. LES AGENTS (NŒUDS DU GRAPHE)
# =====================================================================
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY)

def tech_lead_node(state: AgentState):
    print(f"\n👨‍💻 [Tech Lead] Analyse du ticket {state.get('ticket_id')}...")
    system_prompt = """Tu es le Lead Tech Senior de l'agence.
    Ton rôle est de lire la description d'un ticket technique et de concevoir le plan d'action strict.
    Règles absolues :
    1. Tu ne produis PAS le code final.
    2. Tu définis le nom du fichier Python à créer.
    3. Tu listes les bibliothèques nécessaires.
    4. Tu détailles la structure des fonctions requises."""

    user_prompt = f"Ticket: {state.get('ticket_id')}\nDescription:\n{state.get('ticket_description')}\nRédige ton plan."
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    return {"architecture_plan": response.content}

def developer_node(state: AgentState):
    iteration_actuelle = state.get('iterations', 0) + 1
    print(f"💻 [Développeur] Écriture du code en cours (Essai n°{iteration_actuelle})...")
    system_prompt = """Tu es un Développeur Python Backend Senior.
    Écris le code Python en suivant STRICTEMENT le plan fourni.
    Règles :
    1. Réponds UNIQUEMENT avec le code brut.
    2. AUCUN texte d'introduction ou de conclusion.
    3. N'utilise PAS de balises Markdown autour du code.
    4. TRÈS IMPORTANT : Le code doit être strictement compatible avec Python 3.9. N'utilise SURTOUT PAS l'opérateur `|` pour les types (utilise `typing.Optional` ou `typing.Union` à la place).
    5. Le script doit être 100% indépendant (standalone). N'importe AUCUN module provenant d'un dossier externe imaginaire (comme 'src' ou 'models')."""

    user_prompt = f"Plan de l'architecte:\n{state.get('architecture_plan')}\nErreurs QA à corriger:\n{state.get('qa_errors', 'Aucune')}\nÉcris le script."
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    code = response.content.strip()
    prefix_python = "```python"
    prefix_generic = "```"
    
    if code.startswith(prefix_python): code = code[len(prefix_python):]
    elif code.startswith(prefix_generic): code = code[len(prefix_generic):]
    if code.endswith(prefix_generic): code = code[:-len(prefix_generic)]
        
    return {"generated_code": code.strip()}

def qa_node(state: AgentState):
    print("🕵️ [Testeur QA] Inspection du code par rapport au plan...")
    iteration_actuelle = state.get("iterations", 0) + 1
    system_prompt = """Tu es un Ingénieur QA Intraitable.
    Vérifie le code généré par rapport au plan initial.
    SI LE CODE EST PARFAIT : Réponds EXACTEMENT par le mot 'VALID'.
    S'IL Y A UNE ERREUR : Liste les erreurs pour le développeur."""

    user_prompt = f"Plan original:\n{state.get('architecture_plan')}\n\nCode du développeur:\n{state.get('generated_code')}\n\nInspecte rigoureusement ce code."
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    result = response.content.strip()
    
    if result == "VALID" or "VALID" in result.upper():
        print("✅ [Testeur QA] Code validé !")
        return {"qa_errors": "VALID", "iterations": iteration_actuelle}
    else:
        print("❌ [Testeur QA] Code refusé. Renvoi au développeur...")
        return {"qa_errors": result, "iterations": iteration_actuelle}

# =====================================================================
# 4. LE ROUTAGE & COMPILATION DU GRAPHE
# =====================================================================
def route_qa(state: AgentState) -> Literal["developer", "__end__"]:
    if state.get("qa_errors") == "VALID" or state.get("iterations", 0) >= 3:
        return "__end__"
    return "developer"

workflow = StateGraph(AgentState)
workflow.add_node("tech_lead", tech_lead_node)
workflow.add_node("developer", developer_node)
workflow.add_node("qa", qa_node)
workflow.set_entry_point("tech_lead")
workflow.add_edge("tech_lead", "developer")
workflow.add_edge("developer", "qa")
workflow.add_conditional_edges("qa", route_qa)
app = workflow.compile()

# =====================================================================
# 6. LE CHEF D'ORCHESTRE DU SPRINT (LA BOUCLE)
# =====================================================================
if __name__ == "__main__":
    print("\n🚀 Connexion à Jira pour récupérer le Sprint en cours...")
    
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_TOKEN)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    try:
        search_url = f"{JIRA_URL.rstrip('/')}/rest/api/3/search/jql"
        # On demande uniquement les tickets des Sprints actifs dont le statut n'est pas "Terminé"
        payload = {
            "jql": "project=ECOMENU AND sprint IN openSprints() AND statusCategory != Done ORDER BY created ASC",
            "maxResults": 20,
            "fields": ["*all"]
        }
        response = requests.post(search_url, headers=headers, json=payload, auth=auth)
        issues = response.json().get("issues", [])
        
        if not issues:
            print("📭 Aucun ticket trouvé dans le Sprint. Le backlog de dev est vide ! Session de surf pour tout le monde.")
            exit()
            
        print(f"📦 {len(issues)} tickets trouvés dans le Sprint. L'équipe se met au travail à la chaîne !")
        
    except Exception as e:
        print(f"❌ Erreur générale de connexion : {e}")
        exit()

    for i, target_issue in enumerate(issues, 1):
        issue_key = target_issue.get("key") or target_issue.get("id") or "ECO-INCONNU"
        fields = target_issue.get("fields", {})
        issue_summary = fields.get("summary", "Titre non trouvé")
        
        print(f"\n=======================================================")
        print(f"▶️ TRAITEMENT DU TICKET {i}/{len(issues)} : [{issue_key}] {issue_summary}")
        print(f"=======================================================")

        real_ticket = {
            "ticket_id": issue_key,
            "ticket_description": f"Titre: {issue_summary}",
            "architecture_plan": "",
            "generated_code": "",
            "qa_errors": "",
            "iterations": 0
        }
        
        final_state = app.invoke(real_ticket)
        
        # ASTUCE LEAD TECH : On remplace le tiret de Jira par un underscore pour Python
        nom_fichier = f"{issue_key.replace('-', '_')}_code_genere.py"
        
        with open(nom_fichier, "w", encoding="utf-8") as f:
            f.write(final_state["generated_code"])
            
        print(f"🎉 [SUCCÈS] Code généré et sauvegardé sous '{nom_fichier}' !")
        
        try:
            comment_url = f"{JIRA_URL.rstrip('/')}/rest/api/2/issue/{issue_key}/comment"
            payload_comment = json.dumps({"body": f"✅ Code automatiquement généré lors du Sprint.\nFichier produit : {nom_fichier}"})
            requests.post(comment_url, headers=headers, data=payload_comment, auth=auth)
            print(f"📝 Commentaire ajouté sur le ticket {issue_key}.")
        except Exception as e:
            print(f"⚠️ Impossible de commenter : {e}")
