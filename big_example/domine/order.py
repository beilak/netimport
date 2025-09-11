import dataclasses
import datetime
from typing import List


@dataclasses.dataclass
class Order:
    id: int
    customer_id: int
    order_date: datetime.date
    status: str
    order_item_ids: List[int]
