import dataclasses
from decimal import Decimal


@dataclasses.dataclass
class Account:
    number: int
    title: str
    value: Decimal

    def plus(self, value: Decimal) -> Decimal:
        return value + self.value

    def minus(self, value: Decimal) -> Decimal:
        return value - self.value
