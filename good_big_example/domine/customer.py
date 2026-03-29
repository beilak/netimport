import dataclasses


@dataclasses.dataclass
class Customer:
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    address_id: int
