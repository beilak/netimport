import typing
import typing as tp
from decimal import Decimal

from example.domine.account import Account


class IAccountRepository(tp.Protocol):
    def save(self, account: Account) -> None: ...


class AccountCreator:
    def __init__(self, account_repository: IAccountRepository):
        self._account_repository = account_repository

    def new(self, name: str) -> Account:
        new_account: typing.Final = Account(number=0, title="test", value=Decimal(0.0))
        self._account_repository.save(new_account)


        return new_account
