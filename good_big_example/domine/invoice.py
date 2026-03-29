import dataclasses
import datetime


@dataclasses.dataclass
class Invoice:
    id: int
    order_id: int
    invoice_date: datetime.date
    due_date: datetime.date
    total_amount: float
