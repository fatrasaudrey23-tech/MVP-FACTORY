import os
import glob
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

print("📚 Démarrage de l'Agent Documentaliste (Génération du DAT)...")
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ Erreur : Clé GEMINI_API_KEY introuvable.")
    exit()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY, timeout=300.0, max_retries=5)

fichiers_code = glob.glob("*_code_genere.py")
contenu_fichiers = ""
for fichier in fichiers_code:
    with open(fichier, "r", encoding="utf-8") as f:
        contenu_fichiers += f"\n--- Fichier : {fichier} ---\n"
        contenu_fichiers += f.read() + "\n"

print("🧠 L'Agent analyse le code pour rédiger la documentation...")

system_prompt = """Tu es un Technical Writer (Rédacteur Technique) expert.
Ton rôle est de lire le code source fourni et de rédiger un Document d'Architecture Technique (DAT) complet en format Markdown.
Règles :
1. Crée des sections claires : Infrastructure Globale, Cartographie des APIs/URLs utilisées dans le code, et Registre des Clés/Variables d'environnement nécessaires.
2. Déduis la stack technique en lisant les imports (ex: supabase, openai, streamlit).
3. Sois professionnel, concis et utilise des emojis pour structurer le document.
4. Renvoie UNIQUEMENT le texte Markdown brut, sans balises externes (comme ```markdown)."""

user_prompt = f"Voici le code source du projet :\n{contenu_fichiers}\n\nRédige le fichier ARCHITECTURE.md."

response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])

code = response.content.strip()
if code.startswith("
```markdown"): code = code[11:]
elif code.startswith("```"): code = code[3:]
if code.endswith("
```"): code = code[:-3]

nom_fichier = "ARCHITECTURE.md"
with open(nom_fichier, "w", encoding="utf-8") as f:
    f.write(code.strip())

print(f"\n🎉 [SUCCÈS] Le document '{nom_fichier}' a été généré avec succès !")