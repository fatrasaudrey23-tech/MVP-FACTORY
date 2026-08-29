import json
import os
import re
from contextlib import asynccontextmanager

import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai

import db
from prompts import (
    FEW_SHOT_EXAMPLES,
    THERAPELIO_SYSTEM_INSTRUCTION,
    MODULES_PARCOURS,
    RISK_CLASSIFICATION_INSTRUCTION,
)
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
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="Therapelio API",
    description="Backend IA QVT - Moteur Auto-Réparateur Restauré",
    lifespan=lifespan,
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
    user_id: str = ""
    # Repli si aucun profil enregistré (compatibilité, usage sans inscription)
    prenom: str = ""
    poste: str = ""

class RegisterRequest(BaseModel):
    registration_code: str
    prenom: str
    poste: str = ""

class RecoverRequest(BaseModel):
    recovery_code: str

class BookingRequest(BaseModel):
    eventTypeId: int
    start: str
    name: str
    email: str


# 3. LE MOTEUR AUTO-RÉPARATEUR ORIGINEL
ACTIVE_WORKING_MODEL = None
MODEL_BLACKLIST = set()

# État de risque par conversation (en mémoire : suffisant pour le MVP,
# se réinitialise si le serveur redémarre ou tourne sur plusieurs instances).
SESSION_STATE: dict = {}

def get_session_state(session_id: str) -> dict:
    if session_id not in SESSION_STATE:
        SESSION_STATE[session_id] = {"niveau_max": 1, "parcours_actif": None}
    return SESSION_STATE[session_id]

MODELE_EXCLUS_MOTS_CLES = ("tts", "image", "embedding", "vision", "aqa")

# Timeout appliqué à chaque appel Gemini : sans ça, un modèle en quota dépassé ou
# surchargé peut faire "traîner" la requête pendant plusieurs minutes (le SDK retente
# en interne) avant de remonter l'erreur, ce qui bloque l'utilisateur en silence.
GEMINI_TIMEOUT_CHAT = {"timeout": 25}
GEMINI_TIMEOUT_CLASSIFICATION = {"timeout": 15}

