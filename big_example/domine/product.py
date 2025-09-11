import dataclasses


@dataclasses.dataclass
class Product:
    id: int
    name: str
    description: str
    price: float
    category_id: int
