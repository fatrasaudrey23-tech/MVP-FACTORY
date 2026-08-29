import hashlib
import os
import secrets
import string

import psycopg2
from psycopg2.extras import Json

_db_available = False

# Alphabet sans caractères ambigus (pas de 0/O, 1/I/l) pour les codes de récupération
_ALPHABET_CODE = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1IL")


def _hash_code(code: str) -> str:
    """Hache un code d'accès avant stockage. Le code en clair n'est jamais persisté."""
    pepper = os.getenv("AUTH_PEPPER", "therapelio-pepper-defaut")
    return hashlib.sha256(f"{pepper}:{code.strip().upper()}".encode()).hexdigest()


def init_db():
    """Crée/complète les tables nécessaires. Ne bloque jamais le démarrage de l'API."""
    global _db_available
    # Lu au moment de l'appel (et non à l'import) : main.py charge le .env avant
    # d'appeler init_db(), mais l'import de ce module peut survenir avant ce chargement.
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("⚠️ DATABASE_URL absent : fonctionnalités liées à la base désactivées.")
        return
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS crisis_events (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        session_id VARCHAR(255) NOT NULL,
                        niveau_risque INTEGER NOT NULL CHECK (niveau_risque IN (3, 4)),
                        categories_detectees JSONB,
                        action_taken VARCHAR(255) NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_crisis_events_session_id ON crisis_events(session_id);"
                )
                # Complète le schéma existant (companies / end_users) pour le login
                # pseudonyme : code d'entreprise + prénom/poste + code personnel haché.
                cur.execute(
                    "ALTER TABLE companies ADD COLUMN IF NOT EXISTS registration_code VARCHAR(30) UNIQUE;"
                )
                cur.execute(
                    "ALTER TABLE end_users ADD COLUMN IF NOT EXISTS prenom VARCHAR(100);"
                )
                cur.execute(
                    "ALTER TABLE end_users ADD COLUMN IF NOT EXISTS poste VARCHAR(100);"
                )
            conn.commit()
        _db_available = True
        print("✅ Connexion base de données OK, schéma à jour.")
    except Exception as e:
        print(f"⚠️ Connexion base de données impossible ({e}). Fonctionnalités liées à la base désactivées.")


def log_crisis_event(session_id: str, niveau_risque: int, categories_detectees: list, action_taken: str):
    """Journalise un événement de crise. Ne doit jamais faire échouer la réponse à l'utilisateur."""
    print(f"🚨 CRISIS EVENT | session={session_id} | niveau={niveau_risque} | action={action_taken} | categories={categories_detectees}")
    if not _db_available:
        return
    database_url = os.getenv("DATABASE_URL")
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO crisis_events (session_id, niveau_risque, categories_detectees, action_taken)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (session_id, niveau_risque, Json(categories_detectees or []), action_taken),
                )
            conn.commit()
    except Exception as e:
        print(f"⚠️ Échec de l'écriture du log de crise en base : {e}")


def register_user(registration_code: str, prenom: str, poste: str):
    """
    Crée un profil pseudonyme rattaché à l'entreprise correspondant au code fourni.
    Renvoie (user_id, recovery_code) si succès, ou None si le code entreprise est invalide/introuvable.
    Le code de récupération n'est renvoyé qu'ici, en clair, une seule fois.
    """
    if not _db_available:
        return None
    database_url = os.getenv("DATABASE_URL")
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM companies WHERE registration_code = %s AND status IN ('active', 'trial');",
                    (registration_code.strip(),),
                )
                row = cur.fetchone()
                if not row:
                    return None
                company_id = row[0]

                recovery_code = "".join(secrets.choice(_ALPHABET_CODE) for _ in range(8))
                cur.execute(
                    """
                    INSERT INTO end_users (company_id, access_token_hash, prenom, poste, status)
                    VALUES (%s, %s, %s, %s, 'active')
                    RETURNING id;
                    """,
                    (company_id, _hash_code(recovery_code), prenom.strip()[:100], (poste or "").strip()[:100]),
                )
                user_id = cur.fetchone()[0]
            conn.commit()
        return {"user_id": str(user_id), "recovery_code": recovery_code}
    except Exception as e:
        print(f"⚠️ Échec de l'inscription : {e}")
        return None


def recover_user(recovery_code: str):
    """Retrouve un profil à partir de son code de récupération. Renvoie None si non trouvé."""
    if not _db_available:
        return None
    database_url = os.getenv("DATABASE_URL")
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, prenom, poste FROM end_users WHERE access_token_hash = %s AND status = 'active';",
                    (_hash_code(recovery_code),),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {"user_id": str(row[0]), "prenom": row[1] or "", "poste": row[2] or ""}
    except Exception as e:
        print(f"⚠️ Échec de la récupération de profil : {e}")
        return None


def get_user(user_id: str):
    """Récupère prénom/poste à partir de l'identifiant de profil. Renvoie None si absent/désactivé."""
    if not _db_available or not user_id:
        return None
    database_url = os.getenv("DATABASE_URL")
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT prenom, poste FROM end_users WHERE id = %s AND status = 'active';",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {"prenom": row[0] or "", "poste": row[1] or ""}
    except Exception as e:
        print(f"⚠️ Échec de la lecture du profil : {e}")
        return None
