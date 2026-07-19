import os
from dotenv import load_dotenv
from google import genai

def selectionner_projet():
    print("\n==============================================")
    print(" 🎩 AGENT PO - ENRICHISSEMENT DU CAHIER DES CHARGES")
    print("==============================================\n")
    
    dossiers = [d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".")]
    if not dossiers:
        print("❌ Aucun dossier de projet trouvé.")
        exit()
        
    for i, dossier in enumerate(dossiers, 1):
        print(f"[{i}] {dossier}")
        
    choix = input("\n👉 Pour quel projet veux-tu enrichir le PRD ? (Tape le numéro) : ")
    
    try:
        index = int(choix) - 1
        return dossiers[index]
    except:
        print("❌ Choix invalide.")
        exit()

def executer_po():
    projet = selectionner_projet()
    
    load_dotenv(dotenv_path=".env")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("❌ Erreur : Clé API introuvable.")
        exit()

    # Recherche du formulaire brut
    chemin_prd_brut = None
    for racine, _, fichiers in os.walk(projet):
        for f in fichiers:
            if f.startswith("PRD_") and f.endswith(".txt") and not "ENRICHI" in f:
                chemin_prd_brut = os.path.join(racine, f)
                break
        if chemin_prd_brut:
            break
            
    if not chemin_prd_brut:
        print(f"❌ Aucun formulaire PRD initial trouvé dans le dossier {projet}.")
        exit()

    try:
        with open(chemin_prd_brut, "r", encoding="utf-8") as f:
            contenu_brut = f.read()
    except Exception as e:
        print(f"❌ Impossible de lire le fichier : {e}")
        exit()

    print("🧠 L'Agent PO analyse le domaine et rédige les User Stories au format BDD...")
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Tu es un Product Owner Super Senior.
    Voici le formulaire brut d'une idée de produit :
    {contenu_brut}
    
    Mission :
    Transforme ce brouillon en un PRD exhaustif et un Backlog de niveau professionnel.
    
    🚨 RÈGLE ANTI-OUBLI STRICTE : 
    Tu as l'interdiction formelle de supprimer, d'ignorer ou de filtrer la moindre fonctionnalité mentionnée dans le brouillon initial (même s'il s'agit d'une fonctionnalité qui te semble secondaire, comme des podcasts, des exercices de respiration, etc.). TOUT ce qui est demandé dans le brouillon DOIT être traduit en Epic et User Stories.
    
    Méthodologie (Le Caméléon) :
    Détecte le domaine d'activité. 
    - Si c'est de la Santé/IA : Applique les contraintes de l'AI Act et du DSM-5.
    - Si c'est de l'E-commerce/IoT : Applique les logiques de traçabilité, de conversion et d'UX transactionnelle.
    
    Structure OBLIGATOIRE du document de sortie :
    # 1. VISION ET CONTEXTE
    [Synthèse experte]
    
    # 2. PERSONAS ET PARCOURS UTILISATEURS
    [Détail des cibles]
    
    # 3. CONTRAINTES LÉGALES ET TECHNIQUES (EDGE CASES)
    [Règles d'or à respecter pour l'architecture et les cas d'erreurs]
    
    # 4. EPIC BACKLOG & USER STORIES (Format BDD)
    [Pour chaque fonctionnalité demandée, crée un bloc strict]
    - Titre de la fonctionnalité
    - En tant que... Je veux... Afin de...
    - Critères d'acceptation (Étant donné que... Quand... Alors...)
    
    Ne génère aucun blabla introductif. Renvoie uniquement le texte du PRD enrichi, structuré en Markdown.
    """

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt
        )
        prd_enrichi = response.text.strip()
    except Exception as e:
        print(f"❌ Erreur lors de la génération : {e}")
        exit()

    dossier_build = os.path.join(projet, "2-readytobuild")
    os.makedirs(dossier_build, exist_ok=True)
    chemin_sortie = os.path.join(dossier_build, "PRD_ENRICHI.txt")
    
    try:
        with open(chemin_sortie, "w", encoding="utf-8") as f:
            f.write(prd_enrichi)
        print(f"\n✅ Le cahier des charges expert a été généré avec succès : {chemin_sortie}")
        print("💡 L'Agent Architecte (CTO) devra maintenant lire CE fichier pour créer la base de données.")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde : {e}")

if __name__ == "__main__":
    executer_po()