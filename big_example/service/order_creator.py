import datetime
import typing
import typing as tp
from typing import List

from big_example.domine.order import Order


class IOrderRepository(tp.Protocol):
    def save(self, order: Order) -> None: ...


class OrderCreator:
    def __init__(self, order_repository: IOrderRepository) -> None:
        self._order_repository = order_repository

    def new(self, customer_id: int, order_date: datetime.date, status: str, order_item_ids: List[int]) -> Order:
        new_order: typing.Final = Order(id=0, customer_id=customer_id, order_date=order_date, status=status, order_item_ids=order_item_ids)
        self._order_repository.save(new_order)

        return new_order
