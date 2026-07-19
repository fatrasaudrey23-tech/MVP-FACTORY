import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generer_frontend(projet_nom):
    print(f"🎨 Agent Frontend : Génération avec verrous anti-boucle...")
    
    chemin_contrat = os.path.join(projet_nom, "api_contract.json")
    contrat = {"routes": []}
    if os.path.exists(chemin_contrat):
        with open(chemin_contrat, "r", encoding="utf-8") as f:
            contrat = json.load(f)

    # Force une structure qui interdit les boucles via une fonction unique de fetch
    prompt = f"""
    Tu es un Développeur Frontend Senior. Génère le fichier `index.html` COMPLET.
    
    RÈGLES D'OR ANTI-BOUCLE (À RESPECTER STRICTEMENT) :
    1. UTILISE CETTE FONCTION UNIQUE POUR TOUS LES APPELS API :
       async function safeFetch(url) {{
           try {{
               const response = await fetch(url);
               return await response.json();
           }} catch (e) {{ console.error("Erreur safeFetch", e); return null; }}
       }}
    2. APPELS : N'appelle `safeFetch` QUE dans des gestionnaires d'événements (boutons, clics) ou dans un useEffect avec tableau de dépendances vide `[]`.
    3. INTERDICTION : Il est strictement interdit d'appeler `fetch` en dehors d'une fonction, ou de faire un appel qui déclenche un rechargement d'état qui lui-même relance l'appel.
    4. GESTION DYNAMIQUE : Si l'URL contient {{id}}, remplace-la par une valeur fixe ou récupérée une seule fois.
    
    Contrat API : {json.dumps(contrat)}
    """

    model = genai.GenerativeModel('gemini-1.5-flash')
    reponse = model.generate_content(prompt).text
    code_propre = reponse.replace("```html", "").replace("```", "").strip()

    chemin_frontend = os.path.join(projet_nom, "4-frontend")
    os.makedirs(chemin_frontend, exist_ok=True)
    with open(os.path.join(chemin_frontend, "index.html"), "w", encoding="utf-8") as f:
        f.write(code_propre)
    
    print("✅ Frontend verrouillé contre les boucles.")

if __name__ == "__main__":
    try:
        projet_cible = input()
    except EOFError:
        projet_cible = input("Nom du projet : ")
    generer_frontend(projet_cible.strip())