def get_candidate_models():
    """Récupère et trie les modèles disponibles en excluant la blacklist."""
    try:
        models = [
            m.name
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
            and m.name not in MODEL_BLACKLIST
            and not any(mot in m.name.lower() for mot in MODELE_EXCLUS_MOTS_CLES)
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

def _format_history(history: list) -> list:
    """Correction stricte du format d'historique pour éviter l'erreur de dictionnaire."""
    formatted_history = []
    for h in history:
        role = h.get("role", "user")
        if role == "assistant":
            role = "model"
        parts = h.get("parts", h.get("content", ""))
        if isinstance(parts, str):
            parts = [parts]
        formatted_history.append({"role": role, "parts": parts})
    return formatted_history


def _run_with_auto_healing(call_fn):
    """Essaie chaque modèle candidat jusqu'à ce que call_fn(model_name) réussisse."""
    global ACTIVE_WORKING_MODEL, MODEL_BLACKLIST

    candidates = [ACTIVE_WORKING_MODEL] if ACTIVE_WORKING_MODEL else get_candidate_models()

    for model_name in candidates:
        try:
            result = call_fn(model_name)

            # Verrouillage du premier modèle qui répond sans erreur 404
            if not ACTIVE_WORKING_MODEL:
                ACTIVE_WORKING_MODEL = model_name
                print(f"✅ SUCCÈS ! Modèle verrouillé : {ACTIVE_WORKING_MODEL}")

            return result, model_name

        except Exception as e:
            error_str = str(e)
            print(f"⚠️ Échec sur {model_name}...")

            # Mise en liste noire des modèles inaccessibles ou restreints
            if "404" in error_str or "not found" in error_str.lower() or "no longer available" in error_str.lower():
                MODEL_BLACKLIST.add(model_name)
                if ACTIVE_WORKING_MODEL == model_name:
                    ACTIVE_WORKING_MODEL = None
            continue

    raise Exception("Aucun modèle d'IA n'est actuellement accessible avec cette clé API.")


def generate_with_auto_healing(message: str, history: list, system_instruction: str):
    formatted_history = _format_history(history)

    def call(model_name):
        model = genai.GenerativeModel(model_name=model_name, system_instruction=system_instruction)
        chat_session = model.start_chat(history=formatted_history)
        return chat_session.send_message(message, request_options=GEMINI_TIMEOUT_CHAT).text

    return _run_with_auto_healing(call)


def generate_oneshot_with_auto_healing(prompt: str, system_instruction: str):
    def call(model_name):
        model = genai.GenerativeModel(model_name=model_name, system_instruction=system_instruction)
        return model.generate_content(prompt, request_options=GEMINI_TIMEOUT_CLASSIFICATION).text

    return _run_with_auto_healing(call)


def classify_risk(message: str, history: list, niveau_max_session: int) -> dict:
    """
    Passe 1 : classification du risque et du parcours probable.
    Appel LLM séparé, sans état, avec repli sûr si le LLM ou le parsing échoue.
    """
    historique_resume = "\n".join(
        f"{h.get('role', 'user')}: {h.get('content', h.get('parts', ''))}" for h in history[-6:]
    )
    prompt = f"""Historique récent :
{historique_resume or '(aucun)'}

Dernier message de l'utilisateur : {message}

Niveau de risque maximum déjà atteint dans cette conversation : {niveau_max_session}

Réponds UNIQUEMENT avec un objet JSON strict, au format exact :
{{"niveau": <entier 1 à 4>, "categories_detectees": [<liste de chaînes>], "parcours_probable": "<une lettre parmi A,B,C,D,E,F,G,H>", "confiance": <0 à 1>, "justification_courte": "<une phrase>"}}

Barème :
1 = échange standard, pas de signal de détresse particulier
2 = signal de mal-être modéré
3 = détresse aiguë nécessitant une orientation rapide vers un professionnel
4 = urgence vitale (idées suicidaires explicites, danger immédiat pour soi ou autrui)

Ne descends jamais en dessous du niveau {niveau_max_session} sans justification majeure explicite dans le dernier message.
"""
    try:
        raw_text, _ = generate_oneshot_with_auto_healing(prompt, RISK_CLASSIFICATION_INSTRUCTION)
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        data = json.loads(match.group(0) if match else raw_text)

        niveau = max(1, min(4, int(data.get("niveau", 1))))
        parcours = str(data.get("parcours_probable", "A")).strip().upper()
        if parcours not in MODULES_PARCOURS:
            parcours = "A"

        return {
            "niveau": niveau,
            "categories_detectees": data.get("categories_detectees", []),
            "parcours_probable": parcours,
        }
    except Exception as e:
        print(f"⚠️ Classification de risque indisponible ({e}), repli sur niveau 1 / parcours A.")
        return {"niveau": 1, "categories_detectees": [], "parcours_probable": "A"}


# 4. Routes de l'API

# Filet de sécurité rapide par mots-clés : défense en profondeur, ne dépend pas du LLM.
MOTS_CLES_URGENCE = ["suicide", "en finir", "mourir", "plus envie de vivre", "tout stopper", "me faire du mal", "me tuer"]


@app.post("/v1/auth/register")
async def register(req: RegisterRequest):
    if not req.prenom.strip():
        raise HTTPException(status_code=400, detail="Le prénom est requis.")
    resultat = db.register_user(req.registration_code, req.prenom, req.poste)
    if not resultat:
        raise HTTPException(status_code=404, detail="Code entreprise invalide ou base de données indisponible.")
    return resultat


@app.post("/v1/auth/recover")
async def recover(req: RecoverRequest):
    resultat = db.recover_user(req.recovery_code)
    if not resultat:
        raise HTTPException(status_code=404, detail="Code de récupération introuvable.")
    return resultat


@app.post("/v1/chat")
async def chat_with_therapelio(chat: ChatMessage):
    if not GEMINI_API_KEY:
        return {"status": "error", "reply": "L'IA est déconnectée (clé API manquante)."}
    if not chat.message.strip():
        return {"status": "error", "reply": "Le message ne peut pas être vide."}

    session_id = chat.session_id or "default_session"
    state = get_session_state(session_id)

    # Le profil enregistré en base (via /v1/auth) prime sur les champs libres envoyés
    # par le client, qui ne servent plus que de repli si l'utilisateur n'a pas de compte.
    profil = db.get_user(chat.user_id) if chat.user_id else None
    if profil:
        chat.prenom = profil["prenom"]
        chat.poste = profil["poste"]

    alerte_mot_cle = any(mot in chat.message.lower() for mot in MOTS_CLES_URGENCE)
    classification = classify_risk(chat.message, chat.history, state["niveau_max"])

    niveau = max(classification["niveau"], state["niveau_max"], 4 if alerte_mot_cle else 0)
    state["niveau_max"] = niveau

    # Niveau 4 : urgence vitale, on court-circuite la génération conversationnelle.
    if niveau == 4:
        db.log_crisis_event(session_id, 4, classification["categories_detectees"], "urgence_vitale_hotline_affichee")
        return {
            "status": "success",
            "reply": "Ce que tu me dis m'inquiète beaucoup. Je ne peux pas t'accompagner seul(e) sur ça, il faut qu'on te mette en lien avec quelqu'un maintenant. Voici le 3114, le numéro national de prévention du suicide, gratuit et disponible 24h/24.",
            "security": "urgence_vitale_detectee",
            "niveau_risque": 4,
        }

    # Niveau 3 : détresse aiguë, on force le parcours F (orientation prioritaire) et on journalise.
    if niveau == 3:
        parcours_actif = "F"
        db.log_crisis_event(session_id, 3, classification["categories_detectees"], "orientation_prioritaire_proposee")
    else:
        # Le parcours se fixe au premier échange puis reste stable sur la session
        # (le motif initial ne doit pas changer de catégorie à chaque message).
        if not state["parcours_actif"]:
            state["parcours_actif"] = classification["parcours_probable"]
        parcours_actif = state["parcours_actif"]

    texte_module = MODULES_PARCOURS.get(parcours_actif, MODULES_PARCOURS["A"])

    # Contexte de personnalisation (prénom / poste) : tronqué par prudence, ce sont
    # des champs libres saisis par l'utilisateur et injectés dans le prompt système.
    prenom = (chat.prenom or "").strip()[:40]
    poste = (chat.poste or "").strip()[:60]
    contexte_utilisateur = ""
    if prenom:
        contexte_utilisateur = f"\n\n[CONTEXTE UTILISATEUR]\nPrénom : {prenom}."
        if poste:
            contexte_utilisateur += f"\nPoste : {poste}."

    final_system_instruction = f"{THERAPELIO_SYSTEM_INSTRUCTION}\n\n[INSTRUCTIONS SPÉCIFIQUES]\n{texte_module}{contexte_utilisateur}"

    full_history = FEW_SHOT_EXAMPLES.copy()
    for msg in chat.history:
        full_history.append({"role": msg.get("role"), "parts": [msg.get("content")]})

    try:
        reponse_texte, model_used = generate_with_auto_healing(chat.message, full_history, final_system_instruction)
        return {
            "status": "success",
            "reply": reponse_texte,
            "security": "auto_healing_verified",
            "model_used": model_used,
            "niveau_risque": niveau,
            "parcours_actif": parcours_actif,
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