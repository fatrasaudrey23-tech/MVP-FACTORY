import json
# Import fictif pour ton LLM (OpenAI, Gemini, Mistral...)
# from ton_module_llm import appeler_llm_json, appeler_llm_texte 

def passe_1_detection(message_utilisateur: str, historique: list, session: SessionState) -> dict:
    """
    Passe 1 : Classification du risque. Ne génère pas de texte pour l'utilisateur.
    Renvoie un JSON strict avec le niveau de risque.
    """
    prompt_classification = f"""
    Tu es un module de classification de risque.
    Historique : {historique}
    Dernier message : {message_utilisateur}
    Niveau max atteint : {session.niveau_risque_max_session}
    
    Renvoie UNIQUEMENT un JSON avec : niveau (1-4), categories_detectees, parcours_probable, confiance, justification_courte.
    Ne descends jamais en dessous du niveau max atteint sans justification majeure.
    """
    
    # Appel au LLM configuré pour renvoyer du JSON
    # reponse_json = appeler_llm_json(prompt_classification)
    
    # Simulation de réponse pour l'exemple
    reponse_json = {
        "niveau": 1, 
        "categories_detectees": [],
        "parcours_probable": "A",
        "confiance": 0.9,
        "justification_courte": "Message standard."
    }
    return reponse_json


def passe_2_generation(message_utilisateur: str, historique: list, session: SessionState) -> str:
    """
    Passe 2 : Génération de la réponse conversationnelle selon le niveau de risque.
    """
    # 1. GESTION DES URGENCES (Niveau 4)
    if session.niveau_risque_actuel == 4:
        session.escalade_niveau4_declenchee = True
        return "Ce que tu me dis m'inquiète beaucoup. Je ne peux pas t'accompagner seul(e) sur ça. Voici le 3114, le numéro national de prévention du suicide, gratuit et disponible 24h/24. Veux-tu que je t'aide à les contacter ?"

    # 2. GESTION DES VIGILANCES (Niveau 3)
    if session.niveau_risque_max_session == 3:
        session.escalade_niveau3_declenchee = True
        prompt_maitre = "PROMPT_MAITRE_TEXTE" # À charger depuis tes fichiers
        module_f_niveau3 = "INSTRUCTIONS_MODULE_F_NIVEAU_3" # À charger
        prompt_final = f"{prompt_maitre}\n{module_f_niveau3}\nHistorique: {historique}\nMessage: {message_utilisateur}"
        
        # reponse = appeler_llm_texte(prompt_final)
        return "Génération avec ton d'urgence niveau 3..."

    # 3. GESTION STANDARD (Niveaux 1 et 2)
    prompt_maitre = "PROMPT_MAITRE_TEXTE"
    # Sélection dynamique du module (A, B, C...) selon la session
    module_actif = f"INSTRUCTIONS_MODULE_{session.parcours_actif}" 
    
    prompt_final = f"{prompt_maitre}\n{module_actif}\nHistorique: {historique}\nMessage: {message_utilisateur}"
    
    # reponse = appeler_llm_texte(prompt_final)
    return "Génération standard de la réponse par l'IA..."