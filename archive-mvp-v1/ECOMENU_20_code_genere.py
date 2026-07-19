import logging
import datetime
import typing

import sqlalchemy
from sqlalchemy import create_engine, Column, String, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field

# --- Configuration du logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Modèles SQLAlchemy ORM (définis ici pour rendre le script standalone) ---
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)

    preferred_brands = relationship("UserPreferredBrand", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id='{self.id}', name='{self.name}')>"

class Brand(Base):
    __tablename__ = 'brands'
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)

    users_who_prefer = relationship("UserPreferredBrand", back_populates="brand")

    def __repr__(self) -> str:
        return f"<Brand(id='{self.id}', name='{self.name}')>"

class UserPreferredBrand(Base):
    __tablename__ = 'user_preferred_brands'
    user_id = Column(String, ForeignKey('users.id'), primary_key=True)
    brand_id = Column(String, ForeignKey('brands.id'), primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="preferred_brands")
    brand = relationship("Brand", back_populates="users_who_prefer")

    def __repr__(self) -> str:
        return f"<UserPreferredBrand(user_id='{self.user_id}', brand_id='{self.brand_id}')>"

# --- Pydantic Models ---
class BrandResponse(BaseModel):
    id: str
    name: str
    logo_url: typing.Optional[str] = None

# --- Fonctions de service ---

def _validate_user_exists(user_id: str, db_session: Session) -> bool:
    """
    Fonction utilitaire interne pour vérifier l'existence d'un utilisateur.
    """
    try:
        user = db_session.query(User).filter(User.id == user_id).first()
        return user is not None
    except SQLAlchemyError as e:
        logger.error(f"Database error while checking user existence for ID {user_id}: {e}")
        return False

def _validate_brand_ids_exist(brand_ids: typing.List[str], db_session: Session) -> typing.Tuple[bool, typing.List[str]]:
    """
    Vérifie si une liste d'identifiants d'enseignes correspond à des enseignes existantes dans la base de données.

    Args:
        brand_ids (list[str]): La liste des identifiants d'enseignes à valider.
        db_session (Session): La session de base de données SQLAlchemy.

    Returns:
        tuple[bool, list[str]]: Un tuple contenant un booléen (True si tous les IDs sont valides, False sinon)
                                 et une liste des IDs invalides trouvés.
    """
    if not brand_ids:
        return True, []

    try:
        existing_brands = db_session.query(Brand.id).filter(Brand.id.in_(brand_ids)).all()
        existing_brand_ids = {brand_id for (brand_id,) in existing_brands}

        invalid_brand_ids = [bid for bid in brand_ids if bid not in existing_brand_ids]

        if invalid_brand_ids:
            logger.warning(f"Some brand IDs are invalid or do not exist: {invalid_brand_ids}")
            return False, invalid_brand_ids
        return True, []
    except SQLAlchemyError as e:
        logger.error(f"Database error during brand ID validation: {e}")
        return False, brand_ids # Consider all as invalid if DB error

