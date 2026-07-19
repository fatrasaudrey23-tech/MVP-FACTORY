import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generer_architecture(projet_nom):
    print(f"🧠 [Architecture 2.0] Analyse des relations dynamiques pour {projet_nom}...")
    
    prompt = f"""
    Tu es l'Architecte Logiciel Senior. Tu conçois le MVP de {projet_nom}.
    
    RÈGLE DE CONTRAT D'API AVANCÉ :
    Tu dois définir les routes en précisant les paramètres dynamiques avec une syntaxe claire.
    Si une route nécessite un ID, utilise la notation : /ressource/{{id}}.
    
    Génère à la fin un bloc JSON [API_CONTRACT] comprenant :
    - "routes": liste des routes.
    - "parameters": dictionnaire liant les routes aux paramètres attendus (ex: {{"/v1/conversations/{{id}}": "id"}})
    
    Exemple :
    [API_CONTRACT]
    {{
      "routes": ["/v1/conversations", "/v1/conversations/{{id}}"],
      "parameters": {{"/v1/conversations/{{id}}": "id"}}
    }}
    [/API_CONTRACT]
    """

    model = genai.GenerativeModel('gemini-1.5-flash')
    reponse = model.generate_content(prompt).text

    # Sauvegarde et extraction
    match = re.search(r'\[API_CONTRACT\](.*?)\[/API_CONTRACT\]', reponse, re.DOTALL)
    if match:
        with open(os.path.join(projet_nom, "api_contract.json"), "w", encoding="utf-8") as f:
            f.write(match.group(1).strip())
        print("📝 Contrat d'API 2.0 généré.")
    else:
        print("⚠️ Échec de génération du contrat.")

if __name__ == "__main__":
    try:
        projet_cible = input()
    except EOFError:
        projet_cible = input("Nom du projet : ")
    generer_architecture(projet_cible.strip())