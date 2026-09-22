import os
import re
import json
import statistics
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from supabase import create_client, Client
from postgrest.exceptions import APIError
import anthropic
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Forcer le chemin absolu vers le fichier .env de la factory
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(base_dir, '.env'))

supabase_url = os.getenv("SUPABASE_URL")
supabase_key_admin = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# --- BLOC DE NETTOYAGE CHIRURGICAL ET DIAGNOSTIC ---
print("🔍 [DIAGNOSTIC SÉCURITÉ BACKEND]")
if not supabase_url:
    print("  ❌ SUPABASE_URL est manquante dans le .env")

if not supabase_key_admin:
    print("  ❌ SUPABASE_SERVICE_ROLE_KEY est manquante dans le .env")
else:
    # Nettoyage absolu des espaces, retours à la ligne (\n, \r) et guillemets parasites
    supabase_key_admin = supabase_key_admin.strip().replace("\n", "").replace("\r", "").replace('"', '').replace("'", "")
    print(f"  ✅ Clé SERVICE_ROLE détectée et nettoyée (Longueur : {len(supabase_key_admin)} car.)")
# ---------------------------------------------------

if not supabase_url or not supabase_key_admin:
    raise RuntimeError("Impossible de démarrer le serveur sans URL ou sans la clé SERVICE_ROLE.")

# Initialisation sécurisée du client Supabase avec la clé d'administration (bypasse le RLS pour la factory)
supabase: Client = create_client(supabase_url, supabase_key_admin)

# --- Client Anthropic (Claude) pour la génération de menus ---
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if anthropic_api_key:
    anthropic_api_key = anthropic_api_key.strip().replace("\n", "").replace("\r", "").replace('"', '').replace("'", "")
claude_client: Optional[anthropic.Anthropic] = anthropic.Anthropic(api_key=anthropic_api_key) if anthropic_api_key else None
CLAUDE_MODEL = "claude-sonnet-5"
# Timeout généreux : la génération d'un menu de 7 jours (recettes + liste de courses
# structurée) est une sortie volumineuse, plus longue à produire qu'un simple chat — des
# runs à 72-86s ont été observés en conditions normales, 60s déclenchait donc parfois un
# "read operation timed out" sur des générations pourtant valides (2026-09-12).
CLAUDE_TIMEOUT_MENU = 100.0

# --- Clé d'administration pour les routes non destinées au frontend public
# (lecture en masse de données personnelles, écriture directe dans les tables) ---
admin_api_key = os.getenv("ADMIN_API_KEY")
if admin_api_key:
    admin_api_key = admin_api_key.strip().replace("\n", "").replace("\r", "").replace('"', '').replace("'", "")
if not admin_api_key:
    print("  ⚠️ ADMIN_API_KEY manquante : les routes d'administration sont désactivées.")

def verifier_cle_admin(x_admin_key: Optional[str] = Header(None)):
    if not admin_api_key or x_admin_key != admin_api_key:
        raise HTTPException(status_code=401, detail="Clé d'administration manquante ou invalide.")

app = FastAPI(title="EcoMenu API", version="1.0.0")

# --- Limitation de débit (protège notamment les appels payants à Claude) ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuration du CORS : uniquement les origines du frontend, pas de wildcard
origines_autorisees = [
    o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origines_autorisees,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)

@app.get("/")
def read_root():
    return {"status": "online", "security": "high", "project": "EcoMenu"}

# ==========================================
# SCHÉMAS DE VALIDATION PYDANTIC
# ==========================================

class UsersSchema(BaseModel):
    budget_max: Optional[float] = Field(default=None, ge=10, le=2000)
    taille_foyer: Optional[int] = Field(default=None, ge=1, le=20)
    nb_adultes: Optional[int] = Field(default=None, ge=0, le=12)
    nb_enfants: Optional[int] = Field(default=None, ge=0, le=12)
    gestion_restes: Optional[bool] = None
    type_boite_lunch: Optional[str] = None
    profil_boite_lunch: Optional[str] = None
    # Garde-manger : ce que le foyer a déjà (jamais remis sur la liste de courses)
    garde_manger: Optional[List[str]] = Field(default=None, max_length=30)
    # Achats fixes achetés chaque semaine, indépendamment des promotions (ex. riz, pâtes)
    achats_recurrents: Optional[List[str]] = Field(default=None, max_length=15)
    # Incontournables : plats/ingrédients voulus dans le menu, promo ou non
    incontournables: Optional[List[str]] = Field(default=None, max_length=10)

class EnseignesSchema(BaseModel):
    nom: Optional[str] = None
    logo_url: Optional[str] = None
    actif: Optional[bool] = None

class Enseigne_selectionSchema(BaseModel):
    user_id: Optional[str] = None
    enseigne_id: Optional[str] = None

class PromotionsSchema(BaseModel):
    enseigne: Optional[str] = None
    nom_produit: Optional[str] = None
    prix_promo: Optional[float] = None
    prix_origine: Optional[float] = None
    poids_volume: Optional[str] = None
    unite_mesure: Optional[str] = None
    categorie_alimentaire: Optional[str] = None

class Produit_tagsSchema(BaseModel):
    nom_produit: Optional[str] = None
    tag_standard: Optional[str] = None

class MenusSchema(BaseModel):
    user_id: Optional[str] = None
    menu_data: Optional[dict] = None
    date_generated: Optional[str] = None

# ==========================================
# GÉNÉRATION DE MENU PAR IA (Just-In-Time)
# ==========================================

class GenerateMenuRequest(BaseModel):
    user_id: str

# Catégories de protéines utilisées pour forcer la diversité du menu, inspirées du
# Guide alimentaire canadien (varier les sources de protéines, intégrer du poisson
# et des légumineuses, ne pas se limiter à un seul type de viande).
CATEGORIES_PROTEINE = [
    "viande_rouge",
    "volaille",
    "poisson_fruits_mer",
    "legumineuses_tofu",
    "oeufs",
    "produits_laitiers",
    "vegetalien_leger",
]

# Formats de repas actuellement populaires en cuisine maison, pour éviter des menus fades
# de type "protéine + légume + féculent" répété sans imagination chaque jour.
STYLES_TENDANCE = [
    "Bowl",
    "One-pan / plaque unique",
    "Tacos ou wraps",
    "Stir-fry / sauté asiatique",
    "Fusion méditerranéenne",
    "Comfort food revisité",
    "Meal-prep",
    "Cuisine de rue (street food)",
    "Classique réconfortant",
]

class RecetteJour(BaseModel):
    jour: str
    repas_soir: str
    style_tendance: str
    temps_preparation_min: int
    eco_score: str
    categorie_proteine: str
    ingredient_phare: str
    enseigne_ingredient_phare: Optional[str] = None
    boite_lunch_midi: Optional[str] = None
    # Ingrédient principal du lunch, distinct de celui du souper quand boite_lunch_midi
    # est une recette à part entière (ex. "repas froids spécifiques") — permet de vérifier
    # côté serveur que la liste de courses couvre aussi les lunchs, pas seulement les
    # soupers (chantier du 2026-09-22, cf. garantir_ingredients_phares).
    ingredient_phare_lunch: Optional[str] = None

class ArticleCourse(BaseModel):
    nom_produit: str
    quantite: str
    enseigne: Optional[str] = None
    prix: Optional[float] = None  # calculé côté serveur, jamais fourni par le LLM

class ListeCourses(BaseModel):
    section_circulaire: List[ArticleCourse]
    section_fond_de_placard: List[ArticleCourse]

class MenuGenere(BaseModel):
    budget_respecte: bool
    jours_couverts: int
    message_avertissement: Optional[str] = None
    menu_semaine: List[RecetteJour]
    liste_courses: ListeCourses
    cout_estime_total: float
    economies_estimees: float

# ==========================================
# ROUTES SÉCURISÉES (GET & POST)
# ==========================================

@app.get("/api/v1/users", tags=["users"], response_model=List[dict], dependencies=[Depends(verifier_cle_admin)])
def get_users():
    try:
        response = supabase.table("users").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")

@app.post("/api/v1/users", tags=["users"], response_model=List[dict])
@limiter.limit("10/minute")
def create_users(request: Request, data: UsersSchema):
    try:
        payload = data.dict(exclude_unset=True)
        response = supabase.table("users").insert(payload).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")

@app.get("/api/v1/enseignes", tags=["enseignes"], response_model=List[dict])
def get_enseignes():
    try:
        response = supabase.table("enseignes").select("*").order("nom").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")

@app.post("/api/v1/enseignes", tags=["enseignes"], response_model=List[dict], dependencies=[Depends(verifier_cle_admin)])
def create_enseignes(data: EnseignesSchema):
    try:
        payload = data.dict(exclude_unset=True)
        response = supabase.table("enseignes").insert(payload).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")

@app.get("/api/v1/enseigne_selection", tags=["enseigne_selection"], response_model=List[dict], dependencies=[Depends(verifier_cle_admin)])
def get_enseigne_selection():
    try:
        response = supabase.table("enseigne_selection").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")

@app.post("/api/v1/enseigne_selection", tags=["enseigne_selection"], response_model=List[dict])
@limiter.limit("30/minute")
def create_enseigne_selection(request: Request, data: Enseigne_selectionSchema):
    try:
        payload = data.dict(exclude_unset=True)
        response = supabase.table("enseigne_selection").insert(payload).execute()
        return response.data
    except APIError as e:
        if e.code == "23505":  # violation de la contrainte UNIQUE(user_id, enseigne_id)
            raise HTTPException(status_code=409, detail="Cette enseigne est déjà sélectionnée pour ce foyer.")
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")

