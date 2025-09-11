import dataclasses
import datetime


@dataclasses.dataclass
class Shipment:
    id: int
    order_id: int
    shipment_date: datetime.date
    carrier: str
    tracking_number: str
