import dataclasses


@dataclasses.dataclass
class Category:
    id: int
    name: str
    description: str
