import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generer_backend(projet_nom):
    print(f"⚙️ Agent Backend : Intégration des routes dynamiques pour {projet_nom}...")
    
    chemin_contrat = os.path.join(projet_nom, "api_contract.json")
    contrat = {"routes": [], "parameters": {}}
    if os.path.exists(chemin_contrat):
        with open(chemin_contrat, "r", encoding="utf-8") as f:
            contrat = json.load(f)

    schema_sql = "Aucun schéma."
    chemin_schema = os.path.join(projet_nom, "schema.sql")
    if os.path.exists(chemin_schema):
        with open(chemin_schema, "r", encoding="utf-8") as f:
            schema_sql = f.read()

    prompt = f"""
    Tu es un Développeur Backend Senior Expert en FastAPI.
    Génère le `main.py` complet.
    
    RÈGLES D'OR :
    1. ROUTES DYNAMIQUES : Pour les routes comme "/v1/conversations/{{id}}", tu DOIS utiliser la syntaxe FastAPI : @app.get("/v1/conversations/{{id}}") et définir la fonction comme `async def get_conversation(id: str):`.
    2. SUPABASE : Utilise les clés `SUPABASE_URL` et `SUPABASE_KEY` du .env pour requêter les tables définies dans ce schéma : {schema_sql}.
    3. CORS : Ajoute toujours le `CORSMiddleware` (allow_origins=["*"]).
    4. JOKER : Ajoute une route catch-all à la fin pour logger les requêtes inconnues.
    
    Contrat API : {json.dumps(contrat)}
    """

    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        reponse = model.generate_content(prompt).text
        code_propre = reponse.replace("```python", "").replace("```", "").strip()
    except Exception as e:
        print(f"⚠️ Erreur IA : {e}")
        code_propre = "from fastapi import FastAPI\napp = FastAPI()\n"

    # Injection automatique si manquant
    if "CORSMiddleware" not in code_propre:
        code_propre = "from fastapi.middleware.cors import CORSMiddleware\n" + code_propre.replace("app = FastAPI()", "app = FastAPI()\n\napp.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])")

    chemin_backend = os.path.join(projet_nom, "3-backend")
    os.makedirs(chemin_backend, exist_ok=True)
    with open(os.path.join(chemin_backend, "main.py"), "w", encoding="utf-8") as f:
        f.write(code_propre)
    
    print("✅ Backend généré avec gestion dynamique des paramètres.")

if __name__ == "__main__":
    try:
        projet_cible = input()
    except EOFError:
        projet_cible = input("Nom du projet : ")
    generer_backend(projet_cible.strip())