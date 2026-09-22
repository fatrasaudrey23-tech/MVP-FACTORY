import os
import requests
import json
import time
from typing import Dict, List
from pydantic import BaseModel
import anthropic
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(base_dir, '.env'))

print("🇨🇦 [CONNECTEUR FLIPP] Extraction de toutes les promos alimentaires de Montréal...")

POSTAL_CODE = "H2X1Y8"
BASE_URL = "https://backflipp.wishabi.com/flipp"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
CATEGORIE_FLIPP_ALIMENTAIRE = "Food, Beverages & Tobacco"

# Liste prédéfinie (contrôle de plausibilité, cf. PRD section 3) : toute catégorie
# retournée par le LLM qui n'en fait pas partie est ramenée à "Épicerie".
CATEGORIES_ALIMENTAIRES = [
    "Fruits & Légumes",
    "Boucherie",
    "Poissonnerie",
    "Produits Laitiers",
    "Boulangerie",
    "Charcuterie",
    "Surgelés",
    "Boissons",
    "Épicerie",
    "Prêt-à-manger",
]

TAILLE_LOT_CLASSIFICATION = 40

_anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if _anthropic_api_key:
    _anthropic_api_key = _anthropic_api_key.strip().replace("\n", "").replace("\r", "").replace('"', '').replace("'", "")
claude_client = anthropic.Anthropic(api_key=_anthropic_api_key) if _anthropic_api_key else None
CLAUDE_MODEL = "claude-sonnet-5"


class ProduitClassifie(BaseModel):
    nom_produit: str
    categorie_alimentaire: str
    tag_standard: str


class LotClassification(BaseModel):
    produits: List[ProduitClassifie]


def classifier_produits_llm(noms_produits: List[str]) -> Dict[str, dict]:
    """Catégorisation fine par LLM (cf. PRD Epic 2 / US 2.2 - 'Extraction et Structuration
    des Offres par LLM'). Pour chaque nom de produit unique, fait correspondre :
    - categorie_alimentaire : une catégorie parmi CATEGORIES_ALIMENTAIRES
    - tag_standard : l'ingrédient normalisé (singulier, sans marque ni format),
      ex. 'Tomates italiennes en grappe' -> 'tomate'.
    Traite par lots pour limiter le nombre d'appels API. Best-effort : un lot en échec
    est simplement absent du résultat, l'appelant garde alors sa valeur de repli."""
    if not claude_client or not noms_produits:
        return {}

    resultats: Dict[str, dict] = {}
    noms_uniques = sorted(set(noms_produits))
    lots = [
        noms_uniques[i:i + TAILLE_LOT_CLASSIFICATION]
        for i in range(0, len(noms_uniques), TAILLE_LOT_CLASSIFICATION)
    ]

    for i, lot in enumerate(lots, start=1):
        print(f"🧠 Classification IA du lot {i}/{len(lots)} ({len(lot)} produits)...")
        prompt = (
            "Tu es un catégoriseur de produits d'épicerie. Pour CHAQUE nom de produit "
            "ci-dessous, retourne exactement un objet avec :\n"
            f"- nom_produit : recopié EXACTEMENT tel quel (aucune modification)\n"
            f"- categorie_alimentaire : une valeur EXACTE parmi {CATEGORIES_ALIMENTAIRES}\n"
            "- tag_standard : l'ingrédient de base normalisé, en français, au singulier, "
            "en minuscules, SANS marque ni format ni quantité "
            "(ex. 'Tomates italiennes en grappe' -> 'tomate', "
            "'Poulet entier Metro 1kg' -> 'poulet', "
            "'Fromage cheddar fort Agropur 400g' -> 'fromage cheddar').\n\n"
            "Ne saute aucun produit, retourne-en autant que fournis en entrée.\n\n"
            "PRODUITS :\n" + "\n".join(f"- {n}" for n in lot)
        )
        try:
            # Streaming plutôt qu'appel bloquant, et thinking désactivé (tâche de mise en
            # forme structurée, pas de raisonnement) : cf. la même note dans
            # main.py::generate_menu.
            with claude_client.with_options(timeout=60.0).messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system="Tu réponds uniquement avec des données structurées valides.",
                messages=[{"role": "user", "content": prompt}],
                output_format=LotClassification,
                thinking={"type": "disabled"},
            ) as stream:
                completion = stream.get_final_message()
            lot_classifie = completion.parsed_output
        except Exception as e:
            print(f"⚠️ Échec de classification IA sur le lot {i} : {e}")
            continue

        if not lot_classifie:
            continue

        for produit in lot_classifie.produits:
            categorie = produit.categorie_alimentaire
            if categorie not in CATEGORIES_ALIMENTAIRES:
                categorie = "Épicerie"  # contrôle de plausibilité : catégorie hors-liste
            tag = (produit.tag_standard or "").strip().lower()
            if not tag:
                continue  # contrôle de plausibilité : tag vide rejeté
            resultats[produit.nom_produit] = {
                "categorie_alimentaire": categorie,
                "tag_standard": tag,
            }

        time.sleep(0.2)

    return resultats


