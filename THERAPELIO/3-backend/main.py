import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from prompts import FEW_SHOT_EXAMPLES, THERAPELIO_SYSTEM_INSTRUCTION, MODULES_PARCOURS
from pydantic import BaseModel

# 1. Chargement des variables d'environnement
load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    load_dotenv(dotenv_path="../.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CALCOM_API_KEY = os.getenv("CALCOM_API_KEY")
CALCOM_BASE_URL = "https://api.cal.com/v2"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 2. Initialisation de l'App FastAPI
app = FastAPI(
    title="Therapelio API",
    description="Backend IA QVT - Moteur Auto-Réparateur Restauré",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    session_id: str = "default_session"
    message: str
    history: list = []

class BookingRequest(BaseModel):
    eventTypeId: int
    start: str
    name: str
    email: str


# 3. LE MOTEUR AUTO-RÉPARATEUR ORIGINEL
ACTIVE_WORKING_MODEL = None
MODEL_BLACKLIST = set()

def get_candidate_models():
    """Récupère et trie les modèles disponibles en excluant la blacklist."""
    try:
        models = [
            m.name
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
            and m.name not in MODEL_BLACKLIST
        ]
        flash_models = [m for m in models if "flash" in m.lower()]
        other_models = [m for m in models if "flash" not in m.lower()]
        return flash_models + other_models
    except Exception:
        return [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro",
            "gemini-1.0-pro",
        ]

def generate_with_auto_healing(message: str, history: list, system_instruction: str):
    global ACTIVE_WORKING_MODEL, MODEL_BLACKLIST
    
    candidates = [ACTIVE_WORKING_MODEL] if ACTIVE_WORKING_MODEL else get_candidate_models()
    
    # Correction stricte du format d'historique pour éviter l'erreur de dictionnaire
    formatted_history = []
    for h in history:
        role = h.get("role", "user")
        if role == "assistant":
            role = "model"
        parts = h.get("parts", h.get("content", ""))
        if isinstance(parts, str):
            parts = [parts]
        formatted_history.append({"role": role, "parts": parts})

    for model_name in candidates:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction,
            )
            chat_session = model.start_chat(history=formatted_history)
            response = chat_session.send_message(message)

            # Verrouillage du premier modèle qui répond sans erreur 404
            if not ACTIVE_WORKING_MODEL:
                ACTIVE_WORKING_MODEL = model_name
                print(f"✅ SUCCÈS ! Modèle verrouillé : {ACTIVE_WORKING_MODEL}")

            return response.text, model_name

        except Exception as e:
            error_str = str(e)
            print(f"⚠️ Échec sur {model_name}...")
            
            # Mise en liste noire des modèles inaccessibles ou restreints
            if "404" in error_str or "not found" in error_str.lower() or "no longer available" in error_str.lower():
                MODEL_BLACKLIST.add(model_name)
                if ACTIVE_WORKING_MODEL == model_name:
                    ACTIVE_WORKING_MODEL = None
                continue
            else:
                continue
    
    raise Exception("Aucun modèle d'IA n'est actuellement accessible avec cette clé API.")


# 4. Routes de l'API
@app.post("/v1/chat")
async def chat_with_therapelio(chat: ChatMessage):
    if not GEMINI_API_KEY:
        return {"status": "error", "reply": "L'IA est déconnectée (clé API manquante)."}
    if not chat.message.strip():
        return {"status": "error", "reply": "Le message ne peut pas être vide."}

    # Sécurité critique Niveau 4
    mots_cles_urgence = ["suicide", "en finir", "mourir", "plus envie de vivre", "tout stopper"]
    if any(mot in chat.message.lower() for mot in mots_cles_urgence):
        return {
            "status": "success",
            "reply": "Ce que tu me dis m'inquiète beaucoup. Je ne peux pas t'accompagner seul(e) sur ça, il faut qu'on te mette en lien avec quelqu'un maintenant. Voici le 3114, le numéro national de prévention du suicide, gratuit et disponible 24h/24.",
            "security": "urgence_vitale_detectee"
        }

    parcours_actif = "A"
    texte_module = MODULES_PARCOURS.get(parcours_actif, MODULES_PARCOURS["A"])
    final_system_instruction = f"{THERAPELIO_SYSTEM_INSTRUCTION}\n\n[INSTRUCTIONS SPÉCIFIQUES]\n{texte_module}"

    full_history = FEW_SHOT_EXAMPLES.copy()
    for msg in chat.history:
        full_history.append({"role": msg.get("role"), "parts": [msg.get("content")]})

    try:
        reponse_texte, model_used = generate_with_auto_healing(chat.message, full_history, final_system_instruction)
        return {
            "status": "success",
            "reply": reponse_texte,
            "security": "auto_healing_verified",
            "model_used": model_used
        }
    except Exception as e:
        return {"status": "error", "reply": f"Erreur API Gemini : {str(e)}"}


# Routes Cal.com
@app.get("/v1/therapists/slots/{event_type_id}")
async def get_slots(event_type_id: int):
    if not CALCOM_API_KEY:
        raise HTTPException(status_code=500, detail="Clé Cal.com manquante.")
    now = datetime.now(timezone.utc)
    end_time = now + timedelta(hours=72)
    headers = {"Authorization": f"Bearer {CALCOM_API_KEY}"}
    params = {
        "eventTypeId": event_type_id,
        "startTime": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }
    response = requests.get(f"{CALCOM_BASE_URL}/slots/available", headers=headers, params=params)
    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()
@app.post("/v1/bookings/create")
async def create_booking(booking: BookingRequest):
    if not CALCOM_API_KEY:
        raise HTTPException(status_code=500, detail="Clé Cal.com manquante.")
    
    headers = {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "Content-Type": "application/json",
        "cal-api-version": "2024-08-13" 
    }
    
    # Structure corrigée : 'attendee' au singulier (sans les crochets du tableau)
    payload = {
        "start": booking.start,
        "eventTypeId": booking.eventTypeId,
        "attendee": {
            "name": booking.name,
            "email": booking.email,
            "timeZone": "Europe/Paris",
            "language": "fr"
        }
    }
    
    response = requests.post("https://api.cal.com/v2/bookings", headers=headers, json=payload)
    
    if not response.ok:
        print("Erreur Cal.com V2 :", response.text)
        raise HTTPException(status_code=response.status_code, detail=response.text)
        
    return response.json()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)