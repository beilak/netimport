import typing
import typing as tp

from big_example.domine.order_item import OrderItem


class IOrderItemRepository(tp.Protocol):
    def save(self, order_item: OrderItem) -> None: ...


class OrderItemCreator:
    def __init__(self, order_item_repository: IOrderItemRepository) -> None:
        self._order_item_repository = order_item_repository

    def new(self, order_id: int, product_id: int, quantity: int, price: float) -> OrderItem:
        new_order_item: typing.Final = OrderItem(
            id=0, order_id=order_id, product_id=product_id, quantity=quantity, price=price
        )
        self._order_item_repository.save(new_order_item)

        return new_order_item
