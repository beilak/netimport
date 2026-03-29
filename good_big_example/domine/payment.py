import dataclasses
import datetime


@dataclasses.dataclass
class Payment:
    id: int
    order_id: int
    payment_date: datetime.date
    amount: float
    payment_method: str