@app.get("/api/v1/promotions", tags=["promotions"], response_model=List[dict])
def get_promotions():
    try:
        response = supabase.table("promotions").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")

@app.post("/api/v1/promotions", tags=["promotions"], response_model=List[dict], dependencies=[Depends(verifier_cle_admin)])
def create_promotions(data: PromotionsSchema):
    try:
        payload = data.dict(exclude_unset=True)
        response = supabase.table("promotions").insert(payload).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")

@app.get("/api/v1/produit_tags", tags=["produit_tags"], response_model=List[dict])
def get_produit_tags():
    try:
        response = supabase.table("produit_tags").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")

@app.post("/api/v1/produit_tags", tags=["produit_tags"], response_model=List[dict], dependencies=[Depends(verifier_cle_admin)])
def create_produit_tags(data: Produit_tagsSchema):
    try:
        payload = data.dict(exclude_unset=True)
        response = supabase.table("produit_tags").insert(payload).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")

@app.get("/api/v1/menus", tags=["menus"], response_model=List[dict], dependencies=[Depends(verifier_cle_admin)])
def get_menus():
    try:
        response = supabase.table("menus").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")

@app.post("/api/v1/menus", tags=["menus"], response_model=List[dict], dependencies=[Depends(verifier_cle_admin)])
def create_menus(data: MenusSchema):
    try:
        payload = data.dict(exclude_unset=True)
        response = supabase.table("menus").insert(payload).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")


# Quotas par catégorie pour la sélection des promotions envoyées au LLM : évite que les
# 15 promos retenues soient seulement "les moins chères" (biais vers pâtes/conserves qui
# écarte systématiquement poisson et viande, plus chers). Total = 15 : testé empiriquement
# contre 23 (quotas x~1.5), qui donnait MOINS bien sur l'utilisation du budget (76.7% de
# moyenne sur 3 runs vs 88.7% avec 15, même profil) sans gain de diversité observable —
# plus de choix semble donner au LLM plus d'options "bon marché" pour satisfaire ses
# propres contraintes de diversité sans avoir besoin de remplir le budget.
# "Prêt-à-manger" est volontairement exclu : c'est justement la catégorie des repas
# préparés/transformés (soupes en conserve, plats surgelés, macaroni en boîte) qu'on veut
# éviter comme base des recettes générées.
QUOTAS_CATEGORIE_PROMO = {
    "Boucherie": 3,
    "Poissonnerie": 3,
    "Fruits & Légumes": 3,
    "Produits Laitiers": 2,
    "Charcuterie": 1,
    "Boulangerie": 1,
    "Surgelés": 1,
    "Épicerie": 1,
}

# Mots-clés identifiant un repas préparé/transformé (soupe en conserve, plat surgelé
# prêt-à-manger, macaroni en boîte...) — ces produits sont retirés du bassin de promos
# proposé au LLM pour qu'il ne les choisisse jamais comme base d'une recette, même si
# leur categorie_alimentaire n'est pas "Prêt-à-manger" (classification parfois imparfaite).
MOTS_REPAS_PREPARE = [
    "soupe", "soup", "dîner", "diner irrésistible", "kraft dinner", "repas préparé", "repas pour",
    "prêt-à-manger", "pret-a-manger", "c'est prêt", "macaroni en boîte", "nouilles instantanées",
    "plat surgelé prêt", "lasagne surgelée", "pâté chinois surgelé", "pizza", "croquette", "sandwich",
]


def _motif_pluriel(terme_lower: str) -> str:
    """Construit le fragment regex d'un terme (un ou plusieurs mots) en tolérant un "s"
    optionnel APRÈS CHAQUE MOT plutôt qu'à la toute fin de la phrase : pour "tortilla de
    blé entier", le mot qui se pluralise au marché est le premier ("tortillaS de blé
    entier"), pas le dernier — un "s?" placé seulement en fin de phrase ne matchait donc
    jamais ce cas et créait un doublon dans la liste de courses (garantir_ingredients_phares
    rajoutait "Tortilla de blé entier" en plus de "tortillas de blé entier" déjà présent,
    constaté le 2026-09-22). Comme on ne sait pas a priori quel mot pluralise en français,
    on tolère le "s" sur chacun."""
    mots = terme_lower.split()
    return r"\s+".join(re.escape(m) + r"s?" for m in mots)


def contient_mot_entier(texte_lower: str, mots) -> bool:
    """Comme `any(mot in texte_lower for mot in mots)` mais avec limite de mot (\\b) :
    empêche un mot-clé court de matcher comme simple sous-chaîne d'un mot plus long sans
    rapport — ex. "ail" dans "caille" (caille = viande, pas de l'ail), "lait" dans
    "laitue". Plusieurs cas concrets trouvés lors de tests le 2026-09-15, d'abord corrigés
    dans trouver_promo_pour_terme puis généralisés ici à toutes les listes de mots-clés du
    fichier (catégorisation, condiments, repas préparés).
    Tolère un "s" optionnel après chaque mot (pluriel, cf. _motif_pluriel) : un mot-clé au
    singulier ("tortilla", "carotte"...) doit quand même matcher un nom de produit au
    pluriel ("Tortillas de blé entier", "Carottes nantaises"...), la forme la plus
    courante en épicerie — régression constatée le 2026-09-21 sur "tortilla"/"Tortillas"
    (retombait sur le plafond de 20$ au lieu de son prix unitaire connu de 0,50$, faute de
    correspondre au pluriel)."""
    return any(re.search(r"\b" + _motif_pluriel(mot) + r"\b", texte_lower) for mot in mots)


# Faux-amis alimentaires : le terme cherché est un VRAI mot entier dans le nom du produit,
# mais désigne un aliment complètement différent une fois composé — "pomme(s)" dans
# "pomme(s) de terre" (patate, pas le fruit) en est l'exemple trouvé le 2026-09-15 (un
# utilisateur demandant "pommes" en incontournable se voyait "satisfait" par des patates
# déjà présentes pour une autre recette). \b seul ne peut pas détecter ce cas puisque
# "pomme" y est un vrai mot, pas une sous-chaîne — d'où cette liste d'exclusions dédiée,
# appliquée par motif_terme_recherche() partout où un terme utilisateur est recherché.
EXCLUSIONS_FAUX_AMIS = {
    "pomme": r"\s+de\s+terre",
    "pommes": r"\s+de\s+terre",
}


def motif_terme_recherche(terme_lower: str, ancre_debut: bool = False) -> re.Pattern:
    """Regex \\b pour un terme cherché (nom d'aliment libre saisi par l'utilisateur),
    avec exclusion des faux-amis connus (cf. EXCLUSIONS_FAUX_AMIS). ancre_debut=True
    ancre le motif au tout début de la chaîne (^), pour la correspondance "premier mot"
    prioritaire de trouver_promo_pour_terme. Tolère un "s" optionnel après chaque mot
    (pluriel, cf. _motif_pluriel) : un utilisateur tapant "pomme" doit quand même trouver
    "Pommes rouges du Québec", et "tortilla de blé entier" doit trouver "Tortillas de blé
    entier" sans dupliquer l'article (le "s" se place sur le bon mot, pas juste en fin de
    phrase — régression corrigée le 2026-09-22)."""
    motif = (r"^" if ancre_debut else r"\b") + _motif_pluriel(terme_lower) + r"\b"
    exclusion = EXCLUSIONS_FAUX_AMIS.get(terme_lower)
    if exclusion:
        motif += r"(?!" + exclusion + r")"
    return re.compile(motif)


def est_repas_prepare(nom_produit: str) -> bool:
    nom_lower = (nom_produit or "").lower()
    return contient_mot_entier(nom_lower, MOTS_REPAS_PREPARE)


def selectionner_promos_diversifiees(promos: List[dict], total: int = 15) -> List[dict]:
    # Exclusion complète (pas juste du quota) : sinon la boucle de remplissage plus bas,
    # qui complète avec "les moins chères toutes catégories confondues" quand les quotas
    # ne suffisent pas à atteindre 15, peut quand même repêcher un plat préparé.
    promos = [
        p for p in promos
        if p.get("categorie_alimentaire") != "Prêt-à-manger" and not est_repas_prepare(p.get("nom_produit"))
    ]

    par_categorie: dict = {}
    for p in promos:
        cat = p.get("categorie_alimentaire") or "Épicerie"
        par_categorie.setdefault(cat, []).append(p)

    selection = []
    for cat, quota in QUOTAS_CATEGORIE_PROMO.items():
        selection.extend(par_categorie.get(cat, [])[:quota])

    deja_pris_ids = {p["id"] for p in selection}
    for p in promos:  # comble le reste avec les moins chères toutes catégories confondues
        if len(selection) >= total:
            break
        if p["id"] not in deja_pris_ids:
            selection.append(p)
            deja_pris_ids.add(p["id"])

    return selection[:total]


