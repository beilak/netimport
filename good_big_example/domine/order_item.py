import dataclasses


@dataclasses.dataclass
class OrderItem:
    id: int
    order_id: int
    product_id: int
    quantity: int
    price: float
