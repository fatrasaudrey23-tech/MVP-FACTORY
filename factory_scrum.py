import os
import glob
from dotenv import load_dotenv
from google import genai
from jira import JIRA

def selectionner_projet():
    """Affiche un menu interactif pour choisir le projet cible."""
    print("\n==============================================")
    print(" 🧠 AGENT SCRUM MASTER - SÉLECTEUR DE CONTEXTE")
    print("==============================================\n")
    
    # Liste les dossiers (en ignorant les dossiers cachés et les fichiers)
    dossiers = [d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".")]
    
    if not dossiers:
        print("❌ Aucun dossier de projet trouvé.")
        exit()
        
    for i, dossier in enumerate(dossiers, 1):
        print(f"[{i}] {dossier}")
        
    choix = input("\n👉 Pour quel projet veux-tu générer le Backlog Jira ? (Tape le numéro) : ")
    
    try:
        index = int(choix) - 1
        projet_cible = dossiers[index]
        print(f"\n✅ Contexte basculé sur : {projet_cible}")
        return projet_cible
    except:
        print("❌ Choix invalide. Arrêt du script.")
        exit()

def executer_scrum():
    # 1. CHARGEMENT DES CLÉS MAÎTRESSES (Racine de l'usine)
    load_dotenv(dotenv_path=".env")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    JIRA_URL = os.environ.get("JIRA_URL")
    JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
    JIRA_TOKEN = os.environ.get("JIRA_TOKEN")

    if not all([GEMINI_API_KEY, JIRA_URL, JIRA_EMAIL, JIRA_TOKEN]):
        print("❌ Erreur : Il manque des clés maîtresses dans ton fichier .env à la racine.")
        exit()

    # 2. SÉLECTION DU PROJET
    projet = selectionner_projet()
    
    # 3. CHARGEMENT DES CLÉS DU PROJET (Local)
    chemin_env_projet = os.path.join(projet, "2-readytobuild", ".env")
    if os.path.exists(chemin_env_projet):
        # override=True permet aux variables locales d'écraser les variables globales si besoin
        load_dotenv(dotenv_path=chemin_env_projet, override=True) 
    else:
        print(f"❌ Fichier manquant : {chemin_env_projet}")
        exit()

    JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY")
    if not JIRA_PROJECT_KEY:
        print("❌ Erreur : JIRA_PROJECT_KEY introuvable dans le .env de ton projet.")
        exit()

    # 4. CONNEXION À JIRA
    print(f"🔌 Connexion à l'espace Jira de l'usine...")
    try:
        jira_client = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_TOKEN))
        print(f"🛡️ Connecté avec succès. Routage vers le tableau : {JIRA_PROJECT_KEY}")
    except Exception as e:
        print(f"❌ Impossible de se connecter à Jira : {e}")
        exit()

    # 5. RECHERCHE DU PRD DANS LE DOSSIER READY TO BUILD
    dossier_ready = os.path.join(projet, "2-readytobuild")
    chemin_fichiers_txt = os.path.join(dossier_ready, "PRD_*.txt")
    fichiers_trouves = glob.glob(chemin_fichiers_txt)

    if not fichiers_trouves:
        print(f"⚠️ Aucun fichier PRD trouvé dans {dossier_ready}.")
        print("As-tu bien déplacé le document depuis le dossier 1-draft ?")
        exit()

    chemin_prd = fichiers_trouves[0] # On prend le premier fichier PRD trouvé
    with open(chemin_prd, "r", encoding="utf-8") as f:
        prd_content = f.read()

    print(f"📄 Document {os.path.basename(chemin_prd)} lu avec succès. L'IA analyse ton produit...")

    # 6. APPEL À L'IA POUR CRÉER LES TICKETS (Logique de l'usine)
    # C'est ici que Gemini analyse le PRD et prépare tes Sprints
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Tu es un Scrum Master et Tech Lead d'exception.
    Lis ce PRD : 
    {prd_content}
    
    Génère un plan de développement sous forme de 3 tickets fondateurs pour démarrer.
    Retourne UNIQUEMENT un tableau JSON avec cette structure exacte :
    [
        {{"titre": "ENG-01: Création de la base de données", "description": "Critères d'acceptation..."}}
    ]
    """

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt
        )
        # Nettoyage de la réponse pour obtenir du JSON pur
        reponse_brute = response.text.replace("```json", "").replace("```", "").strip()
        tickets = eval(reponse_brute) # Note : json.loads() est plus sûr en production
    except Exception as e:
        print(f"❌ Erreur lors de la réflexion de l'IA : {e}")
        exit()

    # 7. CRÉATION DES TICKETS DANS LE BON TABLEAU JIRA
    print("🚀 Injection des tickets dans le tableau Jira...")
    for ticket in tickets:
        try:
            nouveau_ticket = jira_client.create_issue(
                project=JIRA_PROJECT_KEY,
                summary=ticket['titre'],
                description=ticket['description'],
                issuetype={'name': 'Tâche'}
            )
            print(f"✅ Créé : {nouveau_ticket.key} - {ticket['titre']}")
        except Exception as e:
            print(f"⚠️ Erreur lors de la création du ticket '{ticket['titre']}' : {e}")

    print("\n🏁 [AGENT SCRUM MASTER] Mission terminée. Le Backlog est prêt à être développé !")

if __name__ == "__main__":
    executer_scrum()