def get_user_preferred_brands(user_id: str, db_session: Session) -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Récupère la liste des enseignes qu'un utilisateur a marquées comme préférées.

    Args:
        user_id (str): L'identifiant unique de l'utilisateur.
        db_session (Session): La session de base de données SQLAlchemy.

    Returns:
        list[dict]: Une liste de dictionnaires, où chaque dictionnaire représente une enseigne préférée
                    (ex: {'id': 'enseigne_id_1', 'name': 'Nom Enseigne 1', 'logo_url': '...'}).
                    Retourne une liste vide si aucune préférence ou si l'utilisateur n'existe pas.
    """
    try:
        if not _validate_user_exists(user_id, db_session):
            logger.info(f"User with ID {user_id} not found when retrieving preferred brands.")
            return []

        preferred_brands = db_session.query(Brand).join(UserPreferredBrand).filter(UserPreferredBrand.user_id == user_id).all()
        
        return [
            BrandResponse(
                id=brand.id,
                name=brand.name,
                logo_url=brand.logo_url
            ).dict() for brand in preferred_brands
        ]
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving preferred brands for user {user_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving preferred brands for user {user_id}: {e}")
        return []

def set_user_preferred_brands(user_id: str, brand_ids: typing.List[str], db_session: Session) -> bool:
    """
    Remplace l'intégralité de la liste des enseignes préférées d'un utilisateur par une nouvelle liste.

    Args:
        user_id (str): L'identifiant unique de l'utilisateur.
        brand_ids (list[str]): Une liste d'identifiants uniques des enseignes à définir comme préférées.
        db_session (Session): La session de base de données SQLAlchemy.

    Returns:
        bool: True si la mise à jour est réussie, False sinon.
    """
    if not _validate_user_exists(user_id, db_session):
        logger.warning(f"Cannot set preferred brands: User with ID {user_id} does not exist.")
        return False

    is_valid, invalid_ids = _validate_brand_ids_exist(brand_ids, db_session)
    if not is_valid:
        logger.warning(f"Cannot set preferred brands: Some provided brand IDs are invalid or do not exist: {invalid_ids}")
        return False

    try:
        db_session.begin_nested() 

        db_session.query(UserPreferredBrand).filter(UserPreferredBrand.user_id == user_id).delete(synchronize_session=False)

        for brand_id in brand_ids:
            new_preference = UserPreferredBrand(user_id=user_id, brand_id=brand_id)
            db_session.add(new_preference)

        db_session.commit()
        logger.info(f"Successfully set preferred brands for user {user_id} to {brand_ids}")
        return True
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Database error setting preferred brands for user {user_id}: {e}")
        return False
    except Exception as e:
        db_session.rollback()
        logger.error(f"An unexpected error occurred while setting preferred brands for user {user_id}: {e}")
        return False

def add_preferred_brand(user_id: str, brand_id: str, db_session: Session) -> bool:
    """
    Ajoute une seule enseigne à la liste des enseignes préférées d'un utilisateur.

    Args:
        user_id (str): L'identifiant unique de l'utilisateur.
        brand_id (str): L'identifiant unique de l'enseigne à ajouter.
        db_session (Session): La session de base de données SQLAlchemy.

    Returns:
        bool: True si l'enseigne a été ajoutée (ou existait déjà), False si une erreur est survenue
              (ex: ID invalide, erreur DB).
    """
    if not _validate_user_exists(user_id, db_session):
        logger.warning(f"Cannot add preferred brand: User with ID {user_id} does not exist.")
        return False

    is_valid_brand, _ = _validate_brand_ids_exist([brand_id], db_session)
    if not is_valid_brand:
        logger.warning(f"Cannot add preferred brand: Brand with ID {brand_id} does not exist.")
        return False

    try:
        existing_preference = db_session.query(UserPreferredBrand).filter(
            UserPreferredBrand.user_id == user_id,
            UserPreferredBrand.brand_id == brand_id
        ).first()

        if existing_preference:
            logger.info(f"Brand {brand_id} is already a preferred brand for user {user_id}. Operation is idempotent.")
            return True

        new_preference = UserPreferredBrand(user_id=user_id, brand_id=brand_id)
        db_session.add(new_preference)
        db_session.commit()
        logger.info(f"Successfully added brand {brand_id} as preferred for user {user_id}.")
        return True
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Database error adding preferred brand {brand_id} for user {user_id}: {e}")
        return False
    except Exception as e:
        db_session.rollback()
        logger.error(f"An unexpected error occurred while adding preferred brand {brand_id} for user {user_id}: {e}")
        return False

def remove_preferred_brand(user_id: str, brand_id: str, db_session: Session) -> bool:
    """
    Supprime une seule enseigne de la liste des enseignes préférées d'un utilisateur.

    Args:
        user_id (str): L'identifiant unique de l'utilisateur.
        brand_id (str): L'identifiant unique de l'enseigne à supprimer.
        db_session (Session): La session de base de données SQLAlchemy.

    Returns:
        bool: True si l'enseigne a été supprimée (ou n'existait pas), False si une erreur est survenue.
    """
    if not _validate_user_exists(user_id, db_session):
        logger.warning(f"Cannot remove preferred brand: User with ID {user_id} does not exist.")
        return False

    try:
        deleted_count = db_session.query(UserPreferredBrand).filter(
            UserPreferredBrand.user_id == user_id,
            UserPreferredBrand.brand_id == brand_id
        ).delete(synchronize_session=False)
        
        db_session.commit()

        if deleted_count > 0:
            logger.info(f"Successfully removed brand {brand_id} from preferred brands for user {user_id}.")
        else:
            logger.info(f"Brand {brand_id} was not found in preferred brands for user {user_id}. No action taken.")
        return True
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Database error removing preferred brand {brand_id} for user {user_id}: {e}")
        return False
    except Exception as e:
        db_session.rollback()
        logger.error(f"An unexpected error occurred while removing preferred brand {brand_id} for user {user_id}: {e}")
        return False

# --- Exemple d'utilisation (pour rendre le script exécutable et tester les fonctions) ---
if __name__ == "__main__":
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()

    try:
        user1 = User(id="user1", name="Alice")
        user2 = User(id="user2", name="Bob")
        brandA = Brand(id="brandA", name="Brand Alpha", logo_url="http://example.com/alpha.png")
        brandB = Brand(id="brandB", name="Brand Beta", logo_url="http://example.com/beta.png")
        brandC = Brand(id="brandC", name="Brand Gamma", logo_url="http://example.com/gamma.png")
        brandD = Brand(id="brandD", name="Brand Delta", logo_url="http://example.com/delta.png")

        db.add_all([user1, user2, brandA, brandB, brandC, brandD])
        db.commit()

        logger.info("\n--- Test get_user_preferred_brands (empty initially) ---")
        prefs = get_user_preferred_brands("user1", db)
        print(f"User1 preferred brands: {prefs}") 

        logger.info("\n--- Test set_user_preferred_brands ---")
        success = set_user_preferred_brands("user1", ["brandA", "brandB"], db)
        print(f"Set brands for user1 successful: {success}") 
        prefs = get_user_preferred_brands("user1", db)
        print(f"User1 preferred brands after set: {prefs}") 

        logger.info("\n--- Test set_user_preferred_brands with some invalid IDs ---")
        success = set_user_preferred_brands("user1", ["brandA", "invalid_brand_id"], db)
        print(f"Set brands for user1 with invalid ID successful: {success}") 
        prefs = get_user_preferred_brands("user1", db)
        print(f"User1 preferred brands after failed set: {prefs}") 

        logger.info("\n--- Test add_preferred_brand ---")
        success = add_preferred_brand("user1", "brandC", db)
        print(f"Add brandC for user1 successful: {success}") 
        prefs = get_user_preferred_brands("user1", db)
        print(f"User1 preferred brands after add: {prefs}") 

        logger.info("\n--- Test add_preferred_brand (already exists) ---")
        success = add_preferred_brand("user1", "brandC", db)
        print(f"Add brandC again for user1 successful (idempotent): {success}") 
        prefs = get_user_preferred_brands("user1", db)
        print(f"User1 preferred brands after idempotent add: {prefs}") 

        logger.info("\n--- Test add_preferred_brand with invalid brand ID ---")
        success = add_preferred_brand("user1", "non_existent_brand", db)
        print(f"Add non_existent_brand for user1 successful: {success}") 

        logger.info("\n--- Test add_preferred_brand for non-existent user ---")
        success = add_preferred_brand("non_existent_user", "brandA", db)
        print(f"Add brandA for non_existent_user successful: {success}") 

        logger.info("\n--- Test remove_preferred_brand ---")
        success = remove_preferred_brand("user1", "brandB", db)
        print(f"Remove brandB for user1 successful: {success}") 
        prefs = get_user_preferred_brands("user1", db)
        print(f"User1 preferred brands after remove: {prefs}") 

        logger.info("\n--- Test remove_preferred_brand (does not exist) ---")
        success = remove_preferred_brand("user1", "brandD", db)
        print(f"Remove non-existent brandD for user1 successful: {success}") 
        prefs = get_user_preferred_brands("user1", db)
        print(f"User1 preferred brands after removing non-existent: {prefs}") 

        logger.info("\n--- Test set_user_preferred_brands (empty list) ---")
        success = set_user_preferred_brands("user1", [], db)
        print(f"Set empty brands for user1 successful: {success}") 
        prefs = get_user_preferred_brands("user1", db)
        print(f"User1 preferred brands after setting empty: {prefs}") 

        logger.info("\n--- Test _validate_brand_ids_exist ---")
        valid, invalid = _validate_brand_ids_exist(["brandA", "brandB", "invalid_id"], db)
        print(f"Validation for ['brandA', 'brandB', 'invalid_id']: Valid={valid}, Invalid={invalid}") 
        valid, invalid = _validate_brand_ids_exist(["brandA", "brandB"], db)
        print(f"Validation for ['brandA', 'brandB']: Valid={valid}, Invalid={invalid}") 
        valid, invalid = _validate_brand_ids_exist([], db)
        print(f"Validation for []: Valid={valid}, Invalid={invalid}") 

    except Exception as e:
        logger.critical(f"An unhandled error occurred in the main block: {e}")
    finally:
        db.close()
        logger.info("Database session closed.")