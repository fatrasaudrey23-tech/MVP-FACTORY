import json
import os
import re
from contextlib import asynccontextmanager

import anthropic
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
if not os.getenv("ANTHROPIC_API_KEY"):
    load_dotenv(dotenv_path="../.env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CALCOM_API_KEY = os.getenv("CALCOM_API_KEY")
CALCOM_BASE_URL = "https://api.cal.com/v2"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
CLAUDE_MODEL = "claude-sonnet-5"

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


# 3. MOTEUR IA (Claude)

# État de risque par conversation (en mémoire : suffisant pour le MVP,
# se réinitialise si le serveur redémarre ou tourne sur plusieurs instances).
SESSION_STATE: dict = {}

def get_session_state(session_id: str) -> dict:
    if session_id not in SESSION_STATE:
        SESSION_STATE[session_id] = {"niveau_max": 1, "parcours_actif": None, "niveau4_count": 0}
    return SESSION_STATE[session_id]

# Timeout appliqué à chaque appel Claude : sans ça, une requête en attente de rate-limit
# ou de retentative interne du SDK peut traîner plusieurs minutes avant de remonter
# l'erreur, ce qui bloque l'utilisateur en silence.
CLAUDE_TIMEOUT_CHAT = 25.0
CLAUDE_TIMEOUT_CLASSIFICATION = 15.0


def _format_history(history: list) -> list:
    """Normalise l'historique (y compris les exemples few-shot) au format Claude."""
    formatted = []
    for h in history:
        role = h.get("role", "user")
        if role == "model":
            role = "assistant"
        elif role not in ("user", "assistant"):
            role = "user"
        content = h.get("content", h.get("parts", ""))
        if isinstance(content, list):
            content = " ".join(str(c) for c in content)
        formatted.append({"role": role, "content": content})
    return formatted


def generate_reply(message: str, history: list, system_instruction: str) -> str:
    """Passe 2 : génération de la réponse conversationnelle de Thera."""
    formatted = _format_history(history)
    # L'API Claude exige que le premier message soit de rôle "user" ; si l'historique
    # commence par un tour "assistant" (ex. l'exemple few-shot d'amorçage), on l'amorce
    # avec un tour utilisateur synthétique pour rester valide.
    if formatted and formatted[0]["role"] != "user":
        formatted = [{"role": "user", "content": "Bonjour"}] + formatted
    formatted.append({"role": "user", "content": message})

    response = client.with_options(timeout=CLAUDE_TIMEOUT_CHAT).messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system_instruction,
        messages=formatted,
    )
    return next(block.text for block in response.content if block.type == "text")


class RiskClassification(BaseModel):
    niveau: int
    categories_detectees: list[str]
    parcours_probable: str
    confiance: float
    justification_courte: str


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

Barème :
1 = échange standard, pas de signal de détresse particulier
2 = signal de mal-être modéré
3 = détresse aiguë nécessitant une orientation rapide vers un professionnel
4 = urgence vitale (idées suicidaires explicites, danger immédiat pour soi ou autrui)

