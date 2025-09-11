import dataclasses
import datetime


@dataclasses.dataclass
class Promotion:
    id: int
    code: str
    description: str
    discount_percentage: float
    start_date: datetime.date
    end_date: datetime.date
