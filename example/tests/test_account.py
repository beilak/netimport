from decimal import Decimal

from example.domine.account import Account
from ..repo.account_repo import AccountRepository


def test_account():
    assert Account(number=0, title="Test Account", value=Decimal(0.0))


def test_print():
    print(AccountRepository)