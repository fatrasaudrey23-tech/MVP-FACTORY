import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

print("🔍 Recherche des moteurs de texte compatibles...")
for model in client.models.list():
    nom = model.name
    # On élimine le bruit (audio, vidéo, vecteurs) pour ne garder que le texte
    if "gemini" in nom and "audio" not in nom and "embedding" not in nom and "live" not in nom:
        print(f"✅ {nom}")