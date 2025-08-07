from decimal import Decimal

from example.domine.account import Account


def test_account() -> None:
    assert Account(number=0, title="Test Account", value=Decimal("0.0"))


def test_print() -> None:
    pass
