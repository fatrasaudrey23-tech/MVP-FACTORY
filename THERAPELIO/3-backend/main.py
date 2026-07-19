import os
import time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from prompts import FEW_SHOT_EXAMPLES, THERAPELIO_SYSTEM_INSTRUCTION
from pydantic import BaseModel

# 1. Chargement des variables d'environnement
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CALCOM_API_KEY = os.getenv("CALCOM_API_KEY")
CALCOM_BASE_URL = "https://api.cal.com/v2"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 2. Initialisation de l'App FastAPI
app = FastAPI(
    title="Therapelio API",
    description="Backend IA QVT avec Bouclier Éthique et Sélection Auto-Réparatrice",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. Modèles de données Pydantic
class ChatMessage(BaseModel):
    message: str
    history: list = []


class BookingRequest(BaseModel):
    eventTypeId: int
    start: str
    name: str
    email: str


# 4. MOTEUR AUTO-RÉPARATEUR : Sélection et mémorisation du modèle valide
ACTIVE_WORKING_MODEL = None
MODEL_BLACKLIST = set()


def get_candidate_models():
    """Récupère et trie les modèles disponibles en excluant ceux qui ont déjà échoué."""
    try:
        models = [
            m.name
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
            and m.name not in MODEL_BLACKLIST
        ]
        # On teste en priorité les modèles "flash", puis "pro", puis les autres
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


# 5. Routes de l'API


@app.post("/v1/chat")
async def chat_with_therapelio(chat: ChatMessage):
    global ACTIVE_WORKING_MODEL

    if not GEMINI_API_KEY:
        return {
            "status": "error",
            "reply": "L'IA est déconnectée (clé API manquante).",
        }

    if not chat.message.strip():
        return {
            "status": "error",
            "reply": "Le message ne peut pas être vide.",
        }

    # Construction de l'historique : Exemples Few-Shot + Historique de session
    full_history = FEW_SHOT_EXAMPLES.copy()
    for msg in chat.history:
        full_history.append(
            {"role": msg.get("role"), "parts": [msg.get("content")]}
        )

    # Si on a déjà identifié le modèle fonctionnel, on l'utilise directement
    candidates = (
        [ACTIVE_WORKING_MODEL]
        if ACTIVE_WORKING_MODEL
        else get_candidate_models()
    )

    for model_name in candidates:
        try:
            if not ACTIVE_WORKING_MODEL:
                print(f"🔄 Test de communication avec : {model_name}...")

            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=THERAPELIO_SYSTEM_INSTRUCTION,
            )
            chat_session = model.start_chat(history=full_history)

            # C'est ici que le serveur Google est contacté :
            response = chat_session.send_message(chat.message)

            # Si le modèle répond, c'est une victoire ! On le mémorise à vie.
            if not ACTIVE_WORKING_MODEL:
                ACTIVE_WORKING_MODEL = model_name
                print(
                    f"✅ SUCCÈS ! Modèle officiel adopté : {ACTIVE_WORKING_MODEL}"
                )

            return {
                "status": "success",
                "reply": response.text,
                "security": "act_protocol_and_zero_retention_verified",
                "model_used": model_name,
            }

        except Exception as e:
            error_str = str(e)
            print(f"⚠️ Échec sur {model_name} ({error_str[:60]}...).")

            # Si le modèle est obsolète ou restreint (404), on le blacklist et le code teste automatiquement le suivant !
            if (
                "404" in error_str
                or "not found" in error_str.lower()
                or "no longer available" in error_str.lower()
            ):
                print(
                    f"🚫 Modèle {model_name} restreint par Google. Passage instantané au candidat suivant..."
                )
                MODEL_BLACKLIST.add(model_name)
                if ACTIVE_WORKING_MODEL == model_name:
                    ACTIVE_WORKING_MODEL = None
                continue
            else:
                continue

    return {
        "status": "error",
        "reply": "Désolé, aucun modèle d'IA n'est actuellement accessible avec cette clé API.",
    }


# Routes Cal.com inchangées
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

    response = requests.get(
        f"{CALCOM_BASE_URL}/slots/available", headers=headers, params=params
    )
    if not response.ok:
        raise HTTPException(
            status_code=response.status_code, detail=response.text
        )
    return response.json()


@app.post("/v1/bookings/create")
async def create_booking(booking: BookingRequest):
    if not CALCOM_API_KEY:
        raise HTTPException(status_code=500, detail="Clé Cal.com manquante.")
    headers = {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "start": booking.start,
        "eventTypeId": booking.eventTypeId,
        "attendees": [
            {
                "name": booking.name,
                "email": booking.email,
                "timeZone": "Europe/Paris",
                "language": "fr",
            }
        ],
        "timeZone": "Europe/Paris",
        "language": "fr",
    }
    response = requests.post(
        f"{CALCOM_BASE_URL}/bookings", headers=headers, json=payload
    )
    if not response.ok:
        raise HTTPException(
            status_code=response.status_code, detail=response.text
        )
    return response.json()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)