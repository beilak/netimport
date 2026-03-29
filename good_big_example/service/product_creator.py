import typing
import typing as tp

from good_big_example.entities import Product


class IProductRepository(tp.Protocol):
    def save(self, product: Product) -> None: ...


class ProductCreator:
    def __init__(self, product_repository: IProductRepository) -> None:
        self._product_repository = product_repository

    def new(self, name: str, description: str, price: float, category_id: int) -> Product:
        new_product: typing.Final = Product(
            id=0, name=name, description=description, price=price, category_id=category_id
        )
        self._product_repository.save(new_product)

        return new_product
