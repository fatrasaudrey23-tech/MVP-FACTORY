import os

import psycopg2
from psycopg2.extras import Json

_db_available = False


def init_db():
    """Crée la table de logs de crise si besoin. Ne bloque jamais le démarrage de l'API."""
    global _db_available
    # Lu au moment de l'appel (et non à l'import) : main.py charge le .env avant
    # d'appeler init_db(), mais l'import de ce module peut survenir avant ce chargement.
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("⚠️ DATABASE_URL absent : logging des urgences en console uniquement.")
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
            conn.commit()
        _db_available = True
        print("✅ Connexion base de données OK, table crisis_events prête.")
    except Exception as e:
        print(f"⚠️ Connexion base de données impossible ({e}). Logging des urgences en console uniquement.")


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
