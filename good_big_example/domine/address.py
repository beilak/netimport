import dataclasses


@dataclasses.dataclass
class Address:
    id: int
    street: str
    city: str
    state: str
    zip_code: str
    country: str