def verifier_diversite_menu(menu: MenuGenere) -> Optional[str]:
    """Retourne une explication si le menu manque de diversité (protéines ou styles
    tendance), sinon None. Les deux checks alimentent le même signal de relance : un menu
    peut varier ses protéines tout en répétant le même style (ex. 4x "Bowl" sur 7 jours),
    ce qui donnait tout de même une impression de menu peu inspiré malgré diversite_ok."""
    categories = [j.categorie_proteine for j in menu.menu_semaine]
    styles = [j.style_tendance for j in menu.menu_semaine]
    n = len(categories)
    if n == 0:
        return None

    compte_proteines: dict = {}
    for c in categories:
        compte_proteines[c] = compte_proteines.get(c, 0) + 1
    categorie_dominante, occurrences = max(compte_proteines.items(), key=lambda kv: kv[1])

    if occurrences > max(3, (n // 2) + 1):
        return f"trop de répétitions de la catégorie '{categorie_dominante}' ({occurrences}/{n} jours)"
    if n >= 4 and compte_proteines.get("poisson_fruits_mer", 0) == 0:
        return "aucun repas de poisson ou fruits de mer sur un menu de 4 jours ou plus"

    compte_styles: dict = {}
    for s in styles:
        compte_styles[s] = compte_styles.get(s, 0) + 1
    style_dominant, occurrences_style = max(compte_styles.items(), key=lambda kv: kv[1])
    # Seuil plus strict que pour les protéines : répéter "volaille" plusieurs fois dans la
    # semaine est normal, répéter le même format de recette (ex. "Bowl") l'est moins, avec
    # 9 styles disponibles dans STYLES_TENDANCE.
    if occurrences_style > max(2, (n // 3) + 1):
        return f"trop de répétitions du style '{style_dominant}' ({occurrences_style}/{n} jours)"

    return None


def construire_prompt(
    user: dict,
    promos: List[dict],
    note_diversite: Optional[str] = None,
    note_sous_budget: Optional[str] = None,
    note_depassement: Optional[str] = None,
) -> str:
    liste_promos = "\n".join(
        f"- {p.get('nom_produit')} | {p.get('categorie_alimentaire') or 'Épicerie'} | "
        f"{p.get('prix_promo')}$ ({p.get('poids_volume') or ''} {p.get('unite_mesure') or ''}) chez {p.get('enseigne')}"
        for p in promos
    )

    boite_lunch = "Non activée."
    if user.get("gestion_restes"):
        type_lunch = user.get("type_boite_lunch")
        profil_lunch = user.get("profil_boite_lunch")
        if type_lunch == "restes":
            boite_lunch = (
                f"Activée — type : réutilisation des restes, profil : {profil_lunch or 'non précisé'}. "
                "Le lunch du lendemain doit réutiliser le repas du soir précédent (même base, présenté "
                "pour être mangé froid ou réchauffé)."
            )
        elif type_lunch == "specifique":
            # Chantier du 2026-09-22 : ce mode n'avait jusqu'ici aucune consigne dédiée et le
            # LLM se rabattait par défaut sur la même logique que "restes" (recycler la
            # protéine du souper), sans réel repas de lunch distinct ni égard pour un profil
            # enfant — testé et confirmé sur un lunch "wrap de porc haché ÉPICÉ" pour un
            # profil enfant, aucune prise en compte des allergènes ou des goûts d'enfant.
            if profil_lunch == "enfants":
                boite_lunch = (
                    "Activée — type : repas froids spécifiques, profil : enfants. Chaque "
                    "boite_lunch_midi doit être une recette de lunch froid À PART ENTIÈRE, "
                    "pas simplement le souper recyclé — même si elle peut réutiliser un "
                    "ingrédient déjà acheté pour limiter le coût. Adapte-la à des goûts "
                    "d'enfant : saveurs douces et familières (JAMAIS épicé/piquant/fort en "
                    "assaisonnement), formats simples à manger froid et à l'école (sandwich, "
                    "wrap doux, pâtes froides, pochette de légumes/fruits coupés avec trempette, "
                    "muffin maison, fromage en cubes...), portion d'enfant. SANS ARACHIDES NI "
                    "NOIX (allergènes les plus communément interdits dans les écoles "
                    "québécoises) — jamais de beurre d'arachide même si l'enfant pourrait "
                    "l'aimer. Varie les lunchs sur la semaine plutôt que de répéter la même "
                    "base tous les jours."
                )
            else:
                boite_lunch = (
                    f"Activée — type : repas froids spécifiques, profil : {profil_lunch or 'adultes'}. "
                    "Chaque boite_lunch_midi doit être une recette de lunch froid À PART "
                    "ENTIÈRE, pas simplement le souper recyclé — même si elle peut réutiliser "
                    "un ingrédient déjà acheté pour limiter le coût. Formats adaptés à un lunch "
                    "transporté et mangé froid (salade composée, wrap, bowl froid, pâtes "
                    "froides...). Varie les lunchs sur la semaine plutôt que de répéter la "
                    "même base tous les jours."
                )
        else:
            boite_lunch = f"Activée — type : {type_lunch or 'non précisé'}, profil : {profil_lunch or 'non précisé'}."

    garde_manger = user.get("garde_manger") or []
    achats_recurrents = user.get("achats_recurrents") or []

    nb_adultes = user.get("nb_adultes")
    nb_enfants = user.get("nb_enfants")
    composition_foyer = f"{user.get('taille_foyer')} personne(s)"
    consigne_portions = f"pour nourrir {user.get('taille_foyer')} personnes"
    if nb_adultes is not None and nb_enfants is not None:
        composition_foyer = f"{nb_adultes} adulte(s) et {nb_enfants} enfant(s)"
        # Portion enfant ≈ 60% d'une portion adulte pour les quantités (viande, féculents...),
        # tout en donnant à chaque enfant une part complète du repas — pas juste un peu moins.
        equivalent_adultes = round(nb_adultes + nb_enfants * 0.6, 1)
        consigne_portions = (
            f"pour {nb_adultes} adulte(s) et {nb_enfants} enfant(s) — compte chaque enfant "
            f"comme environ 0,6 portion adulte pour les quantités d'ingrédients (soit environ "
            f"{equivalent_adultes} portions adultes au total), sans pour autant réduire son repas "
            f"à une portion symbolique"
        )

    section_garde_manger = (
        f"\nDÉJÀ À LA MAISON (ne JAMAIS les remettre dans la liste de courses, tu peux les utiliser librement dans les recettes) :\n"
        + "\n".join(f"- {a}" for a in garde_manger)
        if garde_manger else ""
    )
    section_achats_recurrents = (
        f"\nACHATS FIXES DE LA SEMAINE (achetés chaque semaine peu importe les promos — utilise-les comme base de plusieurs recettes pour varier les féculents ; ils sont ajoutés à la liste de courses automatiquement, ne les y ajoute pas toi-même) :\n"
        + "\n".join(f"- {a}" for a in achats_recurrents)
        if achats_recurrents else ""
    )

    incontournables = user.get("incontournables") or []
    section_incontournables = (
        f"\nINCONTOURNABLES DE LA SEMAINE (le foyer les veut au menu, promo ou non — intègre-les dans au moins une recette chacun) :\n"
        + "\n".join(f"- {a}" for a in incontournables)
        if incontournables else ""
    )

    budget_max_prompt = user.get('budget_max')
    repere_budget_jour = (
        f"\n- Repère de dépense quotidienne pour couvrir 7 jours : environ {budget_max_prompt / 7:.2f} $/jour "
        "(indicatif — vise ce niveau dès la première recette pour éviter d'avoir à corriger le coût par jour "
        "après coup)."
        if budget_max_prompt else ""
    )

    return f"""Tu es un planificateur de menus économiques pour EcoMenu.

PROFIL DU FOYER :
- Budget maximum pour la semaine : {budget_max_prompt} ${repere_budget_jour}
- Foyer : {composition_foyer}
- Boîtes à lunch / restes : {boite_lunch}
{section_garde_manger}
{section_achats_recurrents}
{section_incontournables}

PROMOTIONS DISPONIBLES CETTE SEMAINE :
{liste_promos}

RÈGLES STRICTES :
1. Génère un menu pour 7 jours (Lundi à Dimanche) si le budget le permet. Si le budget est clairement insuffisant pour 7 jours, réduis le nombre de jours couverts, mets budget_respecte à false et explique pourquoi dans message_avertissement.
2. PRIORITÉ À L'ÉQUILIBRE ET LA VARIÉTÉ, PAS AUX PROMOS À TOUT PRIX : construis d'abord un menu varié et nutritionnellement équilibré sur la semaine. Utilise un ingrédient en promotion comme ingredient_phare chaque fois que c'est cohérent avec cet équilibre (indique alors enseigne_ingredient_phare) — mais si aucune promotion ne convient à une recette donnée sans sacrifier la diversité, choisis un ingrédient hors promotion pour ingredient_phare et laisse enseigne_ingredient_phare vide (null). Ne force jamais un ingrédient en promotion dans une recette juste pour respecter cette règle si cela nuit à l'équilibre de la semaine.
3. eco_score est une lettre de A (meilleur) à E (moins bon) selon la fraîcheur/impact environnemental estimé.
4. La liste de courses doit être divisée en deux sections : "section_circulaire" (articles en promotion utilisés, groupés par enseigne, au prix promo) et "section_fond_de_placard" (TOUT le reste des ingrédients nécessaires aux recettes qui ne sont pas en promotion cette semaine — condiments de base ET ingrédients principaux hors promo type viande, légumes, etc. : achète-les quand même, au prix courant estimé). Si des boite_lunch_midi sont des recettes distinctes du souper (type "repas froids spécifiques"), leurs ingrédients propres (ex. pain, trempette, contenants de collation) doivent AUSSI apparaître dans la liste de courses — pas seulement les ingrédients des repas_soir. Quand boite_lunch_midi est une recette distincte, remplis aussi ingredient_phare_lunch avec SON ingrédient principal (ex. "pain tranché" pour un sandwich, "fromage" pour un lunch de cubes de fromage) — laisse-le vide (null) si le lunch réutilise simplement les restes du souper.
5. cout_estime_total doit être un total réaliste et ne doit jamais dépasser le budget maximum de plus de 5%. À l'inverse, vise à utiliser au moins 90% du budget disponible une fois les 7 jours couverts — n'économise pas inutilement : privilégie des coupes de viande ou poissons un peu meilleurs, des portions plus généreuses ou plus de variété plutôt que de laisser une grande partie du budget inutilisée. IMPORTANT : la liste de promotions fournie n'est PAS une limite au nombre de repas ou de jours que tu peux proposer — si tu as épuisé les promotions pertinentes mais qu'il reste du budget, continue avec des ingrédients hors promotion (ils iront dans section_fond_de_placard) plutôt que de réduire le nombre de jours ou de sous-utiliser le budget. Ne réduis le nombre de jours QUE si le budget total est réellement insuffisant, jamais parce que la liste de promotions te semble courte.
6. economies_estimees = somme des écarts entre prix courant estimé et prix promo pour les articles de section_circulaire uniquement.
7. Ne jamais inventer un article de section_circulaire qui n'apparaît pas dans la liste de promotions fournie — tout ingrédient non trouvé dans cette liste va dans section_fond_de_placard, jamais section_circulaire.
8. DIVERSITÉ DES PROTÉINES (inspirée du Guide alimentaire canadien) : pour chaque jour, choisis une categorie_proteine parmi {CATEGORIES_PROTEINE}. Varie ces catégories sur la semaine — ne répète pas la même catégorie plus de 2 jours d'affilée ni plus de la moitié des jours couverts. Si des promotions de poisson_fruits_mer sont disponibles dans la liste, inclus-en au moins un repas sur un menu de 4 jours ou plus. Ne concentre pas le menu sur une seule catégorie même si elle domine les promotions.
9. Privilégie une assiette équilibrée : légumes/fruits en bonne place, protéines variées, grains entiers pour les féculents.
9ter. DISCIPLINE DE LISTE DE COURSES : réutilise les mêmes ingrédients de base sur plusieurs recettes plutôt que d'introduire un nouvel article pour chaque plat — chaque nouvel ingrédient distinct ajoute son propre coût, même petit, et une liste trop longue fait exploser le total. N'achète PAS plusieurs variétés du même type de produit dans la même semaine sans raison (ex. un seul fromage sur 2-3 recettes plutôt que feta + cheddar + fromage à la crème + crème sure) ; vise un féculent principal et une base de légumes récurrente plutôt qu'un légume différent à chaque jour.
9bis. CUISINE MAISON, PAS DE PLATS PRÉPARÉS : ne base jamais une recette sur un aliment transformé/prêt-à-manger (soupe en conserve, plat surgelé tout-prêt, macaroni en boîte, nouilles instantanées, pâté chinois surgelé...). Chaque repas doit être composé d'ingrédients bruts (viande, poisson, légumes, féculents secs, œufs...) assemblés par la recette elle-même, même si un produit transformé apparaît dans les promotions fournies.
10. Ne jamais lister un article "déjà à la maison" dans la liste de courses. Les "achats fixes de la semaine" ne doivent JAMAIS être ajoutés toi-même à section_circulaire ni section_fond_de_placard (ils sont gérés automatiquement en dehors de ta réponse) — utilise-les seulement comme ingrédients de base dans tes recettes pour varier les féculents.
11. Les quantités de la liste de courses (champ quantite) doivent être réalistes {consigne_portions} sur les repas prévus — indique toujours un nombre (ex. "3 unités", "2 lb"), jamais un mot seul comme "chacun".
12. Intègre chaque incontournable listé ci-dessus dans au moins une recette de la semaine, qu'il soit en promotion ou non — une recette de repas_soir (souper) suffit à remplir cette règle. EXCEPTION ABSOLUE : si la boîte à lunch est en mode "repas froids spécifiques" pour un profil enfant (cf. section boîte à lunch), un incontournable contenant arachides ou noix ne doit JAMAIS être placé dans un boite_lunch_midi même s'il apparaît dans la liste des incontournables — intègre-le uniquement dans une recette de souper à la place. La restriction allergènes de la boîte à lunch enfant prime toujours sur cette règle.
13. RECETTES TENDANCE : évite les repas génériques du type "protéine + légume + féculent" servis à l'identique chaque soir. Pour chaque jour, choisis un style_tendance parmi {STYLES_TENDANCE} (ou un format actuel équivalent que tu connais) et varie-les sur la semaine — ne répète pas le même style plus de 2 fois. Donne à repas_soir un nom appétissant et concret (ex. "Bowl teriyaki au poulet et riz" plutôt que "Poulet avec riz et légumes"), tout en respectant le budget et les ingrédients disponibles.
{f"14. ATTENTION : une proposition précédente manquait de diversité ou d'équilibre nutritionnel ({note_diversite}). Corrige-le impérativement cette fois-ci — si le problème concerne les fruits/légumes ou les produits laitiers, ajoute-en davantage dans la liste de courses (en promotion si possible, sinon dans section_fond_de_placard)." if note_diversite else ""}
{f"15. ATTENTION : une proposition précédente sous-utilisait le budget ({note_sous_budget}). Corrige-le impérativement cette fois-ci en visant au moins 90% du budget disponible (meilleures coupes, portions plus généreuses, plus de variété)." if note_sous_budget else ""}
{f"16. ATTENTION CRITIQUE : une proposition précédente dépassait le budget ({note_depassement}). EXIGENCE STRUCTURELLE, pas une simple suggestion : le tableau menu_semaine de ta réponse doit contenir EXACTEMENT le nombre de jours suggéré ci-dessus, ni plus ni moins — si le nombre suggéré est 2, menu_semaine doit avoir 2 entrées, pas 7. Si un incontournable ne peut pas tenir dans ce nombre réduit de jours sans faire exploser le budget, inclus-le dans UN SEUL jour (une seule recette suffit pour respecter la règle 12) plutôt que de garder 7 jours pour lui faire de la place. Ne te contente PAS non plus de réduire les jours en gardant des portions/ingrédients tout aussi coûteux (une proposition précédente a déjà fait cette erreur : moins de jours, mais un coût par jour encore plus élevé qu'avant) — réduis EN MÊME TEMPS le coût par jour (coupes plus économiques, portions mesurées, moins d'ingrédients premium simultanés)." if note_depassement else ""}
"""


ESTIMATION_PRIX_FOND_PLACARD = 3.5  # $ par condiment de base non-promo (sel, huile, épices...)

# Mots-clés identifiant un condiment/assaisonnement bon marché plutôt qu'un ingrédient
# principal de recette (viande, légumes...) — désormais que section_fond_de_placard peut
# contenir de vrais ingrédients nécessaires hors promo, l'estimation à prix fixe de 3,5$
# ne convient plus qu'à ces petits articles.
MOTS_CONDIMENTS = {
    "sel", "poivre", "huile", "vinaigre", "sauce", "moutarde", "ketchup",
    "épices", "epices", "farine", "sucre", "mayonnaise", "assaisonnement", "condiment",
    # Aromates/fines herbes/épices individuelles — absents jusqu'ici, ce qui les faisait
    # retomber sur le prix moyen toutes catégories confondues (~9-10$, tiré vers le haut
    # par la viande/poisson) au lieu d'un prix de condiment (3,5$) : bug constaté avec un
    # menu Claude utilisant ail/citron/persil/paprika comme base aromatique (2026-09-10).
    "ail", "citron", "lime", "persil", "coriandre", "basilic", "paprika", "cumin",
    "curry", "thym", "origan", "cannelle", "gingembre", "échalote", "echalote",
    "câpres", "capres", "zeste", "herbes", "bouillon", "levure", "bicarbonate",
}

# Devine la catégorie d'un article hors promo à partir de mots-clés dans son nom, pour
# l'estimer au prix moyen (prix d'origine, pas prix promo) de sa propre catégorie plutôt
# qu'une moyenne toutes catégories confondues — un poulet entier ne coûte pas le prix
# moyen d'une carotte.
MOTS_PAR_CATEGORIE = {
    "Boucherie": ["poulet", "boeuf", "bœuf", "porc", "viande", "agneau", "veau", "dinde", "steak", "haché"],
    "Poissonnerie": ["saumon", "poisson", "crevette", "thon", "tilapia", "morue", "fruits de mer", "moule", "pétoncle", "truite", "crabe"],
    "Produits Laitiers": ["lait", "fromage", "yogourt", "yaourt", "crème", "beurre"],
    "Boulangerie": ["pain", "baguette", "bagel"],
    "Surgelés": ["surgelé", "surgelée", "congelé"],
    "Fruits & Légumes": ["légume", "légumes", "fruit", "fruits", "tomate", "carotte", "laitue", "pomme", "banane", "oignon", "poivron", "brocoli", "épinard", "concombre", "courgette"],
}


def deviner_categorie(nom_produit: str) -> Optional[str]:
    nom_lower = (nom_produit or "").lower()
    for categorie, mots in MOTS_PAR_CATEGORIE.items():
        if contient_mot_entier(nom_lower, mots):
            return categorie
    return None


def calculer_prix_origine_par_categorie(promos: List[dict]) -> dict:
    """Prix d'origine typique (avant rabais) par catégorie alimentaire, calculé à partir
    des vraies circulaires de la semaine — sert de référence pour estimer le prix courant
    d'un article qui n'est PAS en promo cette semaine (le prix promo moyen sous-estimerait
    systématiquement, puisqu'il est par définition réduit).
    Utilise la MÉDIANE, pas la moyenne : les circulaires mélangent des formats standards
    et des formats "entrepôt/gros volume" (ex. une caisse d'ailes de poulet à 188$ à côté
    d'un paquet à 13$) — quelques valeurs extrêmes suffisent à gonfler une moyenne de 20 à
    30%, alors que la médiane reste représentative de l'achat typique d'un foyer."""
    par_categorie: dict = {}
    for p in promos:
        cat = p.get("categorie_alimentaire") or "Épicerie"
        prix_origine = p.get("prix_origine") or p.get("prix_promo")
        if prix_origine:
            par_categorie.setdefault(cat, []).append(prix_origine)
    return {cat: statistics.median(prix) for cat, prix in par_categorie.items()}


POIDS_MAX_HISTORIQUE = 200  # plafond du poids de l'historique cumulé face à la semaine en cours
POIDS_SEMAINE_COURANTE = 10


def fusionner_avec_historique(prix_semaine: dict, historique: dict) -> dict:
    """Combine le prix moyen d'origine de la semaine en cours avec l'historique cumulé
    (persisté sur plusieurs semaines par pousser_supabase.py), en donnant de plus en plus
    de poids à l'historique à mesure qu'il s'enrichit — plus fiable qu'une seule semaine de
    promotions pour les enseignes choisies par un utilisateur donné, sans pour autant
    ignorer totalement l'évolution récente des prix."""
    fusion: dict = {}
    for categorie in set(prix_semaine) | set(historique):
        prix_s = prix_semaine.get(categorie)
        hist = historique.get(categorie)
        if hist and prix_s is not None:
            poids_hist = min(hist["nb_observations"], POIDS_MAX_HISTORIQUE)
            fusion[categorie] = (
                hist["prix_origine_moyen"] * poids_hist + prix_s * POIDS_SEMAINE_COURANTE
            ) / (poids_hist + POIDS_SEMAINE_COURANTE)
        elif hist:
            fusion[categorie] = hist["prix_origine_moyen"]
        elif prix_s is not None:
            fusion[categorie] = prix_s
    return fusion


# Prix approximatifs pour des articles dont la quantité de recette est un VRAI compteur
# d'unités individuelles (ex. "10 unités" d'œufs = 10 œufs) plutôt qu'un nombre de paquets —
# nos prix par catégorie sont calibrés au niveau du paquet/promo typique, donc les multiplier
# par un tel compteur surestime radicalement (10 œufs à ~6,50$/paquet-moyen = 65$ au lieu de
# ~4$ ; 12 tortillas au même prix paquet = 78$ au lieu de ~6$ ; constatés sur des menus Claude
# le 2026-09-10). Cas trop spécifiques et peu nombreux pour justifier une refonte du modèle de
# prix par quantité — cf. le chantier "poids/volume fiable des promos" déjà identifié comme
# prérequis à une solution générale. PLAFOND_PRIX_LIGNE_NON_PROMO ci-dessous complète cette
# liste en filet de sécurité pour le prochain ingrédient du même genre qu'on n'aura pas prévu.
PRIX_UNITAIRE_CONNU = {
    "oeuf": 0.4,
    "œuf": 0.4,
    "tortilla": 0.5,
}

# Filet de sécurité : au-delà de ce montant, une seule ligne d'article non trouvé tel quel
# dans les promos (fond de placard ou nom introuvable en circulaire) est plus probablement
# une erreur d'unité (ex. "12 unités" d'un article compté par paquet, cf.
# PRIX_UNITAIRE_CONNU ci-dessus) qu'un article réellement coûteux à ce point — aucun
# ingrédient de recette hebdomadaire courant ne justifie 20$+ sur une seule ligne hors
# grosse pièce de viande/poisson (déjà bien couverte par sa vraie catégorie).
PLAFOND_PRIX_LIGNE_NON_PROMO = 20.0


def estimer_prix_fond_de_placard(
    nom_produit: str, prix_origine_par_categorie: dict, prix_origine_global: float
) -> tuple:
    """Retourne (prix_unitaire, categorie_incertaine). categorie_incertaine=True signifie
    qu'aucun mot-clé de condiment ni de catégorie n'a reconnu l'article — le prix retourné
    est alors le prix de repli Épicerie, une estimation de dernier recours moins fiable
    que les autres cas, notamment si la quantité de recette est un compteur d'unités
    individuelles élevé (cf. PLAFOND_PRIX_LIGNE_NON_PROMO)."""
    nom_lower = (nom_produit or "").lower()
    for mot, prix in PRIX_UNITAIRE_CONNU.items():
        if contient_mot_entier(nom_lower, [mot]):
            return prix, False
    if contient_mot_entier(nom_lower, MOTS_CONDIMENTS):
        return ESTIMATION_PRIX_FOND_PLACARD, False
    categorie = deviner_categorie(nom_produit)
    if categorie and categorie in prix_origine_par_categorie:
        return prix_origine_par_categorie[categorie], False
    return prix_origine_global, True


def extraire_quantite_numerique(texte: str) -> float:
    """Extrait le nombre d'unités à acheter d'une quantité en texte libre ('4 unités' ->
    4.0, '2 lb' -> 2.0, 'chacun' -> 1.0). Un nombre suivi de g/ml décrit la taille d'UN
    contenant ('250 ml', '500 g') et non un nombre d'unités à acheter — sinon on
    multiplierait le prix par 250 pour une seule bouteille d'huile. Le LLM écrit ce champ
    en langage naturel, donc l'analyse reste best-effort.
    "douzaine(s)" est un multiplicateur (×12), pas un simple compteur : sans ce cas
    particulier, "3 douzaines" d'œufs pour une grande famille était lu comme 3 œufs au
    lieu de 36, à 0,40$/œuf — un total de 1,20$ au lieu de 14,40$ (constaté le
    2026-09-22, foyer de 8 personnes)."""
    texte = texte or ""
    if re.search(r"\d+(?:[.,]\d+)?\s*(g|gramme|grammes|ml|millilitre|millilitres|mg)\b", texte, re.IGNORECASE):
        return 1.0
    m_douzaine = re.search(r"\d+(?:[.,]\d+)?(?=\s*douzaines?\b)", texte, re.IGNORECASE)
    if m_douzaine:
        return float(m_douzaine.group().replace(",", ".")) * 12
    m = re.search(r"\d+(?:[.,]\d+)?", texte)
    return float(m.group().replace(",", ".")) if m else 1.0


def indexer_promos_par_nom(promos: List[dict]) -> dict:
    index = {}
    for p in promos:
        cle = (p.get("nom_produit") or "").strip().lower()
        if cle and cle not in index:
            index[cle] = p  # promos triées par prix croissant : garde la moins chère
    return index


# Garde-fou "panier de base" (chantier du 2026-09-09) : le menu généré par le LLM à partir
# des promos peut respecter le budget et varier ses protéines tout en étant pauvre en
# fruits/légumes ou en produits laitiers. On compare la liste de courses au panier de
# référence nutritif (Guide alimentaire canadien 2007, converti en kg/semaine par personne
# lors de la discussion avec l'utilisateur), mais SANS viser les kg précis : les promos
# scrapées n'ont pas de poids/volume fiable (poids_volume n'est jamais rempli côté
# scraper), donc un seuil sur le NOMBRE D'ARTICLES DISTINCTS est le proxy le plus robuste
# disponible aujourd'hui. Un vrai contrôle par quantité demanderait d'abord de fiabiliser
# le scraper (chantier séparé, mis de côté au profit de cette version plus simple).
# La diversité des protéines est déjà couverte par verifier_diversite_menu au niveau des
# recettes (categorie_proteine par jour), donc on ne la revérifie pas ici.
def verifier_couverture_panier(liste_courses: dict, tous_promos: List[dict], jours_couverts: int) -> Optional[str]:
    """Retourne une explication si la liste de courses manque de fruits/légumes ou de
    produits laitiers par rapport au panier de référence, sinon None."""
    index_promos = indexer_promos_par_nom(tous_promos)
    articles = (
        liste_courses.get("section_circulaire", [])
        + liste_courses.get("section_fond_de_placard", [])
        + liste_courses.get("section_achats_fixes", [])
    )

    noms_vus = set()
    compte_categories: dict = {}
    for a in articles:
        nom = (a.get("nom_produit") or "").strip().lower()
        if not nom or nom in noms_vus:
            continue
        noms_vus.add(nom)
        categorie = (index_promos.get(nom) or {}).get("categorie_alimentaire") or deviner_categorie(nom)
        if categorie:
            compte_categories[categorie] = compte_categories.get(categorie, 0) + 1

    seuil_fruits_legumes = max(2, round(jours_couverts * 3 / 7))
    seuil_produits_laitiers = 1 if jours_couverts >= 3 else 0

    manques = []
    nb_fl = compte_categories.get("Fruits & Légumes", 0)
    if nb_fl < seuil_fruits_legumes:
        manques.append(
            f"seulement {nb_fl} article(s) de Fruits & Légumes pour {jours_couverts} jours "
            f"(minimum visé : {seuil_fruits_legumes})"
        )
    if compte_categories.get("Produits Laitiers", 0) < seuil_produits_laitiers:
        manques.append("aucun produit laitier dans la liste de courses cette semaine")

    return " ; ".join(manques) if manques else None


def recalculer_couts_reels(menu: MenuGenere, promos: List[dict], historique_categorie: Optional[dict] = None) -> None:
    """Ne fait jamais confiance aux totaux estimés par le LLM : recalcule cout_estime_total
    et economies_estimees des sections section_circulaire/section_fond_de_placard à partir
    des vrais prix. Le LLM peut halluciner un total plausible sans rapport avec les prix
    réels. budget_respecte est laissé à la charge de l'appelant, une fois les achats fixes
    (gérés hors de ce schéma) ajoutés au total."""
    index_promos = indexer_promos_par_nom(promos)
    prix_origine_par_categorie = calculer_prix_origine_par_categorie(promos)
    if historique_categorie:
        prix_origine_par_categorie = fusionner_avec_historique(prix_origine_par_categorie, historique_categorie)
    # Prix de repli pour un article dont on ne devine pas la catégorie (deviner_categorie
    # renvoie None) : la moyenne DE TOUTES les catégories confondues (Boucherie/Poissonnerie
    # incluses) surestimait fortement ce genre d'article, souvent un petit ingrédient
    # (aromate, condiment) plutôt qu'une pièce de viande — constaté avec ail/citron/persil
    # estimés à ~9,50$ chacun (2026-09-10). Épicerie est le rayon "fourre-tout" le plus
    # représentatif d'un article non identifié ; à défaut, le prix de condiment (3,5$) est
    # une estimation plus sûre qu'une moyenne tirée vers le haut par la viande/poisson.
    prix_origine_global = prix_origine_par_categorie.get("Épicerie", ESTIMATION_PRIX_FOND_PLACARD)

    cout_reel = 0.0
    economies_reelles = 0.0

    for article in menu.liste_courses.section_circulaire:
        qte = extraire_quantite_numerique(article.quantite)
        promo = index_promos.get(article.nom_produit.strip().lower())
        if promo:
            prix_ligne = promo["prix_promo"] * qte
            prix_origine = promo.get("prix_origine") or promo["prix_promo"]
            economies_reelles += max(0.0, prix_origine - promo["prix_promo"]) * qte
        else:
            # Le LLM a mentionné un article introuvable tel quel dans les promos fournies
            # (paraphrase, nom combiné/tronqué...) : on l'estime par sa catégorie plutôt que
            # par le prix moyen de TOUT le pool de promos, qui incluait viande/poisson et
            # surestimait fortement un simple légume ou condiment mal apparié (même bug que
            # celui corrigé sur section_fond_de_placard, cf. estimer_prix_fond_de_placard).
            # Hypothèse conservatrice : on ne sait pas si l'article est vraiment en promo,
            # donc on utilise son prix hors-promo plutôt que de lui inventer un rabais.
            prix_unitaire, categorie_incertaine = estimer_prix_fond_de_placard(
                article.nom_produit, prix_origine_par_categorie, prix_origine_global
            )
            prix_ligne = prix_unitaire * qte
            if categorie_incertaine:
                prix_ligne = min(prix_ligne, PLAFOND_PRIX_LIGNE_NON_PROMO)
        article.prix = round(prix_ligne, 2)
        cout_reel += prix_ligne

    for article in menu.liste_courses.section_fond_de_placard:
        prix_unitaire, categorie_incertaine = estimer_prix_fond_de_placard(
            article.nom_produit, prix_origine_par_categorie, prix_origine_global
        )
        prix_ligne = prix_unitaire * extraire_quantite_numerique(article.quantite)
        if categorie_incertaine:
            prix_ligne = min(prix_ligne, PLAFOND_PRIX_LIGNE_NON_PROMO)
        article.prix = round(prix_ligne, 2)
        cout_reel += prix_ligne

    menu.cout_estime_total = round(cout_reel, 2)
    menu.economies_estimees = round(economies_reelles, 2)


def trouver_promo_pour_terme(terme_lower: str, tous_promos: List[dict]) -> Optional[dict]:
    """Cherche la meilleure promo correspondant à un terme générique ('riz', 'saumon'...).
    Le terme comme premier mot du produit ("Riz bistro express") est un bien meilleur
    indice que c'est vraiment l'article recherché qu'une simple sous-chaîne n'importe où
    ("Croustilles ... de riz" contiendrait "riz" sans être du riz). On ne retombe sur la
    correspondance large que si aucun match "premier mot" n'existe.
    Les deux comparaisons utilisent des limites de mot (\\b) plutôt qu'une sous-chaîne
    brute : sans ça, chercher "lait" appariait "laitue" (Carottes... ou laitue duo...) au
    lieu d'un vrai produit laitier, "lait" étant littéralement les 4 premières lettres de
    "laitue" — constaté sur un profil de test le 2026-09-15.
    Le repli "n'importe où dans le nom" reste risqué même en mot entier : "lait" apparaît
    aussi, en toute légitimité linguistique, dans "Escalope de cuisseau de veau de LAIT"
    (Boucherie) — même semaine de test. Quand on peut deviner la catégorie attendue du
    terme cherché lui-même (via deviner_categorie), on exige que la promo trouvée par ce
    repli partage cette catégorie, sinon on préfère ne rien trouver (l'appelant utilisera
    alors une estimation générique) plutôt qu'un article hors-sujet mais textuellement
    correspondant."""
    motif_debut = motif_terme_recherche(terme_lower, ancre_debut=True)
    motif_partout = motif_terme_recherche(terme_lower)
    match_debut = next(
        (p for p in tous_promos if motif_debut.match((p.get("nom_produit") or "").strip().lower())),
        None,
    )
    if match_debut:
        return match_debut

    categorie_attendue = deviner_categorie(terme_lower)
    for p in tous_promos:
        if not motif_partout.search((p.get("nom_produit") or "").lower()):
            continue
        if categorie_attendue and p.get("categorie_alimentaire") != categorie_attendue:
            continue
        return p
    return None


def garantir_incontournables(menu: MenuGenere, incontournables: List[str], tous_promos: List[dict]) -> None:
    """Filet de sécurité : en pratique, le LLM utilise parfois un incontournable comme
    ingredient_phare d'une recette sans l'ajouter à la liste de courses. On vérifie et on
    corrige, pour ne jamais laisser l'utilisateur devant une recette dont il manque
    l'ingrédient sur sa liste."""
    deja_presents = {
        a.nom_produit.strip().lower()
        for a in menu.liste_courses.section_circulaire + menu.liste_courses.section_fond_de_placard
    }
    for terme in incontournables:
        terme_lower = terme.strip().lower()
        if not terme_lower:
            continue
        # motif_terme_recherche : limite de mot + exclusion des faux-amis connus (ex.
        # "pommes" ne doit pas être considéré satisfait par "pommes de terre" déjà
        # présent pour une autre recette — cf. EXCLUSIONS_FAUX_AMIS, 2026-09-15).
        motif_deja_present = motif_terme_recherche(terme_lower)
        if any(motif_deja_present.search(nom) for nom in deja_presents):
            continue
        promo = trouver_promo_pour_terme(terme_lower, tous_promos)
        if promo:
            menu.liste_courses.section_circulaire.append(
                ArticleCourse(nom_produit=promo["nom_produit"], quantite="1", enseigne=promo.get("enseigne"))
            )
        else:
            menu.liste_courses.section_fond_de_placard.append(
                ArticleCourse(nom_produit=terme.capitalize(), quantite="1", enseigne=None)
            )


def garantir_ingredients_phares(menu: MenuGenere, tous_promos: List[dict], motifs_exclure: Optional[list] = None) -> None:
    """Filet de sécurité (chantier "complétude de la liste de courses", 2026-09-22) :
    l'ingrédient-phare d'un souper (ingredient_phare) ou d'un lunch distinct
    (ingredient_phare_lunch) n'est pas toujours repris par le LLM dans la liste de
    courses, ce qui laisse l'utilisateur devant une recette dont il manque l'ingrédient
    central — constaté sur un test de boîte à lunch enfant où fromage/pain/farine
    manquaient malgré des lunchs qui en dépendaient. Même logique que
    garantir_incontournables, sauf pour un terme qui correspond à un motif explicitement
    exclu (garde-manger/achats fixes) : son absence de la liste est alors volontaire, pas
    un oubli."""
    motifs_exclure = motifs_exclure or []
    deja_presents = {
        a.nom_produit.strip().lower()
        for a in menu.liste_courses.section_circulaire + menu.liste_courses.section_fond_de_placard
    }
    termes = []
    for jour in menu.menu_semaine:
        if jour.ingredient_phare:
            termes.append(jour.ingredient_phare)
        if jour.ingredient_phare_lunch:
            termes.append(jour.ingredient_phare_lunch)

    for terme in termes:
        terme_lower = terme.strip().lower()
        if not terme_lower:
            continue
        motif = motif_terme_recherche(terme_lower)
        if any(motif.search(nom) for nom in deja_presents):
            continue
        if any(m.search(terme_lower) for m in motifs_exclure):
            continue
        promo = trouver_promo_pour_terme(terme_lower, tous_promos)
        if promo:
            menu.liste_courses.section_circulaire.append(
                ArticleCourse(nom_produit=promo["nom_produit"], quantite="1", enseigne=promo.get("enseigne"))
            )
            deja_presents.add(promo["nom_produit"].strip().lower())
        else:
            menu.liste_courses.section_fond_de_placard.append(
                ArticleCourse(nom_produit=terme.strip().capitalize(), quantite="1", enseigne=None)
            )
            deja_presents.add(terme_lower)


def construire_achats_fixes(termes: List[str], tous_promos: List[dict]) -> tuple:
    """Construit la section "Basiques de la semaine" : chaque achat fixe est acheté peu
    importe les promos — s'il est en promo cette semaine on en profite (vrai prix, vraie
    enseigne), sinon on l'achète quand même au prix courant estimé. Contrairement au
    fond de placard générique (que le LLM invente librement), cette liste est entièrement
    déterministe pour ne jamais dépendre de ce que le LLM a choisi d'écrire ou non."""
    articles = []
    cout_supplementaire = 0.0
    economies_supplementaires = 0.0

    for terme in termes:
        terme_lower = terme.lower()
        promo = trouver_promo_pour_terme(terme_lower, tous_promos)
        if promo:
            prix_origine = promo.get("prix_origine") or promo["prix_promo"]
            articles.append({
                "nom_produit": promo["nom_produit"],
                "quantite": "1",
                "enseigne": promo.get("enseigne"),
                "en_promo": True,
                "prix": round(promo["prix_promo"], 2),
            })
            cout_supplementaire += promo["prix_promo"]
            economies_supplementaires += max(0.0, prix_origine - promo["prix_promo"])
        else:
            articles.append({
                "nom_produit": terme.capitalize(),
                "quantite": "1",
                "enseigne": None,
                "en_promo": False,
                "prix": ESTIMATION_PRIX_FOND_PLACARD,
            })
            cout_supplementaire += ESTIMATION_PRIX_FOND_PLACARD

    return articles, round(cout_supplementaire, 2), round(economies_supplementaires, 2)


@app.post("/api/v1/menus/generate", tags=["menus"])
@limiter.limit("5/minute")
def generate_menu(request: Request, payload: GenerateMenuRequest):
    if not claude_client:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY manquante : génération de menu indisponible.")

    # 1. Profil utilisateur
    try:
        user_resp = supabase.table("users").select("*").eq("id", payload.user_id).single().execute()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Utilisateur introuvable : {str(e)}")
    user = user_resp.data
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    # 2. Enseignes sélectionnées (jointure vers le catalogue enseignes pour récupérer le nom)
    enseignes_resp = (
        supabase.table("enseigne_selection")
        .select("enseigne_id, enseignes(nom)")
        .eq("user_id", payload.user_id)
        .execute()
    )
    enseignes = sorted({
        r["enseignes"]["nom"] for r in enseignes_resp.data
        if r.get("enseignes") and r["enseignes"].get("nom")
    })
    if not enseignes:
        raise HTTPException(status_code=400, detail="Aucune enseigne sélectionnée pour ce foyer.")

    # 3. Clé de cache basée sur [Enseignes + Budget + Taille Foyer + Boîtes à lunch + Garde-manger]
    cache_key = "|".join([
        ",".join(enseignes),
        str(user.get("budget_max")),
        str(user.get("taille_foyer")),
        str(user.get("nb_adultes")),
        str(user.get("nb_enfants")),
        str(user.get("gestion_restes")),
        str(user.get("type_boite_lunch")),
        str(user.get("profil_boite_lunch")),
        ",".join(sorted(user.get("garde_manger") or [])),
        ",".join(sorted(user.get("achats_recurrents") or [])),
    ])

    cached_resp = (
        supabase.table("menus")
        .select("*")
        .filter("menu_data->>cache_key", "eq", cache_key)
        .order("date_generated", desc=True)
        .limit(1)
        .execute()
    )
    if cached_resp.data:
        return cached_resp.data[0]

    # 4. Promotions disponibles pour les enseignes choisies, puis sélection équilibrée par
    # catégorie (cf. selectionner_promos_diversifiees) plutôt que les simples moins chères
    promos_resp = (
        supabase.table("promotions")
        .select("*")
        .in_("enseigne", enseignes)
        .order("prix_promo")
        .limit(300)
        .execute()
    )
    tous_promos = promos_resp.data
    if not tous_promos:
        raise HTTPException(
            status_code=422,
            detail="Aucune promotion alimentaire trouvée pour ces enseignes. Élargissez votre sélection.",
        )
    promos = selectionner_promos_diversifiees(tous_promos)

    # Préparation des étapes déterministes qui ne dépendent pas du menu généré par le LLM,
    # donc pas besoin de les refaire à chaque tentative.
    garde_manger_norm = {a.strip().lower() for a in (user.get("garde_manger") or []) if a.strip()}
    achats_recurrents_termes = [a.strip() for a in (user.get("achats_recurrents") or []) if a.strip()]
    achats_recurrents_norm = {a.lower() for a in achats_recurrents_termes}
    a_exclure = garde_manger_norm | achats_recurrents_norm
    # Motifs \b (pas une égalité stricte) : si le LLM viole la règle 10 du prompt en
    # écrivant un nom plus précis que le terme saisi par l'utilisateur (ex. "Riz basmati
    # 900g" au lieu de "riz"), une comparaison exacte laisserait passer l'article alors
    # que l'utilisateur a dit l'avoir déjà. motif_terme_recherche gère aussi les
    # faux-amis (ex. exclure "pomme" n'exclut pas "pomme de terre").
    motifs_exclure = [motif_terme_recherche(t) for t in a_exclure]
    incontournables_termes = [a.strip() for a in (user.get("incontournables") or []) if a.strip()]
    achats_fixes, cout_achats_fixes, economies_achats_fixes = construire_achats_fixes(
        achats_recurrents_termes, tous_promos
    )
    try:
        historique_resp = supabase.table("historique_prix_categorie").select("*").execute()
        historique_categorie = {r["categorie_alimentaire"]: r for r in historique_resp.data}
    except Exception:
        historique_categorie = {}
    budget_max = user.get("budget_max")

    # 5. Génération par IA (sortie structurée validée par schéma Pydantic), avec une
    # seconde tentative si la première manque de diversité protéique OU sous-utilise
    # nettement le budget disponible (moins de 90%).
    menu_genere = None
    menu_data = None
    raison_manque_diversite = None
    raison_manque_panier = None
    raison_sous_budget = None
    raison_depassement = None
    meilleur_menu_data = None
    meilleur_respecte = False
    meilleure_diversite_ok = False
    meilleurs_jours_couverts = -1
    meilleur_ecart_budget = float("inf")
    meilleure_raison_diversite = None
    meilleure_raison_panier = None
    # 3 tentatives (au lieu de 2) : réduit la variance du % de budget utilisé en donnant
    # une chance de plus à la boucle de corriger un menu sous-utilisé/en manque de
    # diversité, au prix d'environ 50% d'appels Claude en plus dans le pire cas (les
    # tentatives s'arrêtent dès qu'un menu satisfait tous les critères, cf. le break plus bas).
    for tentative in range(3):
        note_diversite_combinee = " ; ".join(
            r for r in (raison_manque_diversite, raison_manque_panier) if r
        ) or None
        prompt = construire_prompt(
            user, promos,
            note_diversite=note_diversite_combinee,
            note_sous_budget=raison_sous_budget,
            note_depassement=raison_depassement,
        )
        try:
            # En streaming plutôt qu'en appel bloquant unique : avec un max_tokens élevé
            # (menu de 7 jours + liste de courses structurée), Anthropic recommande le
            # streaming pour éviter qu'une connexion inactive trop longtemps ne soit
            # coupée (cf. https://platform.claude.com/docs/en/api/errors#long-requests) —
            # observé en pratique via une erreur "Request timed out or interrupted" après
            # ~3 tentatives internes du SDK sur l'appel bloquant.
            # thinking désactivé : Claude Sonnet 5 l'active par défaut, mais un pur exercice
            # de mise en forme structurée (Pydantic) n'en a pas besoin — activé, le modèle a
            # épuisé tout le budget max_tokens en réflexion interne sans jamais produire le
            # JSON (stop_reason="max_tokens", content=[thinking] uniquement, constaté en test).
            with claude_client.with_options(timeout=CLAUDE_TIMEOUT_MENU).messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=8192,
                system="Tu réponds uniquement avec des données structurées valides, sans texte hors-schéma.",
                messages=[{"role": "user", "content": prompt}],
                output_format=MenuGenere,
                thinking={"type": "disabled"},
            ) as stream:
                completion = stream.get_final_message()
            menu_genere = completion.parsed_output
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Échec de la génération IA : {str(e)}")

        if not menu_genere or not menu_genere.menu_semaine:
            raise HTTPException(status_code=502, detail="Le LLM n'a retourné aucune recette exploitable.")

        # 6. Contrôle de plausibilité (garde-fou anti-hallucination, cf. PRD)
        if menu_genere.cout_estime_total < 0 or menu_genere.economies_estimees < 0:
            raise HTTPException(status_code=502, detail="Coûts générés incohérents (valeur négative).")

        # 6bis. Garantie garde-manger / achats récurrents — ne pas se fier uniquement au
        # prompt : on force la cohérence programmatiquement. Défense en profondeur : si le
        # LLM a quand même écrit un achat fixe brut malgré la consigne, on le retire — il
        # sera reconstruit proprement dans sa propre section "Basiques de la semaine".
        if motifs_exclure:
            for section in (menu_genere.liste_courses.section_circulaire, menu_genere.liste_courses.section_fond_de_placard):
                section[:] = [
                    a for a in section
                    if not any(m.search(a.nom_produit.strip().lower()) for m in motifs_exclure)
                ]

        # 6ter. Garantie incontournables — le LLM les utilise parfois dans une recette sans
        # les ajouter à la liste de courses ; on vérifie et on complète nous-mêmes si besoin.
        if incontournables_termes:
            garantir_incontournables(menu_genere, incontournables_termes, tous_promos)

        # 6quinquies. Garantie ingrédients-phares (souper + lunch distinct) — même filet de
        # sécurité que les incontournables, mais pour ce que le LLM a lui-même désigné comme
        # ingrédient central de chaque recette (cf. garantir_ingredients_phares).
        garantir_ingredients_phares(menu_genere, tous_promos, motifs_exclure)

        # 6quater. Recalcul déterministe des coûts des sections gérées par le LLM (fond de
        # placard + circulaire), à partir des vrais prix plutôt que des estimations du LLM.
        recalculer_couts_reels(menu_genere, tous_promos, historique_categorie)

        # 7. Totaux finaux (LLM + achats fixes "Basiques de la semaine") et vérification du
        # budget sur le total réel.
        menu_data = menu_genere.model_dump()
        menu_data["liste_courses"]["section_achats_fixes"] = achats_fixes
        menu_data["cout_estime_total"] = round(menu_data["cout_estime_total"] + cout_achats_fixes, 2)
        menu_data["economies_estimees"] = round(menu_data["economies_estimees"] + economies_achats_fixes, 2)

        cout_total = menu_data["cout_estime_total"]
        respecte_reellement = budget_max is None or cout_total <= budget_max * 1.05
        if menu_data["budget_respecte"] and not respecte_reellement:
            menu_data["budget_respecte"] = False
            menu_data["message_avertissement"] = (
                (menu_data.get("message_avertissement") or "")
                + f" Coût réel recalculé ({cout_total:.2f} $) au-delà du budget de {budget_max} $."
            )
        else:
            menu_data["budget_respecte"] = respecte_reellement

        # Garde-fou anti-hallucination : la règle 1 du prompt dit au LLM de n'écrire un
        # message_avertissement QUE s'il réduit réellement le nombre de jours couverts.
        # Observé empiriquement (tests du 2026-09-08) : le LLM écrit parfois un message du
        # type "budget insuffisant" alors que le menu couvre bien 7 jours et respecte
        # largement le budget une fois les coûts recalculés côté serveur — un message
        # halluciné, contradictoire avec les faits, qui partait tel quel vers l'utilisateur.
        # On ne garde le message brut du LLM que quand il correspond à un vrai jour réduit ;
        # les seuls avertissements affichés dans les autres cas sont ceux calculés plus bas
        # par le serveur lui-même (dépassement de budget, diversité limitée).
        if menu_data["jours_couverts"] >= 7 and respecte_reellement:
            menu_data["message_avertissement"] = None

        raison_manque_diversite = verifier_diversite_menu(menu_genere)
        raison_manque_panier = verifier_couverture_panier(
            menu_data["liste_courses"], tous_promos, menu_data["jours_couverts"]
        )
        sous_utilise = budget_max is not None and respecte_reellement and cout_total < budget_max * 0.90
        if sous_utilise:
            raison_sous_budget = (
                f"seulement {cout_total:.2f} $ utilisés sur {budget_max} $ disponibles "
                f"({cout_total / budget_max * 100:.0f}%), pour {menu_data['jours_couverts']} jours couverts"
            )
            if menu_data["jours_couverts"] < 7:
                cout_par_jour_actuel = cout_total / menu_data["jours_couverts"]
                jours_atteignables = int(budget_max / cout_par_jour_actuel) if cout_par_jour_actuel > 0 else 7
                raison_sous_budget += (
                    ". Ce n'est PAS un problème de budget insuffisant : il reste clairement de l'argent disponible. "
                    "Ne réduis PAS le nombre de jours à cause de la taille de la liste de promotions — complète "
                    "avec des ingrédients hors promotion autant que nécessaire pour couvrir 7 jours complets. "
                    f"IMPORTANT : garde le MÊME niveau de dépense par jour que cette proposition (environ "
                    f"{cout_par_jour_actuel:.2f} $/jour, ce qui permettrait d'atteindre {min(7, jours_atteignables)} "
                    "jours) — ne repars pas sur des choix plus coûteux pour les nouveaux jours ajoutés, ou tu "
                    "dépasseras à nouveau le budget."
                )
        else:
            raison_sous_budget = None

        if not respecte_reellement and budget_max:
            jours_actuels = menu_data["jours_couverts"]
            # Suggestion arithmétique plutôt qu'une consigne vague : réduit les jours
            # proportionnellement au dépassement constaté (ex. 7 jours à 124% du budget ->
            # viser ~5-6 jours), pour donner au LLM un objectif concret à la place d'un
            # "réduis si besoin" qu'il a tendance à ignorer.
            jours_suggeres = max(1, int(jours_actuels * budget_max / cout_total))
            raison_depassement = (
                f"le menu à {jours_actuels} jours coûte {cout_total:.2f} $ pour un budget de {budget_max} $ "
                f"(dépassement de {(cout_total / budget_max - 1) * 100:.0f}%) — vise environ {jours_suggeres} jour(s) cette fois"
            )
        else:
            raison_depassement = None

        # On garde la MEILLEURE tentative, pas systématiquement la dernière — une relance
        # peut corriger un problème mais en introduire/aggraver un autre (ex. la 2e
        # tentative propose moins de jours pour paraître "mieux utiliser" le budget, ou
        # pire, dépasse le budget). Priorité stricte : 1) respecter le budget, 2) diversité
        # des protéines, 3) MAXIMISER le nombre de jours couverts (moins de jours est
        # toujours pire pour l'utilisateur, même si le % de budget utilisé est meilleur),
        # 4) minimiser l'écart en dessous de 90% d'utilisation à nombre de jours égal (si le
        # budget est respecté) OU minimiser le dépassement à nombre de jours égal (sinon).
        diversite_ok = not raison_manque_diversite and not raison_manque_panier
        jours_couverts = menu_data["jours_couverts"]
        if budget_max is None:
            ecart_budget = 0.0
        elif respecte_reellement:
            ecart_budget = max(0.0, budget_max * 0.90 - cout_total)
        else:
            # Bug corrigé (2026-09-15) : la formule ci-dessus plafonne à 0.0 dès que le
            # budget est dépassé, rendant impossible de distinguer un dépassement de 73%
            # d'un dépassement de 160% — la toute première tentative "gagnait" par défaut
            # même quand une tentative ultérieure, bien meilleure, existait. On mesure ici
            # le dépassement réel plutôt qu'un écart plafonné à zéro.
            ecart_budget = cout_total - budget_max
        if respecte_reellement:
            # Parmi des tentatives qui respectent TOUTES le budget : plus de jours
            # d'abord, puis se rapprocher de 90% d'utilisation à nombre de jours égal.
            tier3_gagne = jours_couverts > meilleurs_jours_couverts
            tier4_gagne = jours_couverts == meilleurs_jours_couverts and ecart_budget < meilleur_ecart_budget
        else:
            # Bug corrigé (2026-09-15) : quand AUCUNE tentative ne respecte le budget,
            # comparer "plus de jours" avant l'écart de budget faisait gagner un menu à
            # 7 jours mais 310% au-dessus du budget contre un menu à 1 jour à seulement
            # 16% au-dessus — alors que le premier n'est pas plus réalisable pour
            # l'utilisateur que le second, juste plus ambitieux sur le papier. Dans ce
            # cas, on se rapproche d'abord du budget, le nombre de jours ne départageant
            # qu'à écart égal.
            tier3_gagne = ecart_budget < meilleur_ecart_budget
            tier4_gagne = ecart_budget == meilleur_ecart_budget and jours_couverts > meilleurs_jours_couverts

        est_meilleure = (
            meilleur_menu_data is None
            or (respecte_reellement and not meilleur_respecte)
            or (respecte_reellement == meilleur_respecte and diversite_ok and not meilleure_diversite_ok)
            or (respecte_reellement == meilleur_respecte and diversite_ok == meilleure_diversite_ok and tier3_gagne)
            or (respecte_reellement == meilleur_respecte and diversite_ok == meilleure_diversite_ok and tier4_gagne)
        )

        if est_meilleure:
            meilleur_menu_data = menu_data
            meilleur_respecte = respecte_reellement
            meilleure_diversite_ok = diversite_ok
            meilleurs_jours_couverts = jours_couverts
            meilleur_ecart_budget = ecart_budget
            meilleure_raison_diversite = raison_manque_diversite
            meilleure_raison_panier = raison_manque_panier

        if not raison_manque_diversite and not raison_manque_panier and not raison_sous_budget and not raison_depassement:
            break

    menu_data = meilleur_menu_data
    if meilleure_raison_diversite:
        menu_data["message_avertissement"] = (
            (menu_data.get("message_avertissement") or "") + f" Diversité limitée cette semaine : {meilleure_raison_diversite}."
        )
    if meilleure_raison_panier:
        menu_data["message_avertissement"] = (
            (menu_data.get("message_avertissement") or "") + f" Panier peu équilibré cette semaine : {meilleure_raison_panier}."
        )
    # Le sous-usage du budget n'est pas signalé à l'utilisateur : ce n'est pas un problème
    # pour lui (il dépense moins que prévu), seulement un signal interne pour la relance.

    menu_data["cache_key"] = cache_key

    try:
        insert_resp = supabase.table("menus").insert({
            "user_id": payload.user_id,
            "menu_data": menu_data,
        }).execute()
        return insert_resp.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de sauvegarde du menu : {str(e)}")
