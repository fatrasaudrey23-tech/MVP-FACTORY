import json
import uuid
from datetime import datetime
import os
import typing

class Recipe:
    def __init__(self,
                 name: str,
                 description: str,
                 ingredients: typing.List[typing.Dict[str, typing.Union[str, float]]],
                 instructions: typing.List[str],
                 prep_time_minutes: int,
                 cook_time_minutes: int,
                 servings: int,
                 category: str,
                 dietary_tags: typing.Optional[typing.List[str]] = None,
                 recipe_id: typing.Optional[str] = None,
                 created_at: typing.Optional[datetime] = None,
                 updated_at: typing.Optional[datetime] = None):
        self.id = recipe_id if recipe_id else str(uuid.uuid4())
        self.name = name
        self.description = description
        self.ingredients = ingredients
        self.instructions = instructions
        self.prep_time_minutes = prep_time_minutes
        self.cook_time_minutes = cook_time_minutes
        self.servings = servings
        self.category = category
        self.dietary_tags = dietary_tags if dietary_tags is not None else []
        self.created_at = created_at if created_at else datetime.now()
        self.updated_at = updated_at if updated_at else datetime.now()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'ingredients': self.ingredients,
            'instructions': self.instructions,
            'prep_time_minutes': self.prep_time_minutes,
            'cook_time_minutes': self.cook_time_minutes,
            'servings': self.servings,
            'category': self.category,
            'dietary_tags': self.dietary_tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @staticmethod
    def from_dict(data: typing.Dict[str, typing.Any]) -> 'Recipe':
        return Recipe(
            recipe_id=data['id'],
            name=data['name'],
            description=data['description'],
            ingredients=data['ingredients'],
            instructions=data['instructions'],
            prep_time_minutes=data['prep_time_minutes'],
            cook_time_minutes=data['cook_time_minutes'],
            servings=data['servings'],
            category=data['category'],
            dietary_tags=data.get('dietary_tags', []),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )

class RecipeStorage:
    def __init__(self, storage_file: str = 'recipes.json'):
        self.storage_file = storage_file
        self._recipes: typing.Dict[str, Recipe] = {}
        self._load_data()

    def _load_data(self) -> None:
        if os.path.exists(self.storage_file) and os.path.getsize(self.storage_file) > 0:
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._recipes = {item['id']: Recipe.from_dict(item) for item in data}
            except json.JSONDecodeError:
                self._recipes = {} # Handle empty or corrupt JSON file
        else:
            self._recipes = {}

    def _save_data(self) -> None:
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump([recipe.to_dict() for recipe in self._recipes.values()], f, indent=4)

    def add_recipe(self, recipe: Recipe) -> Recipe:
        recipe.updated_at = datetime.now()
        self._recipes[recipe.id] = recipe
        self._save_data()
        return recipe

    def get_recipe_by_id(self, recipe_id: str) -> typing.Optional[Recipe]:
        return self._recipes.get(recipe_id)

    def get_all_recipes(self) -> typing.List[Recipe]:
        return list(self._recipes.values())

    def find_recipes(self,
                     name: typing.Optional[str] = None,
                     category: typing.Optional[str] = None,
                     ingredient: typing.Optional[str] = None,
                     dietary_tag: typing.Optional[str] = None) -> typing.List[Recipe]:
        results = []
        for recipe in self._recipes.values():
            match = True
            if name and name.lower() not in recipe.name.lower():
                match = False
            if category and category.lower() != recipe.category.lower():
                match = False
            if ingredient and not any(ingredient.lower() in ing['name'].lower() for ing in recipe.ingredients):
                match = False
            if dietary_tag and dietary_tag.lower() not in [tag.lower() for tag in recipe.dietary_tags]:
                match = False
            if match:
                results.append(recipe)
        return results

    def update_recipe(self, recipe_id: str, updated_data: typing.Dict[str, typing.Any]) -> typing.Optional[Recipe]:
        recipe = self._recipes.get(recipe_id)
        if recipe:
            for key, value in updated_data.items():
                if hasattr(recipe, key):
                    setattr(recipe, key, value)
            recipe.updated_at = datetime.now()
            self._save_data()
            return recipe
        return None

    def delete_recipe(self, recipe_id: str) -> bool:
        if recipe_id in self._recipes:
            del self._recipes[recipe_id]
            self._save_data()
            return True
        return False