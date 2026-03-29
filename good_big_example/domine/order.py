import dataclasses
import datetime


@dataclasses.dataclass
class Order:
    id: int
    customer_id: int
    order_date: datetime.date
    status: str
    order_item_ids: list[int]
