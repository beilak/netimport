from good_big_example.entities import OrderItem


class OrderItemRepository:
    def __init__(self) -> None:
        self._some_obj = None

    def save(self, order_item: OrderItem) -> None:
        pass