Le parcours_probable doit être une lettre parmi A,B,C,D,E,F,G,H.
Ne descends jamais en dessous du niveau {niveau_max_session} sans justification majeure explicite dans le dernier message.
"""
    try:
        response = client.with_options(timeout=CLAUDE_TIMEOUT_CLASSIFICATION).messages.parse(
            model=CLAUDE_MODEL,
            max_tokens=512,
            system=RISK_CLASSIFICATION_INSTRUCTION,
            messages=[{"role": "user", "content": prompt}],
            output_format=RiskClassification,
        )
        data = response.parsed_output

        niveau = max(1, min(4, data.niveau))
        parcours = data.parcours_probable.strip().upper()
        if parcours not in MODULES_PARCOURS:
            parcours = "A"

        return {
            "niveau": niveau,
            "categories_detectees": data.categories_detectees,
            "parcours_probable": parcours,
        }
    except Exception as e:
        print(f"⚠️ Classification de risque indisponible ({e}), repli sur niveau 1 / parcours A.")
        return {"niveau": 1, "categories_detectees": [], "parcours_probable": "A"}


# 4. Routes de l'API

# Filet de sécurité rapide par mots-clés : défense en profondeur, ne dépend pas du LLM.
MOTS_CLES_URGENCE = ["suicide", "en finir", "mourir", "plus envie de vivre", "tout stopper", "me faire du mal", "me tuer"]

# Tournures figurées où ces mots-clés apparaissent sans signal de détresse réel : on les
# retire du texte avant la recherche, pour éviter qu'un "mourir de rire" déclenche à tort
# le niveau 4 (et bloque la session en mode crise pour le reste de la conversation).
EXPRESSIONS_FIGUREES_A_IGNORER = [
    "mourir de rire", "mort de rire", "mdr", "mourir de faim", "mourir de honte",
    "mourir d'ennui", "mourir de chaud", "à en mourir de rire",
]

def contient_signal_urgence(message: str) -> bool:
    texte = message.lower()
    for expression in EXPRESSIONS_FIGUREES_A_IGNORER:
        texte = texte.replace(expression, " ")
    return any(re.search(rf"\b{re.escape(mot)}\b", texte) for mot in MOTS_CLES_URGENCE)


# Réponse niveau 4 : volontairement figée (pas d'improvisation du LLM face à un danger vital),
# mais déclinée en tu/vous et variée entre le premier message et les suivants dans la même
# session, pour ne pas répéter mot pour mot la même phrase si la personne continue d'écrire.
MESSAGE_URGENCE_INITIAL_TU = (
    "Ce que tu me dis m'inquiète beaucoup. Je ne peux pas t'accompagner seul(e) sur ça, il faut "
    "qu'on te mette en lien avec quelqu'un maintenant. Voici le 3114, le numéro national de "
    "prévention du suicide, gratuit et disponible 24h/24."
)
MESSAGE_URGENCE_INITIAL_VOUS = (
    "Ce que vous me dites m'inquiète beaucoup. Je ne peux pas vous accompagner seul(e) sur ça, il "
    "faut qu'on vous mette en lien avec quelqu'un maintenant. Voici le 3114, le numéro national de "
    "prévention du suicide, gratuit et disponible 24h/24."
)
MESSAGES_URGENCE_SUIVANTS_TU = [
    "Je reste inquiète pour toi. Le 3114 est toujours là, gratuitement et 24h/24, si tu veux parler à quelqu'un maintenant.",
    "Ce que tu me dis reste très préoccupant. Le 3114 peut t'écouter à tout moment, gratuitement et 24h/24 : c'est fait pour ça.",
]
MESSAGES_URGENCE_SUIVANTS_VOUS = [
    "Je reste inquiète pour vous. Le 3114 est toujours là, gratuitement et 24h/24, si vous voulez parler à quelqu'un maintenant.",
    "Ce que vous me dites reste très préoccupant. Le 3114 peut vous écouter à tout moment, gratuitement et 24h/24 : c'est fait pour ça.",
]
MOTS_VOUVOIEMENT = re.compile(r"\bvous\b", re.IGNORECASE)


def message_urgence(message_utilisateur: str, rang_alerte: int) -> str:
    """rang_alerte : 0 pour la première alerte niveau 4 de la session, 1+ pour les suivantes."""
    vouvoiement = bool(MOTS_VOUVOIEMENT.search(message_utilisateur))
    if rang_alerte == 0:
        return MESSAGE_URGENCE_INITIAL_VOUS if vouvoiement else MESSAGE_URGENCE_INITIAL_TU
    variantes = MESSAGES_URGENCE_SUIVANTS_VOUS if vouvoiement else MESSAGES_URGENCE_SUIVANTS_TU
    return variantes[(rang_alerte - 1) % len(variantes)]


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
    if not ANTHROPIC_API_KEY:
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

    alerte_mot_cle = contient_signal_urgence(chat.message)
    classification = classify_risk(chat.message, chat.history, state["niveau_max"])

    niveau = max(classification["niveau"], state["niveau_max"], 4 if alerte_mot_cle else 0)
    state["niveau_max"] = niveau

    # Niveau 4 : urgence vitale, on court-circuite la génération conversationnelle.
    if niveau == 4:
        db.log_crisis_event(session_id, 4, classification["categories_detectees"], "urgence_vitale_hotline_affichee")
        reponse = message_urgence(chat.message, state["niveau4_count"])
        state["niveau4_count"] += 1
        return {
            "status": "success",
            "reply": reponse,
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

    full_history = FEW_SHOT_EXAMPLES + chat.history

    try:
        reponse_texte = generate_reply(chat.message, full_history, final_system_instruction)
        return {
            "status": "success",
            "reply": reponse_texte,
            "security": "verified",
            "model_used": CLAUDE_MODEL,
            "niveau_risque": niveau,
            "parcours_actif": parcours_actif,
        }
    except Exception as e:
        return {"status": "error", "reply": f"Erreur API Claude : {str(e)}"}


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