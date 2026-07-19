import os
from datetime import datetime
import typing

from sqlalchemy import create_engine, Column, Integer, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# Base for ORM models
Base = declarative_base()

class WeeklyBudget(Base):
    """
    ORM model for the weekly_budgets table.
    Stores weekly budget settings for users.
    """
    __tablename__ = 'weekly_budgets'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        """Converts the ORM object to a dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class WeeklyBudgetManager:
    """
    Manages weekly budget settings for users, interacting with a database
    via SQLAlchemy ORM.
    """

    def __init__(self, db_connection_string: str) -> None:
        """
        Constructor of the class, initializes the database connection.

        Args:
            db_connection_string (str): The database connection string
                                        (e.g., 'sqlite:///./sql_app.db').
        """
        self.engine = create_engine(db_connection_string)
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def _validate_budget_amount(self, amount: float) -> None:
        """
        Private validation method to ensure the budget amount is valid.

        Args:
            amount (float): The budget amount to validate.

        Raises:
            ValueError: If the amount is not a number or is negative.
        """
        if not isinstance(amount, (int, float)):
            raise ValueError("Budget amount must be a number (integer or float).")
        if amount < 0:
            raise ValueError("Budget amount cannot be negative.")

    def set_user_weekly_budget(self, user_id: int, amount: float) -> typing.Dict[str, typing.Any]:
        """
        Creates a new weekly budget for a user or updates an existing budget.
        This is the main "setting" function.

        Args:
            user_id (int): The unique identifier of the user.
            amount (float): The weekly budget amount to set.

        Returns:
            dict: A dictionary containing the details of the set budget.

        Raises:
            ValueError: If the budget amount is invalid.
        """
        self._validate_budget_amount(amount)

        session = self.Session()
        try:
            budget = session.query(WeeklyBudget).filter(WeeklyBudget.user_id == user_id).first()

            if budget:
                # Update existing budget
                budget.amount = amount
                budget.updated_at = datetime.utcnow()
            else:
                # Create new budget
                budget = WeeklyBudget(
                    user_id=user_id,
                    amount=amount,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(budget)

            session.commit()
            session.refresh(budget) # Refresh to get potentially updated timestamps/id

            return budget.to_dict()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_user_weekly_budget(self, user_id: int) -> typing.Optional[typing.Dict[str, typing.Any]]:
        """
        Retrieves the currently set weekly budget for a given user.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            dict: A dictionary containing the budget details if found,
                  otherwise None.
        """
        session = self.Session()
        try:
            budget = session.query(WeeklyBudget).filter(WeeklyBudget.user_id == user_id).first()
            if budget:
                return budget.to_dict()
            return None
        finally:
            session.close()

    def update_user_weekly_budget(self, user_id: int, new_amount: float) -> typing.Dict[str, typing.Any]:
        """
        Updates the weekly budget amount for an existing user.

        Args:
            user_id (int): The unique identifier of the user.
            new_amount (float): The new budget amount.

        Returns:
            dict: A dictionary containing the details of the updated budget.

        Raises:
            ValueError: If the new budget amount is invalid or if no budget
                        is found for the user.
        """
        self._validate_budget_amount(new_amount)

        session = self.Session()
        try:
            budget = session.query(WeeklyBudget).filter(WeeklyBudget.user_id == user_id).first()

            if not budget:
                raise ValueError(f"No weekly budget found for user_id: {user_id}")

            budget.amount = new_amount
            budget.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(budget) # Refresh to get updated timestamp

            return budget.to_dict()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_user_weekly_budget(self, user_id: int) -> bool:
        """
        Deletes the weekly budget setting for a user.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            bool: True if the budget was successfully deleted, False otherwise.
        """
        session = self.Session()
        try:
            budget = session.query(WeeklyBudget).filter(WeeklyBudget.user_id == user_id).first()

            if budget:
                session.delete(budget)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

# Example usage (for demonstration purposes, not part of the class)
if __name__ == "__main__":
    # Use an in-memory SQLite database for demonstration
    DB_CONNECTION_STRING = os.getenv("DATABASE_URL", "sqlite:///./weekly_budgets.db")

    manager = WeeklyBudgetManager(DB_CONNECTION_STRING)

    print("--- Setting/Updating Budgets ---")

    # Set a new budget for user 1
    try:
        budget1 = manager.set_user_weekly_budget(user_id=1, amount=150.75)
        print(f"Set budget for user 1: {budget1}")
    except ValueError as e:
        print(f"Error setting budget for user 1: {e}")

    # Set a new budget for user 2
    try:
        budget2 = manager.set_user_weekly_budget(user_id=2, amount=200.00)
        print(f"Set budget for user 2: {budget2}")
    except ValueError as e:
        print(f"Error setting budget for user 2: {e}")

    # Update budget for user 1
    try:
        updated_budget1 = manager.set_user_weekly_budget(user_id=1, amount=175.50)
        print(f"Updated budget for user 1: {updated_budget1}")
    except ValueError as e:
        print(f"Error updating budget for user 1: {e}")

    print("\n--- Retrieving Budgets ---")

    # Get budget for user 1
    retrieved_budget1 = manager.get_user_weekly_budget(user_id=1)
    print(f"Retrieved budget for user 1: {retrieved_budget1}")

    # Get budget for user 2
    retrieved_budget2 = manager.get_user_weekly_budget(user_id=2)
    print(f"Retrieved budget for user 2: {retrieved_budget2}")

    # Try to get budget for a non-existent user
    retrieved_budget3 = manager.get_user_weekly_budget(user_id=3)
    print(f"Retrieved budget for user 3: {retrieved_budget3}")

    print("\n--- Explicitly Updating Budgets ---")
    try:
        explicit_update_budget2 = manager.update_user_weekly_budget(user_id=2, new_amount=220.25)
        print(f"Explicitly updated budget for user 2: {explicit_update_budget2}")
    except ValueError as e:
        print(f"Error explicitly updating budget for user 2: {e}")

    # Try to update a non-existent budget
    try:
        manager.update_user_weekly_budget(user_id=4, new_amount=100.00)
    except ValueError as e:
        print(f"Error updating non-existent budget for user 4: {e}")

    print("\n--- Deleting Budgets ---")

    # Delete budget for user 1
    delete_success1 = manager.delete_user_weekly_budget(user_id=1)
    print(f"Deletion successful for user 1: {delete_success1}")
    print(f"Budget for user 1 after deletion: {manager.get_user_weekly_budget(user_id=1)}")

    # Try to delete a non-existent budget
    delete_success4 = manager.delete_user_weekly_budget(user_id=4)
    print(f"Deletion successful for non-existent user 4: {delete_success4}")

    # Final check
    print("\n--- Final Check ---")
    print(f"Budget for user 1: {manager.get_user_weekly_budget(user_id=1)}")
    print(f"Budget for user 2: {manager.get_user_weekly_budget(user_id=2)}")