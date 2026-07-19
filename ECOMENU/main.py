import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from supabase import create_client, Client
from dotenv import load_dotenv

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

app = FastAPI(title="EcoMenu API", version="1.0.0")

# Configuration du CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "online", "security": "high", "project": "EcoMenu"}

# ==========================================
# SCHÉMAS DE VALIDATION PYDANTIC
# ==========================================

class UsersSchema(BaseModel):
    budget_max: Optional[float] = None
    taille_foyer: Optional[int] = None
    gestion_restes: Optional[bool] = None
    type_boite_lunch: Optional[str] = None
    profil_boite_lunch: Optional[str] = None

class Enseigne_selectionSchema(BaseModel):
    user_id: Optional[str] = None
    enseigne: Optional[str] = None

class PromotionsSchema(BaseModel):
    enseigne: Optional[str] = None
    nom_produit: Optional[str] = None
    prix_promo: Optional[float] = None
    poids_volume: Optional[str] = None
    unite_mesure: Optional[str] = None
    categorie_alimentaire: Optional[str] = None

class Produit_tagsSchema(BaseModel):
    nom_produit: Optional[str] = None
    tag_standard: Optional[str] = None

class MenusSchema(BaseModel):
    user_id: Optional[str] = None
    menu_data: Optional[str] = None
    date_generation: Optional[str] = None

# ==========================================
# ROUTES SÉCURISÉES (GET & POST)
# ==========================================

@app.get("/api/v1/users", tags=["users"], response_model=List[dict])
def get_users():
    try:
        response = supabase.table("users").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")

@app.post("/api/v1/users", tags=["users"], response_model=List[dict])
def create_users(data: UsersSchema):
    try:
        payload = data.dict(exclude_unset=True)
        response = supabase.table("users").insert(payload).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")

@app.get("/api/v1/enseigne_selection", tags=["enseigne_selection"], response_model=List[dict])
def get_enseigne_selection():
    try:
        response = supabase.table("enseigne_selection").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")

@app.post("/api/v1/enseigne_selection", tags=["enseigne_selection"], response_model=List[dict])
def create_enseigne_selection(data: Enseigne_selectionSchema):
    try:
        payload = data.dict(exclude_unset=True)
        response = supabase.table("enseigne_selection").insert(payload).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")

@app.get("/api/v1/promotions", tags=["promotions"], response_model=List[dict])
def get_promotions():
    try:
        response = supabase.table("promotions").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")

@app.post("/api/v1/promotions", tags=["promotions"], response_model=List[dict])
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

@app.post("/api/v1/produit_tags", tags=["produit_tags"], response_model=List[dict])
def create_produit_tags(data: Produit_tagsSchema):
    try:
        payload = data.dict(exclude_unset=True)
        response = supabase.table("produit_tags").insert(payload).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")

@app.get("/api/v1/menus", tags=["menus"], response_model=List[dict])
def get_menus():
    try:
        response = supabase.table("menus").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase : {str(e)}")

@app.post("/api/v1/menus", tags=["menus"], response_model=List[dict])
def create_menus(data: MenusSchema):
    try:
        payload = data.dict(exclude_unset=True)
        response = supabase.table("menus").insert(payload).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'insertion : {str(e)}")
