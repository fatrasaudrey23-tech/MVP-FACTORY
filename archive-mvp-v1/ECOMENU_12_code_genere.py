import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import os
from typing import Optional

# Configuration du logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Base ORM (à importer depuis un module models.py si existant)
Base = declarative_base()

# Modèle d'exemple pour l'enseigne (à déplacer dans models.py)
class Brand(Base):
    __tablename__ = 'brands'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_reference = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Brand(id={self.id}, name='{self.name}', is_reference={self.is_reference})>"


class ReferenceBrandsService:
    """
    Service dédié à la gestion et la sélection des enseignes de référence.
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialise le service avec l'URL de la base de données.
        L'URL peut être fournie explicitement ou via la variable d'environnement DATABASE_URL.
        """
        # from dotenv import load_dotenv # Si utilisé
        # load_dotenv() # Charger les variables d'environnement si .env est utilisé
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            logger.error("L'URL de la base de données n'est pas configurée. Veuillez fournir 'database_url' ou définir la variable d'environnement 'DATABASE_URL'.")
            raise ValueError("DATABASE_URL non configurée.")
        
        self.engine = self._create_database_engine()
        Base.metadata.create_all(self.engine) # Création des tables si elles n'existent pas
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info("ReferenceBrandsService initialisé.")

    def _create_database_engine(self):
        """
        Crée et retourne l'engine SQLAlchemy pour la connexion à la base de données.
        """
        try:
            engine = create_engine(self.database_url)
            # Tester la connexion
            with engine.connect() as connection:
                connection.execute("SELECT 1")
            logger.info("Connexion à la base de données établie avec succès.")
            return engine
        except Exception as e:
            logger.exception(f"Échec de la connexion à la base de données: {e}")
            raise

    def get_reference_brands(self) -> list[Brand]:
        """
        Récupère toutes les enseignes marquées comme 'de référence'.
        """
        session = self.SessionLocal()
        try:
            brands = session.query(Brand).filter(Brand.is_reference == True).all()
            logger.info(f"Récupération de {len(brands)} enseignes de référence.")
            return brands
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Erreur lors de la récupération des enseignes de référence: {e}")
            raise
        finally:
            session.close()

    def get_brand_by_id(self, brand_id: int) -> Optional[Brand]:
        """
        Récupère une enseigne spécifique par son ID, qu'elle soit de référence ou non.
        """
        session = self.SessionLocal()
        try:
            brand = session.query(Brand).filter(Brand.id == brand_id).first()
            if brand:
                logger.info(f"Enseigne trouvée avec l'ID {brand_id}: {brand.name}.")
            else:
                logger.warning(f"Aucune enseigne trouvée avec l'ID {brand_id}.")
            return brand
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Erreur lors de la récupération de l'enseigne {brand_id}: {e}")
            raise
        finally:
            session.close()

    def mark_brand_as_reference(self, brand_id: int) -> bool:
        """
        Marque une enseigne existante comme "de référence".
        Retourne True si l'opération réussit, False sinon.
        """
        session = self.SessionLocal()
        try:
            brand = session.query(Brand).filter(Brand.id == brand_id).first()
            if brand:
                if not brand.is_reference:
                    brand.is_reference = True
                    session.add(brand)
                    session.commit()
                    session.refresh(brand)
                    logger.info(f"L'enseigne '{brand.name}' (ID: {brand_id}) a été marquée comme référence.")
                    return True
                else:
                    logger.info(f"L'enseigne '{brand.name}' (ID: {brand_id}) est déjà marquée comme référence.")
                    return True # Déjà de référence, considéré comme succès
            else:
                logger.warning(f"Impossible de marquer l'enseigne comme référence: ID {brand_id} non trouvé.")
                return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Erreur lors du marquage de l'enseigne {brand_id} comme référence: {e}")
            raise
        finally:
            session.close()

    def unmark_brand_as_reference(self, brand_id: int) -> bool:
        """
        Démarque une enseigne existante de la liste "de référence".
        Retourne True si l'opération réussit, False sinon.
        """
        session = self.SessionLocal()
        try:
            brand = session.query(Brand).filter(Brand.id == brand_id).first()
            if brand:
                if brand.is_reference:
                    brand.is_reference = False
                    session.add(brand)
                    session.commit()
                    session.refresh(brand)
                    logger.info(f"L'enseigne '{brand.name}' (ID: {brand_id}) a été démarquée de référence.")
                    return True
                else:
                    logger.info(f"L'enseigne '{brand.name}' (ID: {brand_id}) n'était déjà pas marquée comme référence.")
                    return True # Déjà pas de référence, considéré comme succès
            else:
                logger.warning(f"Impossible de démarquer l'enseigne: ID {brand_id} non trouvé.")
                return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Erreur lors du démarquage de l'enseigne {brand_id}: {e}")
            raise
        finally:
            session.close()

    def add_brand(self, name: str, is_reference: bool = False) -> Brand:
        """
        Ajoute une nouvelle enseigne à la base de données.
        """
        session = self.SessionLocal()
        try:
            new_brand = Brand(name=name, is_reference=is_reference)
            session.add(new_brand)
            session.commit()
            session.refresh(new_brand)
            logger.info(f"Nouvelle enseigne '{name}' ajoutée avec l'ID {new_brand.id}.")
            return new_brand
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Erreur lors de l'ajout de l'enseigne '{name}': {e}")
            raise
        finally:
            session.close()

    def list_all_brands(self) -> list[Brand]:
        """
        Récupère toutes les enseignes existantes dans la base de données.
        """
        session = self.SessionLocal()
        try:
            brands = session.query(Brand).all()
            logger.info(f"Récupération de {len(brands)} enseignes au total.")
            return brands
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Erreur lors de la récupération de toutes les enseignes: {e}")
            raise
        finally:
            session.close()