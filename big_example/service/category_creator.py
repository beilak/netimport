import typing
import typing as tp

from big_example.domine.category import Category


class ICategoryRepository(tp.Protocol):
    def save(self, category: Category) -> None: ...


class CategoryCreator:
    def __init__(self, category_repository: ICategoryRepository) -> None:
        self._category_repository = category_repository

    def new(self, name: str, description: str) -> Category:
        new_category: typing.Final = Category(id=0, name=name, description=description)
        self._category_repository.save(new_category)

        return new_category
