from decimal import Decimal

from good_example.entities import Account


def test_account_stores_expected_fields() -> None:
    account = Account(number=101, title="Cash", value=Decimal("10.0"))

    assert account.number == 101
    assert account.title == "Cash"
    assert account.value == Decimal("10.0")


def test_account_arithmetic_helpers_use_account_value() -> None:
    account = Account(number=101, title="Cash", value=Decimal("10.0"))

    assert account.plus(Decimal("2.5")) == Decimal("12.5")
    assert account.minus(Decimal("2.5")) == Decimal("-7.5")