def decouvrir_enseignes_epicerie(code_postal):
    """Interroge Flipp pour la liste des circulaires actives du secteur et retient les
    enseignes de la catégorie 'Groceries'. Aucune liste d'enseignes codée en dur :
    si une nouvelle épicerie publie une circulaire dans le secteur, elle est captée
    automatiquement au prochain run."""
    try:
        res = requests.get(
            f"{BASE_URL}/flyers",
            headers=HEADERS,
            params={"postal_code": code_postal},
            timeout=15,
        )
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠️ Impossible de récupérer la liste des circulaires : {e}")
        return []

    flyers = res.json().get("flyers", [])
    enseignes = sorted({
        f["merchant"] for f in flyers
        if "Groceries" in f.get("categories", []) and f.get("merchant")
    })
    print(f"🏪 {len(enseignes)} enseignes d'épicerie détectées : {', '.join(enseignes)}")
    return enseignes


def collecter_promos_enseigne(enseigne, code_postal):
    """Récupère les articles en circulaire pour une enseigne donnée, puis ne garde que
    ceux que Flipp lui-même classe comme alimentaires (champ _L1), au lieu de filtrer
    sur une liste de mots-clés produits devinés à l'avance."""
    try:
        res = requests.get(
            f"{BASE_URL}/items/search",
            headers=HEADERS,
            params={"q": enseigne, "postal_code": code_postal},
            timeout=15,
        )
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠️ Échec de récupération pour {enseigne} : {e}")
        return []

    items = res.json().get("items", [])
    return [
        item for item in items
        if item.get("item_type") == "flyer"
        and item.get("merchant_name") == enseigne
        and item.get("_L1") == CATEGORIE_FLIPP_ALIMENTAIRE
    ]


def nettoyer_nom_produit(nom_brut):
    """Nettoie le texte commercial, retire le bilinguisme après le pipe ou la virgule."""
    if not nom_brut:
        return ""
    nom_nettoye = nom_brut.split('|')[0].split(',')[0]
    return nom_nettoye.strip().capitalize()


def determiner_tag_standard(nom_brut, sous_categorie_flipp):
    """Dérive un tag standard simple à partir de la sous-catégorie Flipp (_L2) ou, à
    défaut, du premier mot du nom du produit. Sert de base grossière pour le futur
    matching produit <-> ingrédient de recette ; un affinage (ex: LLM) reste à faire."""
    base = (sous_categorie_flipp or nom_brut or "").lower().strip()
    mots = base.replace("-", " ").split()
    return mots[0] if mots else "autre"


def executer_pipeline():
    enseignes_epicerie = decouvrir_enseignes_epicerie(POSTAL_CODE)
    promotions_nettoyees = []
    deja_vus = set()

    for enseigne in enseignes_epicerie:
        print(f"🛰️ Collecte des promos alimentaires chez : {enseigne}")
        items_alimentaires = collecter_promos_enseigne(enseigne, POSTAL_CODE)

        for item in items_alimentaires:
            nom_original = item.get("name")
            prix = item.get("current_price")
            if not (nom_original and prix):
                continue

            cle_dedoublonnage = (nom_original, enseigne, prix)
            if cle_dedoublonnage in deja_vus:
                continue
            deja_vus.add(cle_dedoublonnage)

            sous_categorie = item.get("_L2") or "Épicerie"
            prix_origine = item.get("original_price") or round(float(prix) * 1.30, 2)

            promotions_nettoyees.append({
                "nom_produit": nettoyer_nom_produit(nom_original),
                "categorie": sous_categorie,
                "tag_standard": determiner_tag_standard(nom_original, sous_categorie),
                "prix_origine": prix_origine,
                "prix_promo": float(prix),
                "unite": "chacun",
                "enseigne": enseigne,
                "date_fin": item.get("valid_to"),
            })

        time.sleep(0.3)  # on ménage l'API entre deux enseignes

    # --- CATÉGORISATION FINE PAR LLM ---
    if claude_client:
        noms_a_classifier = [p["nom_produit"] for p in promotions_nettoyees]
        classification = classifier_produits_llm(noms_a_classifier)
        n_classifies = 0
        for p in promotions_nettoyees:
            classe = classification.get(p["nom_produit"])
            if classe:
                p["categorie"] = classe["categorie_alimentaire"]
                p["tag_standard"] = classe["tag_standard"]
                n_classifies += 1
        print(f"🧠 [CLASSIFICATION IA] {n_classifies}/{len(promotions_nettoyees)} promos catégorisées finement "
              f"(le reste garde la catégorie Flipp brute en repli).")
    else:
        print("⚠️ OPENAI_API_KEY manquante : catégorisation fine ignorée, catégories Flipp brutes conservées.")

    # Structuration finale respectant l'architecture
    donnees_mvp = {
        "promotions": promotions_nettoyees,
        "enseigne_selection": [
            {"nom_enseigne": e, "distance_max_km": 5, "fidelite_uniquement": False}
            for e in enseignes_epicerie
        ],
    }

    with open(os.path.join(base_dir, "data_live.json"), "w", encoding="utf-8") as f:
        json.dump(donnees_mvp, f, indent=4, ensure_ascii=False)

    print(
        f"💾 [CONNECTEUR FLIPP] Terminé : {len(promotions_nettoyees)} promos alimentaires "
        f"collectées sur {len(enseignes_epicerie)} enseignes."
    )


if __name__ == "__main__":
    executer_pipeline()
