import requests
import json
import time

print("🇨🇦 [CONNECTEUR FLIPP ENRICHI] Extraction et nettoyage des données de Montréal...")

POSTAL_CODE = "H2X 1Y8"
# On élargit les mots-clés pour capter ce qu'on a vu dans ta table Metro
MOTS_CLES = ["laitue", "fromage", "bière", "lait", "porc", "crevettes", "saumon", "bifteck", "tomates", "pain"]

def determiner_tag_et_categorie(nom_brut):
    """Analyse le nom du produit pour en extraire un tag standard et une catégorie propre."""
    nom_lower = nom_brut.lower()
    
    # Dictionnaire de correspondance Mots-clés -> [Tag Standard, Catégorie]
    regles = {
        "laitue": ("laitue", "Fruits & Légumes"),
        "tomates": ("tomate", "Fruits & Légumes"),
        "fromage": ("fromage", "Produits Laitiers"),
        "lait": ("lait", "Produits Laitiers"),
        "porc": ("porc", "Boucherie"),
        "bifteck": ("bœuf", "Boucherie"),
        "tournedos": ("bœuf", "Boucherie"),
        "crevettes": ("crevette", "Poissonnerie"),
        "saumon": ("saumon", "Poissonnerie"),
        "homard": ("homard", "Poissonnerie"),
        "pain": ("pain", "Boulangerie"),
        "bière": ("bière", "Boissons")
    }
    
    for cle, (tag, cat) in regles.items():
        if cle in nom_lower:
            return tag, cat
            
    return "autre", "Épicerie"

def nettoyer_nom_produit(nom_brut):
    """Nettoie le texte commercial, retire le bilinguisme après le pipe ou la virgule."""
    if not nom_brut:
        return ""
    
    # On sépare si présence de "|" ou "," pour enlever la partie anglaise ou les mentions inutiles
    nom_nettoye = nom_brut.split('|')[0].split(',')[0]
    
    # On remet en jolie casse (première lettre en majuscule, le reste en minuscule)
    return nom_nettoye.strip().capitalize()

# --- PIPELINE D'EXTRACTION ---
promotions_nettoyees = []
enseignes_detectees = []

def collecter_flipp(mot_cle, code_postal):
    url = "https://backflipp.wishabi.com/flipp/items/search"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    try:
        res = requests.get(url, headers=headers, params={"q": mot_cle, "postal_code": code_postal}, timeout=10)
        return res.json().get("items", []) if res.ok else []
    except:
        return []

for mc in MOTS_CLES:
    print(f"🛰️ Analyse et filtrage sur Flipp pour : [{mc}]")
    items = collecter_flipp(mc, POSTAL_CODE)
    
    for item in items[:4]: # On prend les 4 meilleures offres par catégorie
        nom_original = item.get("name")
        prix = item.get("current_price")
        enseigne = item.get("merchant_name")
        unite_brute = item.get("current_price_display_string") # Souvent là où se cache le 'chacun' ou 'lb'
        
        if nom_original and prix and enseigne:
            # Application de notre pipeline d'enrichissement intelligent
            nom_propre = nettoyer_nom_produit(nom_original)
            tag_standard, categorie_propre = determiner_tag_et_categorie(nom_original)
            
            promotions_nettoyees.append({
                "nom_produit": nom_propre,
                "categorie": categorie_propre,
                "tag_standard": tag_standard,
                "prix_origine": float(prix) * 1.30, # Simulation prix d'origine
                "prix_promo": float(prix),
                "unite": str(unite_brute) if unite_brute else "chacun",
                "date_fin": "2026-06-30"
            })
            
            if enseigne not in enseignes_detectees:
                enseignes_detectees.append(enseigne)
                
    time.sleep(0.3)

# Structuration finale respectant l'architecture
donnees_mvp = {
    "promotions": promotions_nettoyees,
    "enseigne_selection": [{"nom_enseigne": e, "distance_max_km": 5, "fidelite_uniquement": False} for e in enseignes_detectees],
    "menus": [
        {
            "titre_recette": "Salade fraîche et Laitue croquante",
            "jours_semaine": "Lundi",
            "score_eco_score": "A",
            "temps_preparation_min": 15
        },
        {
            "titre_recette": "Sauté de Porc aux tomates fraîches",
            "jours_semaine": "Mardi",
            "score_eco_score": "B",
            "temps_preparation_min": 25
        }
    ]
}

with open("data_live.json", "w", encoding="utf-8") as f:
    json.dump(donnees_mvp, f, indent=4, ensure_ascii=False)

print(f"💾 [CONNECTEUR FLIPP] Pipeline de nettoyage terminé ! {len(promotions_nettoyees)} produits enrichis dans 'data_live.json'.")