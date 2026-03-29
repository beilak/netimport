from good_big_example.entities import Order


class OrderRepository:
    def __init__(self) -> None:
        self._some_obj = None

    def save(self, order: Order) -> None:
        pass
