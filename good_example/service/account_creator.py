from decimal import Decimal

from good_example.entities import Account
from good_example.ports import AccountWriter


class AccountCreator:
    def __init__(self, account_repository: AccountWriter) -> None:
        self._account_repository = account_repository

    def new(self, name: str) -> Account:
        new_account = Account(number=0, title=name, value=Decimal("0.0"))
        self._account_repository.save(new_account)

        return new_account
